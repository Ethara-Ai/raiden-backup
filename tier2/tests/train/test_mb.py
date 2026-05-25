from helpers import format_assertions as fa
from helpers import moto_state


def test_mb_stdout_state_happy(cli, s3, random_bucket):
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.make_bucket_line(random_bucket))
    assert moto_state.bucket_exists(s3, random_bucket)


def test_mb_state_duplicate_fails(cli, s3, random_bucket, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    s3.create_bucket(
        Bucket=random_bucket,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 1
    assert b"BucketAlreadyOwnedByYou" in r.stderr


def test_mb_invalid_uri(cli):
    r = cli("s3", "mb", "no-prefix")
    assert r.returncode != 0


def test_mb_state_us_east_1(cli, s3, random_bucket, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    assert moto_state.bucket_exists(s3, random_bucket)


def test_mb_stdout_no_trailing_garbage(cli, s3, random_bucket):
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    assert r.stdout == fa.make_bucket_line(random_bucket)
    assert r.stderr == b""
