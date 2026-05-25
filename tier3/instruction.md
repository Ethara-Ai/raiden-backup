# AWS CLI — S3 Subset (Tier 3)

Implement an executable at `/app/awscli` supporting six `s3` subcommands
with full single-file and recursive semantics:

- `mb` — make bucket
- `rb` — remove bucket
- `cp` — copy (single-file and recursive, all three direction triples)
- `ls` — list (with `--recursive`, `--human-readable`, `--summarize`)
- `mv` — move (cp + delete-source semantics)
- `rm` — remove (single-key and recursive)

Plus include/exclude filter semantics for `cp` / `mv` / `rm` recursive.

This is Tier 3 — the full pilot scope minus `sync`. The implementation is
tested as a black box.

---

## 1. Runtime contract

- Entry point: `/app/awscli` (executable, any shebang).
- Required env vars: `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`.
- Allowed deps: `boto3`, `botocore`, Python stdlib.
- Forbidden: invoking any pre-built `aws`/`awscli` binary; real network
  calls outside `AWS_ENDPOINT_URL`.

---

## 2. Output format strings (the contract)

Single source of truth for all transfer-type stdout templates. Every line
ends with `\n`.

| Transfer type | Template | Stream |
|---|---|---|
| `upload` (local → s3) | `upload: <rel_local> to s3://<bucket>/<key>` | stdout |
| `download` (s3 → local) | `download: s3://<bucket>/<key> to <rel_local>` | stdout |
| `copy` (s3 → s3 via `cp`) | `copy: s3://<sb>/<sk> to s3://<db>/<dk>` | stdout |
| `move` (any direction via `mv`) | `move: s3://<sb>/<sk> to s3://<db>/<dk>` (or analogous for local↔s3) | stdout |
| `delete` (via `rm`, `rb --force`, `mv` source removal) | `delete: s3://<bucket>/<key>` | stdout |
| `make_bucket` | `make_bucket: <bucket>` (bare name) | stdout |
| `remove_bucket` | `remove_bucket: <bucket>` (bare name) | stdout |
| dryrun prefix | `(dryrun) ` (with trailing space) prepended to any success line | stdout |
| failure | `<transfer_type> failed: <src> to <dest> <error>` (or `<transfer_type> failed: <src> <error>` for single-arg ops) | stderr |

For `<rel_local>`: relative to the current working directory at invocation,
NO `./` prefix.

For URI normalization: trailing `/` on a destination means "use src basename".
Example: `cp s3://b/a/x.txt s3://b2/` writes to `s3://b2/x.txt`, NOT
`s3://b2/a/x.txt`.

---

## 3. Exit codes

| Code | Meaning |
|---|---|
| `0` | All operations succeeded. |
| `1` | One or more operations failed (API error, validation in some cases). |
| `2` | One or more warnings emitted and no failures (e.g. Glacier-storage object skipped). |
| `130` | Operation interrupted by SIGINT. |
| `255` | Fatal validation error before any operation. |

---

## 4. URI parsing

```
s3://<bucket>          → bucket = <bucket>, key = ""
s3://<bucket>/         → bucket = <bucket>, key = ""
s3://<bucket>/<key>    → bucket = <bucket>, key = <key>
s3://<bucket>/a/b/c    → bucket = <bucket>, key = "a/b/c"   (split on FIRST / only)
```

Trailing slash on a destination URI means "use src basename".

Path types:

- `LocalPath` + `S3Uri`: **upload**
- `S3Uri` + `LocalPath`: **download**
- `S3Uri` + `S3Uri`: **copy** (or **move** via `mv`)
- `LocalPath` + `LocalPath`: **rejected with fatal validation error**

---

## 5. `s3 mb` (regression scope)

```
aws s3 mb <S3Uri>
```

Stdout: `make_bucket: <bucket>\n`. Stderr (failure): `make_bucket failed: <arg> <err>\n`. Exit 0/1.

---

## 6. `s3 rb`

```
aws s3 rb <S3Uri> [--force]
```

Stdout: `remove_bucket: <bucket>\n`.

With `--force`: emit one `delete: s3://<bucket>/<key>\n` per object first,
then `remove_bucket:`. If recursive delete fails, bucket is NOT deleted
and stderr reports fatal failure.

---

## 7. `s3 cp` — full scope

### Synopsis

```
aws s3 cp <src> <dest>
    [--recursive]
    [--dryrun] [--quiet] [--only-show-errors] [--no-progress]
    [--include PATTERN]... [--exclude PATTERN]...
    [--content-type CT] [--cache-control CC]
    [--storage-class CLASS] [--metadata K=V,...]
    [--metadata-directive {COPY,REPLACE}]
    [--page-size N]
    [--source-region REGION]
```

### Single-file vs recursive

- **Single file** (default, no `--recursive`):
  - `src` is exactly one file/object.
  - `dest` ending in `/` preserves src basename.
  - Local → local rejected.
  - Streaming with `-` is not in scope for this pilot.
- **Recursive** (`--recursive`):
  - `src` is a directory (local) or prefix (S3).
  - `dest` is a directory or prefix.
  - All files under `src` are transferred, preserving relative paths.
  - Auto-creates missing destination directories for s3 → local.

