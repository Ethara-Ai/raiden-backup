import re

from helpers import format_assertions as fa


def test_ls_buckets(cli, s3):
    s3.create_bucket(Bucket="alpha-x")
    s3.create_bucket(Bucket="beta-x")
    r = cli("s3", "ls")
    fa.assert_ls_bucket_lines(r.stdout, ["alpha-x", "beta-x"])


def test_ls_recursive_no_pre_lines(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="root.txt", Body=b"r")
    s3.put_object(Bucket=random_bucket, Key="sub/deep.txt", Body=b"d")
    r = cli("s3", "ls", f"s3://{random_bucket}/", "--recursive")
    assert r.returncode == 0
    assert b"PRE" not in r.stdout
    assert b"root.txt" in r.stdout
    assert b"sub/deep.txt" in r.stdout


def test_ls_pre_for_subdirs(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="sub/x.txt", Body=b"x")
    s3.put_object(Bucket=random_bucket, Key="root.txt", Body=b"r")
    r = cli("s3", "ls", f"s3://{random_bucket}/")
    assert r.returncode == 0
    assert b"PRE sub/" in r.stdout
    assert b"root.txt" in r.stdout


def test_ls_human_readable_1_byte_singular(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="one.txt", Body=b"a")
    r = cli("s3", "ls", f"s3://{random_bucket}/", "--human-readable")
    assert r.returncode == 0
    assert b"1 Byte" in r.stdout and b"1 Bytes" not in r.stdout


def test_ls_human_readable_kib_boundary(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="k.bin", Body=b"x" * 1024)
    r = cli("s3", "ls", f"s3://{random_bucket}/", "--human-readable")
    assert r.returncode == 0
    assert re.search(rb"1\.0\s+KiB", r.stdout)


def test_ls_missing_prefix_exit_1(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "ls", f"s3://{random_bucket}/missing/")
    assert r.returncode == 1
