# AWS CLI — S3 Subset (Tier 2)

Implement an executable at `/app/awscli` supporting five `s3` subcommands:
**`mb`**, **`rb`**, **`cp` (single-file)**, **`ls`**, **`rm`**. The implementation
is tested as a black box — tests invoke `/app/awscli s3 <subcommand> [args]`
via subprocess and assert on stdout, stderr, exit code, and S3-side state.

This is Tier 2 of a 3-tier curriculum. Tier 3 adds `mv`, recursive `cp`,
include/exclude filters, and more URI parsing.

---

## 1. Runtime contract

- **Entry point**: `/app/awscli` (executable file, any shebang).
- **Working directory** at invocation: arbitrary.
- **Required env vars** (set in the container):
  - `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
    `AWS_DEFAULT_REGION`.
- **Allowed deps**: `boto3`, `botocore`, Python stdlib.
- **Forbidden**: pre-built `aws` / `awscli` binaries; real network calls
  outside `AWS_ENDPOINT_URL`.

---

## 2. `s3 mb` — make bucket

### Synopsis
```
aws s3 mb <S3Uri>
```

### Stdout (success)
```
make_bucket: <bucket>
```
(bare bucket name, no `s3://` prefix). Exit code `0`.

### Stderr (failure)
```
make_bucket failed: <s3uri_arg> <error_details>
```
Exit code `1`.

### Behavior
- For non-`us-east-1` regions, send `LocationConstraint`.
- For `us-east-1`, do not send `LocationConstraint` (else `InvalidLocationConstraint`).
- URI without `s3://` prefix → fatal validation error, exit `255`.
- URI containing a key → reject before API call.

---

## 3. `s3 rb` — remove bucket

### Synopsis
```
aws s3 rb <S3Uri> [--force]
```

### Stdout (success)
```
remove_bucket: <bucket>
```
With `--force`, prepend one `delete: s3://<bucket>/<key>` line per object
removed. Exit code `0`.

### Stderr (failure)
```
remove_bucket failed: <s3uri_arg> <error_details>
```
Exit code `1`.

### Behavior
- Without `--force`: `DeleteBucket` directly. Non-empty bucket → `BucketNotEmpty`.
- With `--force`: delete every object (emit `delete: ...` per object), then
  `DeleteBucket`. If recursive delete fails, bucket is NOT deleted.

---

## 4. `s3 cp` (single-file) — copy

### Synopsis (this tier — no `--recursive`)
```
aws s3 cp <src> <dest> [--dryrun] [--quiet] [--only-show-errors]
                       [--no-progress] [--content-type CT]
                       [--metadata K=V,...]
                       [--storage-class CLASS]
                       [--cache-control CC]
                       [--page-size N]
```

### Path types (this tier)
- `LocalPath` → `S3Uri`: **upload**.
- `S3Uri` → `LocalPath`: **download**.
- `S3Uri` → `S3Uri`: **copy** (same-bucket or cross-bucket).
- `LocalPath` → `LocalPath`: **rejected** with fatal validation error.
- Streaming `-` is **not** in scope for this tier.

### Stdout (success, one line per file)

| Direction | Template |
|---|---|
| local → s3 | `upload: <rel_local> to s3://<bucket>/<key>` |
| s3 → local | `download: s3://<bucket>/<key> to <rel_local>` |
| s3 → s3 | `copy: s3://<src_b>/<src_k> to s3://<dest_b>/<dest_k>` |

- `<rel_local>` is the path relative to the current working directory (no
  `./` prefix).
- Trailing `/` on the destination preserves the source basename. Example:
  `cp s3://b/a/x.txt s3://b2/` puts the object at `s3://b2/x.txt`.

### Dryrun
With `--dryrun`, prepend the literal string `(dryrun) ` (with trailing space)
to the success line. No state change.

### Quiet / no-progress / only-show-errors

- `--quiet` / `--only-show-errors`: suppress success lines (errors still
  go to stderr). Exit code unchanged.
- `--no-progress`: do not emit `\r`-style progress updates (you may still
  print success lines).

### Stderr (failure)
```
<transfer_type> failed: <src> to <dest> <error_details>
```
Where `<transfer_type>` is `upload` | `download` | `copy`. Exit code `1`.

### Validation errors
- `LocalPath` → `LocalPath` → fatal validation error, exit `255`.
- Missing local source file → exit `1`, error message naming the missing path.

---

