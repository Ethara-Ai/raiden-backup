from helpers import format_assertions as fa
from helpers import moto_state


def test_rb_stdout_state_removes_empty_bucket(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "rb", f"s3://{random_bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.remove_bucket_line(random_bucket))
    assert r.stderr == b""
    assert not moto_state.bucket_exists(s3, random_bucket)


def test_rb_non_empty_without_force_fails(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="blocker.txt", Body=b"x")
    r = cli("s3", "rb", f"s3://{random_bucket}")
    assert r.returncode == 1
    assert b"BucketNotEmpty" in r.stderr
    assert moto_state.bucket_exists(s3, random_bucket)


def test_rb_state_with_force_deletes_all_then_bucket(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="a.txt", Body=b"a")
    s3.put_object(Bucket=random_bucket, Key="b.txt", Body=b"b")

    r = cli("s3", "rb", f"s3://{random_bucket}", "--force")
    assert r.returncode == 0
    assert not moto_state.bucket_exists(s3, random_bucket)


def test_rb_stdout_force_emits_delete_lines(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="x.txt", Body=b"x")

    r = cli("s3", "rb", f"s3://{random_bucket}", "--force")
    assert r.returncode == 0
    assert fa.delete_line(random_bucket, "x.txt") in r.stdout
    assert fa.remove_bucket_line(random_bucket) in r.stdout


def test_rb_invalid_uri_no_prefix(cli):
    r = cli("s3", "rb", "my-bucket")
    assert r.returncode != 0
    assert r.stdout == b""


def test_rb_with_key_in_uri_rejected(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "rb", f"s3://{random_bucket}/some-key")
    assert r.returncode != 0
    assert moto_state.bucket_exists(s3, random_bucket)
