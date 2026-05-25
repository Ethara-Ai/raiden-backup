from helpers import format_assertions as fa
from helpers import moto_state


def test_mb_stdout_state_happy_path(cli, s3, random_bucket):
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.make_bucket_line(random_bucket))
    assert r.stderr == b""
    assert moto_state.bucket_exists(s3, random_bucket)


def test_mb_state_bucket_appears_in_list(cli, s3, random_bucket):
    cli("s3", "mb", f"s3://{random_bucket}")
    buckets = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    assert random_bucket in buckets


def test_mb_state_idempotent_owned_fails(cli, s3, random_bucket, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    s3.create_bucket(
        Bucket=random_bucket,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 1
    assert b"BucketAlreadyOwnedByYou" in r.stderr


def test_mb_stdout_no_extra_lines(cli, s3, random_bucket):
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    assert r.stdout.count(b"\n") == 1


def test_mb_invalid_uri_no_prefix(cli):
    r = cli("s3", "mb", "my-bucket")
    assert r.returncode != 0
    assert r.stdout == b""


def test_mb_state_us_east_1_no_location_constraint(cli, s3, random_bucket, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    assert moto_state.bucket_exists(s3, random_bucket)
