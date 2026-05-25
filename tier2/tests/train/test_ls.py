import re

from helpers import format_assertions as fa


def test_ls_buckets_format(cli, s3):
    s3.create_bucket(Bucket="bucket-alpha")
    s3.create_bucket(Bucket="bucket-beta")
    r = cli("s3", "ls")
    assert r.returncode == 0
    fa.assert_ls_bucket_lines(r.stdout, ["bucket-alpha", "bucket-beta"])


def test_ls_empty_bucket_exits_zero(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "ls", f"s3://{random_bucket}/", "--summarize")
    assert r.returncode == 0
    assert b"Total Objects: 0" in r.stdout


def test_ls_missing_prefix_exits_one(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "ls", f"s3://{random_bucket}/missing-prefix/")
    assert r.returncode == 1


def test_ls_objects_show_basename(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="hello.txt", Body=b"hello")
    r = cli("s3", "ls", f"s3://{random_bucket}/")
    assert r.returncode == 0
    assert b"hello.txt" in r.stdout
    assert re.search(rb"\b5\s+hello\.txt", r.stdout)


def test_ls_summarize_block(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="a.txt", Body=b"aaa")
    s3.put_object(Bucket=random_bucket, Key="b.txt", Body=b"bbbb")
    r = cli("s3", "ls", f"s3://{random_bucket}/", "--summarize")
    assert r.returncode == 0
    assert b"Total Objects: 2" in r.stdout
    assert b"Total Size: 7" in r.stdout
