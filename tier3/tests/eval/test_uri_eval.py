from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_uri_deep_key_isomorphic(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-uri-deep-{request.node.name}")
    bucket = iso.bucket("deep-bucket")
    s3.create_bucket(Bucket=bucket)
    (tmp_workdir / "f.txt").write_text("data")
    deep_key = "a/b/c/d/e/f.txt"
    r = cli("s3", "cp", "--no-progress", "f.txt", f"s3://{bucket}/{deep_key}")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, bucket, deep_key)


def test_uri_basename_preserve_on_trailing_slash(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-uri-basename-{request.node.name}")
    bucket = iso.bucket("basename-bucket")
    s3.create_bucket(Bucket=bucket)
    (tmp_workdir / "input.bin").write_bytes(b"x" * 10)
    r = cli("s3", "cp", "--no-progress", "input.bin", f"s3://{bucket}/prefix/")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, bucket, "prefix/input.bin")
