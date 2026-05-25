from helpers import format_assertions as fa
from helpers import moto_state


def test_mb_basic(cli, s3, random_bucket):
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.make_bucket_line(random_bucket))
    assert moto_state.bucket_exists(s3, random_bucket)


def test_mb_state_already_owned(cli, s3, random_bucket, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    s3.create_bucket(
        Bucket=random_bucket,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    r = cli("s3", "mb", f"s3://{random_bucket}")
    assert r.returncode == 1
    assert b"BucketAlreadyOwnedByYou" in r.stderr


def test_rb_force_with_many_objects(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    for i in range(15):
        s3.put_object(Bucket=random_bucket, Key=f"dir/sub/o-{i}.txt", Body=f"d-{i}".encode())
    r = cli("s3", "rb", f"s3://{random_bucket}", "--force")
    assert r.returncode == 0
    assert not moto_state.bucket_exists(s3, random_bucket)


def test_rb_non_empty_no_force(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="x", Body=b"x")
    r = cli("s3", "rb", f"s3://{random_bucket}")
    assert r.returncode == 1
    assert moto_state.bucket_exists(s3, random_bucket)