## 5. `s3 ls` — list buckets or objects

### Synopsis
```
aws s3 ls [<S3Uri>] [--human-readable] [--summarize] [--page-size N]
```

### Three modes

**(a) Bucket listing**: `ls` or `ls s3://`. One line per bucket:
```
YYYY-MM-DD HH:MM:SS <bucket_name>
```
Date is `CreationDate` formatted in the LOCAL timezone (which is UTC in
this container). Exit code `0` even if zero buckets.

**(b) Prefix listing**: `ls s3://bucket[/prefix]`. Mixed output:
- Common-prefix lines (subdirectory placeholders):
  ```
                              PRE <prefix>/
  ```
  (literal: 27 spaces, then `PRE`, one space, then prefix + `/`)
- Object lines:
  ```
  YYYY-MM-DD HH:MM:SS  <size_rjust_10> <basename>
  ```
  Date format same as above. Size is right-justified in width 10. Last
  field is the basename (segment after final `/`).

**(c) Recursive listing**: when `--recursive` is in scope (it isn't in
this tier; tier 3 adds it). For tier 2, no `--recursive` flag.

### Modifiers

- `--human-readable`: format sizes using base-2 IEC suffixes.
  - `0` → `0 Bytes`
  - `1` → `1 Byte` (singular!)
  - `2..1023` → `N Bytes`
  - `1024..` → `<n>.<n> KiB` / `MiB` / `GiB` / `TiB` / `PiB` / `EiB`
    (one decimal place).
- `--summarize`: appends a trailing block:
  ```
  <blank line>
  Total Objects: N
     Total Size: S
  ```
  Counts only objects (not common prefixes).

### Exit codes
- `0` on success.
- `1` if a user-provided KEY-style prefix matched nothing (e.g.
  `ls s3://bucket/no-such-prefix`).
- `0` if a bucket-style URI matched nothing (empty bucket → exit 0).

---

## 6. `s3 rm` — remove objects

### Synopsis (this tier — no `--recursive`)
```
aws s3 rm <S3Uri> [--dryrun] [--quiet] [--only-show-errors]
                  [--page-size N]
```

### Stdout
```
delete: s3://<bucket>/<key>
```
(One line per object removed; no `to <dest>` field.)

### Dryrun
With `--dryrun`, prepend `(dryrun) ` to the delete line. No state change.

### Behavior
- Without `--recursive`: deletes exactly one object. `DeleteObject` is
  idempotent — removing a non-existent key still prints the line and
  exits `0`.

### Exit codes
- `0` always for valid input. `1` only on API errors.

---

## 7. Cross-cutting rules

### URI parsing

- `s3://bucket` — bucket-only.
- `s3://bucket/` — bucket-only (normalize: append `/` when bucket-only).
- `s3://bucket/key` — bucket + key. Keys may contain `/`.
- `s3://bucket/a/b/c` — bucket = `bucket`, key = `a/b/c` (split on FIRST `/` only).
- Trailing `/` on a destination URI means "use source basename" for
  single-file `cp`.

### Exit codes (canonical)

| Code | Meaning |
|---|---|
| `0` | All operations succeeded. |
| `1` | One or more transfers / operations failed. |
| `2` | (Tier 3 only — Glacier warnings.) |
| `255` | Fatal validation error. |

### Output streams
- Success lines, dryrun lines, `ls` output → **stdout**.
- Failure / fatal lines → **stderr**.
- All lines end with `\n`.

### Verbosity matrix

| Flag | Progress | Success lines | Errors |
|---|---|---|---|
| (none) | yes | yes | yes |
| `--no-progress` | no | yes | yes |
| `--quiet` | no | no | yes |
| `--only-show-errors` | no | no | yes |
| `--dryrun` | no | yes (prefixed) | n/a |

---

## 8. Properties tests will verify

- Round-trip integrity: `cp local s3 && cp s3 local2` ⇒ `bytes(local) == bytes(local2)`.
- After `cp`, `ls` shows the object.
- After `rm`, `ls` does not show the object.
- `rm` of a non-existent key exits `0` and prints the delete line.
- `mb` then `mb` of the same bucket fails with the right error code.
- `rb --force` on a non-empty bucket succeeds; without `--force` fails.
- `--dryrun` does NOT mutate state.
- Byte-exact stdout for each success template.

---

## 9. Submission

Place an executable at `/app/awscli`, `chmod +x` it, and exit.
