from helpers.isomorphic import IsomorphicTransform


def test_ls_recursive_isomorphic(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier3-ls-rec-{request.node.name}")
    bucket = iso.bucket("ls-rec-bucket")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key="root", Body=b"r")
    s3.put_object(Bucket=bucket, Key="deep/leaf", Body=b"d")

    r = cli("s3", "ls", f"s3://{bucket}/", "--recursive")
    assert r.returncode == 0
    assert b"PRE" not in r.stdout
    assert b"deep/leaf" in r.stdout


def test_ls_summarize_isomorphic(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier3-ls-sum-{request.node.name}")
    bucket = iso.bucket("sum-bucket")
    s3.create_bucket(Bucket=bucket)
    for i in range(4):
        s3.put_object(Bucket=bucket, Key=iso.key(f"k-{i}"), Body=b"ab")

    r = cli("s3", "ls", f"s3://{bucket}/", "--recursive", "--summarize")
    assert r.returncode == 0
    assert b"Total Objects: 4" in r.stdout
    assert b"Total Size: 8" in r.stdout


def test_ls_human_readable_kib_boundary_isomorphic(cli, s3, request):
    import re
    iso = IsomorphicTransform(seed=f"tier3-ls-kib-{request.node.name}")
    bucket = iso.bucket("kib-bucket")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key="x", Body=b"a" * 2048)
    r = cli("s3", "ls", f"s3://{bucket}/", "--human-readable")
    assert r.returncode == 0
    assert re.search(rb"2\.0\s+KiB", r.stdout)