### Stdout (single transfer)

See §2.

### Filters

If `--include` and/or `--exclude` are present:

- **Default state**: every file INCLUDED.
- Each filter is evaluated **after prepending the source root** to its
  pattern. E.g., `--exclude ".git/*"` actually matches `<src_root>/.git/*`.
- Later filters **override** earlier ones.
- Pattern syntax: `fnmatch` (`*`, `?`, `[seq]`, `[!seq]`). NO `**` recursive
  glob; NO regex.
- A bare `--include PATTERN` (no preceding `--exclude`) is a no-op because
  default is already INCLUDE.

Examples:
- `--exclude '*' --include '*.txt'` → only `.txt` files.
- `--include '*.txt' --exclude '*'` → nothing transferred.

### Failure
```
upload failed: <src> to <dest> <error>
download failed: <src> to <dest> <error>
copy failed: <src> to <dest> <error>
```
Exit code: `1` for failures, `0` for success.

---

## 8. `s3 mv`

```
aws s3 mv <src> <dest> [same flags as cp minus --expected-size]
```

`mv` = `cp` + delete-source after successful copy.

Transfer-type emitted is `move:` (NOT `copy:`) for all three directions:

```
move: <src> to <dest>
```

### Self-move guard

`mv s3://b/k s3://b/k` (and equivalent normalized forms) MUST raise a fatal
validation error before any API call:

```
Cannot mv a file onto itself: s3://b/k - s3://b/k
```

Exit code: `255` (or `1`; both are acceptable for this validation).

### Source deletion

The source is deleted only if the copy succeeds. Failure of the copy
leaves the source untouched.

---

## 9. `s3 ls` — full scope

```
aws s3 ls [<S3Uri>] [--recursive] [--human-readable] [--summarize]
                    [--page-size N]
```

### Modes
- No URI or `s3://` → list buckets.
- `s3://bucket[/prefix]` non-recursive → mixed prefix + leaf output.
- `--recursive` → leaf-only output, full keys (no `PRE` lines).

### Bucket listing
```
YYYY-MM-DD HH:MM:SS <bucket_name>
```

### Object lines (non-recursive)
```
                              PRE <subdir>/    (common-prefix line, 30-char width to PRE)
YYYY-MM-DD HH:MM:SS  <size_rjust_10> <basename>
```

### Object lines (recursive)
```
YYYY-MM-DD HH:MM:SS  <size_rjust_10> <full_key>
```

### `--human-readable` size formatting

Source-of-truth from `awscli/customizations/s3/utils.py human_readable_size`:

- `0` → `0 Bytes`
- `1` → `1 Byte` (singular)
- `2..1023` → `N Bytes`
- `1024..` → `{n.n} KiB` / `MiB` / `GiB` / `TiB` / `PiB` / `EiB`
  (one decimal place, base-2 IEC).

### `--summarize`

Appends:

```
<blank line>
Total Objects: N
   Total Size: S
```

Object count excludes common-prefix lines.

### Exit codes
- `0` if at least one bucket/object/prefix matched.
- `1` if a user-provided **key prefix** matched nothing (e.g.
  `ls s3://bucket/no-such/`).
- `0` if a **bucket-style URI** matched nothing (empty bucket → exit `0`).

---

## 10. `s3 rm` — full scope

```
aws s3 rm <S3Uri> [--recursive] [--dryrun] [--quiet] [--only-show-errors]
                  [--include PATTERN]... [--exclude PATTERN]...
                  [--page-size N]
```

### Single-object (no `--recursive`)
- Idempotent: deleting a non-existent key still prints the `delete:` line
  and exits `0`.

### Recursive (`--recursive`)
- Lists every object under the prefix and deletes each.
- Filters applied as in `cp` recursive.

### Dryrun
- Prefix `(dryrun) ` on delete lines. No state change.

---

## 11. Verbosity matrix

| Flag | Progress | Success lines | Errors |
|---|---|---|---|
| (none) | yes (\r) | yes | yes |
| `--no-progress` | no | yes | yes |
| `--quiet` | no | no | yes |
| `--only-show-errors` | no | no | yes |
| `--dryrun` | no | yes (prefixed `(dryrun) `) | n/a |

---

## 12. Properties tests will verify

- Round-trip integrity: `cp local s3 && cp s3 local2` ⇒ byte-equal.
- `mv` deletes source if and only if copy succeeded.
- `mv` self-move is rejected before API call.
- Filter order matters: `--exclude '*' --include '*.txt'` keeps `.txt`;
  reversed keeps nothing.
- Filter root-prefixing: `--exclude '.git/*'` actually matches paths
  relative to the source root.
- Trailing slash on destination preserves source basename.
- Recursive `cp` auto-creates local destination directories.
- `rm s3://b/non-existent` exits `0`.
- `ls --human-readable` produces `1 Byte` (singular) for 1, `2 Bytes` for 2.
- `ls --recursive` does not emit `PRE` lines.
- `ls` of unmatched key prefix exits `1`; empty bucket exits `0`.
- Byte-exact stdout for each success template.
- Side-effects verified via direct S3 client (not just stdout).

---

## 13. Submission

Place an executable at `/app/awscli`, `chmod +x` it, and exit.
