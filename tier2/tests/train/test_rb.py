from helpers import format_assertions as fa
from helpers import moto_state


def test_rb_empty_bucket_happy(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "rb", f"s3://{random_bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.remove_bucket_line(random_bucket))
    assert not moto_state.bucket_exists(s3, random_bucket)


def test_rb_non_empty_no_force_fails(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="x", Body=b"x")
    r = cli("s3", "rb", f"s3://{random_bucket}")
    assert r.returncode == 1
    assert b"BucketNotEmpty" in r.stderr
    assert moto_state.bucket_exists(s3, random_bucket)


def test_rb_force_state_clean(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    for k in ("a.txt", "b.txt", "deep/c.txt"):
        s3.put_object(Bucket=random_bucket, Key=k, Body=b"x")
    r = cli("s3", "rb", f"s3://{random_bucket}", "--force")
    assert r.returncode == 0
    assert not moto_state.bucket_exists(s3, random_bucket)


def test_rb_invalid_uri_with_key(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "rb", f"s3://{random_bucket}/has-key")
    assert r.returncode != 0
    assert moto_state.bucket_exists(s3, random_bucket)
