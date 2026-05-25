# AWS CLI — S3 Subset (Tier 1)

You will implement an executable at `/app/awscli` that supports two `s3`
subcommands: **`mb`** (make bucket) and **`rb`** (remove bucket). The
implementation will be tested as a black box — tests invoke
`/app/awscli s3 <subcommand> [args]` via subprocess and assert on stdout,
stderr, exit code, and side-effects in the S3 backend.

This is Tier 1 of a 3-tier curriculum. Later tiers add `cp`, `ls`, `rm`,
`mv`, recursive operations, and filters.

---

## 1. Runtime contract

- **Entry point**: `/app/awscli` — an executable file. You choose the shebang
  (`#!/usr/bin/env python3`, `#!/bin/bash`, etc.). Mark it `chmod +x`.
- **Working directory** at invocation: arbitrary. Your code must respect
  cwd-relative paths.
- **Environment variables you MUST honor**:
  - `AWS_ENDPOINT_URL` — base URL for the S3 API (set in the container).
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — credentials.
  - `AWS_DEFAULT_REGION` — default region for new buckets.

### Allowed dependencies

You may use the following Python packages (already installed in the container):

- `boto3`
- `botocore`

You may also use any standard-library module.

### Forbidden

- Invoking any pre-built `aws` / `awscli` / `aws-cli-v2` binary present on
  the system. Roll your own.
- Making real network calls outside the configured `AWS_ENDPOINT_URL`.
- Reading test files or solution files (these are not present during your
  run anyway).

---

## 2. Subcommand: `s3 mb`

Create a bucket.

### Synopsis

```
aws s3 mb <S3Uri> [--tags KEY VALUE]...
```

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `<S3Uri>` | string | yes | Bucket URI of the form `s3://bucket-name`. |
| `--tags` | repeatable, 2 args | no | Key/value pair to attach as a bucket tag. |

### Output on success

A single line to stdout, exactly:

```
make_bucket: <bucket>
```

Note: the literal output is the **bare bucket name**, not `s3://<bucket>`.

stderr: empty.
Exit code: `0`.

### Output on failure

A single line to stderr, exactly:

```
make_bucket failed: <s3uri_arg> <error_details>
```

Where `<error_details>` is the underlying error message (typically a
botocore `ClientError` string like
`An error occurred (BucketAlreadyOwnedByYou) when calling the CreateBucket operation: ...`).

stdout: empty.
Exit code: `1`.

### Behavior

- The bucket is created at the region given by `AWS_DEFAULT_REGION`.
- For regions other than `us-east-1`, you must pass `LocationConstraint`
  in the CreateBucket configuration. Sending `LocationConstraint=us-east-1`
  causes an `InvalidLocationConstraint` error.
- Tags, when present, are sent as part of the CreateBucket configuration.

### Validation errors

- A URI that does not start with `s3://` is a fatal error. Exit code `255`,
  stderr: a fatal error message describing the invalid argument.
- A URI that contains a key (e.g. `s3://bucket/key`) is also invalid for
  this command. Reject before the API call.

### Examples

```
$ aws s3 mb s3://my-bucket
make_bucket: my-bucket
$ echo $?
0
```

```
$ aws s3 mb s3://my-bucket
make_bucket failed: s3://my-bucket An error occurred (BucketAlreadyOwnedByYou) when calling the CreateBucket operation: ...
$ echo $?
1
```

---

## 3. Subcommand: `s3 rb`

Remove a bucket.

### Synopsis

```
aws s3 rb <S3Uri> [--force]
```

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `<S3Uri>` | string | yes | Bucket URI of the form `s3://bucket-name`. |
| `--force` | flag | no | Delete all objects in the bucket before removing it. |

### Output on success

A single line to stdout, exactly:

```
remove_bucket: <bucket>
```

(Bare bucket name, same convention as `mb`.)

stderr: empty.
Exit code: `0`.

### Output on failure

A single line to stderr:

```
remove_bucket failed: <s3uri_arg> <error_details>
```

Exit code: `1`.

### Behavior

- Without `--force`: simply attempts `DeleteBucket`. If the bucket is
  non-empty, the underlying S3 returns `BucketNotEmpty` and the command
  fails.
- With `--force`: first deletes every object in the bucket (internally
  equivalent to `s3 rm <S3Uri> --recursive`), then `DeleteBucket`. Each
  object deletion is printed as a separate line:

  ```
  delete: s3://<bucket>/<key>
  ```

  followed by the final `remove_bucket: <bucket>` line.

- If the recursive deletion fails for any reason (permissions, etc.), the
  bucket is NOT deleted, and stderr emits a fatal error:

  ```
  remove_bucket failed: <s3uri_arg> Unable to delete all objects in the bucket, bucket will not be deleted.
  ```

  Exit code: `1`.

### Validation errors

- A URI without `s3://` prefix is a fatal error. Exit code `255`.
- A URI containing a key (`s3://bucket/key`) is invalid. Reject before the
  API call.

### Examples

```
$ aws s3 rb s3://my-empty-bucket
remove_bucket: my-empty-bucket
$ echo $?
0
```

```
$ aws s3 rb s3://has-objects --force
delete: s3://has-objects/file1.txt
delete: s3://has-objects/file2.txt
remove_bucket: has-objects
$ echo $?
0
```

```
$ aws s3 rb s3://has-objects
remove_bucket failed: s3://has-objects An error occurred (BucketNotEmpty) when calling the DeleteBucket operation: The bucket you tried to delete is not empty
$ echo $?
1
```

---

## 4. Cross-cutting rules

### URI parsing

- All S3 URIs begin with `s3://`.
- For bucket-only URIs:
  - `s3://bucket` is valid for `mb` and `rb`.
  - `s3://bucket/` (trailing slash) is also valid.
  - `s3://bucket/key` is INVALID for `mb` and `rb` — reject with a
    validation error.
- Strip the `s3://` prefix and validate the remainder is a non-empty
  bucket-name without `/` (or has only a trailing `/`).

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Operation succeeded. |
| `1` | Operation attempted but failed (API error, etc.). |
| `255` | Fatal validation error (bad URI, etc.). |

### Output streams

- Success lines go to **stdout**.
- Failure / fatal lines go to **stderr**.
- Every line ends with a single `\n`.

### Properties tests will check

Tests will verify, among other things:
- After `mb s3://X`, listing buckets shows `X`.
- After `rb s3://X`, listing buckets does NOT show `X`.
- `mb` then `mb` of the same bucket fails the second time with the right
  error code.
- `rb` of a non-empty bucket without `--force` fails.
- `rb` of the same bucket with `--force` succeeds and deletes the objects.
- The exact stdout/stderr lines documented above.

---

## 5. Submission

Place your executable at `/app/awscli`, ensure it has the executable bit
set (`chmod +x /app/awscli`), and exit. The harness will then run the
test suite against your submission.

Minimal Python skeleton (you do not have to follow this layout):

```python
#!/usr/bin/env python3
import sys

def main(argv):
    # argv[0] is the script name; argv[1:] are user args.
    # Expected: "s3" <subcommand> ...
    ...

if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Good luck.
