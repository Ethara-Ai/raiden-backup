# Known Divergences: moto 5.2.1 vs real S3

Behaviors that differ between the simulator and production S3. Tests are
designed to assert on aspects where moto and real S3 agree; this doc
records the deltas for transparency.

## Where moto matches real S3 (we depend on these)

- `CreateBucket` / `DeleteBucket` / `HeadBucket` / `ListBuckets`
- `PutObject` / `GetObject` / `CopyObject` / `DeleteObject` / `HeadObject`
- `ListObjectsV2` with `Prefix` and `MaxKeys`
- Error codes: `NoSuchBucket`, `NoSuchKey`, `BucketAlreadyOwnedByYou`,
  `BucketNotEmpty`, `AccessDenied`
- Path-style virtual-hosting (with `S3_IGNORE_SUBDOMAIN_BUCKETNAME=true`)
- Multipart upload (5 MiB minimum part size)
- ETag format: `<md5>` single-part, `<md5>-<count>` multipart
- Bucket region routing (CreateBucket with LocationConstraint)

## Where moto diverges (tests avoid asserting on these)

### Error message text

Real S3 emits specific phrasings like
`"The specified bucket does not exist"`. moto's text is close but not
byte-identical. **Tests assert on error CODE (`NoSuchBucket`) only,
never on full message text.**

### LastModified precision

Real S3: whole-second, server-assigned at upload time.
moto: whole-second, request-time on the server.

Both are whole-second precision. For tests that compare timestamps,
ordering is deterministic within a process; absolute values differ
across runs. Tests do not assert exact dates.

### `BucketAlreadyOwnedByYou` in us-east-1

Real S3: returns `OK` silently if you re-create an owned bucket in
us-east-1.
moto: returns the error in every region.

**Tests run the duplicate-bucket assertion in `us-west-2`** to avoid
the divergence.

### MaxKeys default

Real S3: default 1000.
moto: default 100. We override via `MOTO_S3_DEFAULT_MAX_KEYS=1000` env
var (set in `shared/Dockerfile`).

### CRC32C checksums

Real S3: supports CRC32C natively.
moto: requires `pip install moto[s3crc32c]`. We don't install this
because no tests assert on CRC32C.

### Cross-account access

Real S3: enforces account boundaries.
moto: permissive by default; we override via
`MOTO_S3_ALLOW_CROSSACCOUNT_ACCESS=false`.

### Default CORS

Real S3: no CORS by default.
moto: permissive default; we override via `MOTO_DISABLE_GLOBAL_CORS=true`.

### `--acl` flag

Real S3: supports BucketACL/ObjectACL APIs.
moto: partial support; aws-cli `--acl public-read` works at the API
level but the ACL state may differ.

**Tests do not assert on ACL behaviors.**

### S3 Object Lambda, S3 Access Points

Real S3: full support.
moto: not implemented.

**Tests do not exercise these.**

### Real-S3 idempotency vs moto for multipart

If you complete the same multipart upload twice, real S3 may return
slightly different error codes vs moto. We don't have tests that
re-complete multipart uploads.

## Configuration we apply to minimize divergence

```dockerfile
ENV MOTO_S3_DEFAULT_MAX_KEYS=1000          # match real default
ENV MOTO_DISABLE_GLOBAL_CORS=true          # match real default
ENV MOTO_S3_ALLOW_CROSSACCOUNT_ACCESS=false # match real default
ENV S3_IGNORE_SUBDOMAIN_BUCKETNAME=true    # use path-style
```

These four overrides bring moto's S3 behavior closer to real S3 for the
6 commands this env covers.

## When to worry about a divergence

A test that fails on real S3 but passes against moto (or vice versa) is
a bug. If we discover one:

1. Document it here.
2. If the divergence is in our favor (test passes everywhere) — leave it.
3. If the divergence breaks the test on real S3 — change the test to
   target a behavior both implementations agree on, OR add a `pytest.skip`
   with rationale.

## Validating against real S3

The oracle path bakes real `aws-cli` v2.17.0. By running
`harbor run -p tierN -a oracle` we exercise:

- The CLI's interpretation of the commands (correct args, correct API calls).
- Moto's response to those calls (correct enough to satisfy tests).

If oracle scores ≥ 0.98 on a tier, both the CLI and moto's responses
agree with the tests for that tier.

## Reporting future divergences

If you discover a divergence not listed here, append it to this file
with:
- The behavior.
- Real S3's response.
- moto's response.
- Whether tests assert on it.
- Mitigation (if any).
