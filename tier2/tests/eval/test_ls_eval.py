from helpers.isomorphic import IsomorphicTransform


def test_ls_isomorphic_object_listing(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier2-ls-{request.node.name}")
    bucket = iso.bucket("ls-bucket")
    key = iso.key("ls-key")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=key, Body=b"x")
    r = cli("s3", "ls", f"s3://{bucket}/", "--recursive")
    assert r.returncode == 0
    assert key.encode() in r.stdout


def test_ls_isomorphic_summarize(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier2-ls-sum-{request.node.name}")
    bucket = iso.bucket("sum-bucket")
    s3.create_bucket(Bucket=bucket)
    for i in range(3):
        s3.put_object(Bucket=bucket, Key=iso.key(f"k-{i}"), Body=b"abc")
    r = cli("s3", "ls", f"s3://{bucket}/", "--recursive", "--summarize")
    assert r.returncode == 0
    assert b"Total Objects: 3" in r.stdout
    assert b"Total Size: 9" in r.stdout


def test_ls_isomorphic_missing_prefix_exit_1(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier2-ls-miss-{request.node.name}")
    bucket = iso.bucket("miss-bucket")
    s3.create_bucket(Bucket=bucket)
    r = cli("s3", "ls", f"s3://{bucket}/never-exists-{iso.rng.randbytes(2).hex()}/")
    assert r.returncode == 1
