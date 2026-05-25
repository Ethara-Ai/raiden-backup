"""Byte-exact assertion helpers for aws-cli stdout templates.

Templates are sourced from awscli/customizations/s3/results.py and subcommands.py
(verified at the source-of-truth level). Each helper returns nothing on match,
raises AssertionError with diff-style error on mismatch.
"""
import re


# Source: awscli/customizations/s3/subcommands.py line ~928
def make_bucket_line(bucket: str) -> bytes:
    return f"make_bucket: {bucket}\n".encode()


def remove_bucket_line(bucket: str) -> bytes:
    return f"remove_bucket: {bucket}\n".encode()


# Source: awscli/customizations/s3/results.py — SUCCESS_FORMAT
def _local(path: str) -> str:
    if path.startswith("./") or path.startswith("/") or path == "-":
        return path
    return f"./{path}"


def upload_line(rel_local: str, bucket: str, key: str) -> bytes:
    return f"upload: {_local(rel_local)} to s3://{bucket}/{key}\n".encode()


def download_line(bucket: str, key: str, rel_local: str) -> bytes:
    return f"download: s3://{bucket}/{key} to {_local(rel_local)}\n".encode()


def copy_line(src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> bytes:
    return f"copy: s3://{src_bucket}/{src_key} to s3://{dest_bucket}/{dest_key}\n".encode()


def move_line(src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> bytes:
    return f"move: s3://{src_bucket}/{src_key} to s3://{dest_bucket}/{dest_key}\n".encode()


def delete_line(bucket: str, key: str) -> bytes:
    return f"delete: s3://{bucket}/{key}\n".encode()


def dryrun_prefix(line: bytes) -> bytes:
    """Prepend the literal '(dryrun) ' prefix used by aws s3 --dryrun."""
    return b"(dryrun) " + line


# `ls` output regexes — used when exact bucket name / date varies.
DATE_RE = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
LS_BUCKET_RE = re.compile(rf"^{DATE_RE} (.+)$")
LS_OBJECT_RE = re.compile(rf"^{DATE_RE} +(\d+) (.+)$")
LS_PRE_RE = re.compile(r"^ {27}PRE (.+)/$")


def assert_contains_line(stdout: bytes, line: bytes) -> None:
    if line not in stdout:
        raise AssertionError(
            f"\nMissing expected line.\nExpected: {line!r}\nGot stdout: {stdout!r}"
        )


def assert_stdout_equals(actual: bytes, expected: bytes) -> None:
    if actual != expected:
        raise AssertionError(
            f"\nStdout mismatch.\nExpected: {expected!r}\nActual: {actual!r}"
        )


def assert_ls_bucket_lines(stdout: bytes, buckets: list[str]) -> None:
    """Assert that `ls` output contains exactly the listed buckets, each on
    a line matching `YYYY-MM-DD HH:MM:SS <bucket>`."""
    lines = stdout.decode().rstrip("\n").split("\n") if stdout.strip() else []
    seen = set()
    for line in lines:
        m = LS_BUCKET_RE.match(line)
        if not m:
            raise AssertionError(f"ls bucket line malformed: {line!r}")
        seen.add(m.group(1))
    if seen != set(buckets):
        raise AssertionError(
            f"ls bucket set mismatch.\nExpected: {set(buckets)}\nGot: {seen}"
        )
