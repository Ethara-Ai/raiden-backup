from helpers import format_assertions as fa
from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_cp_upload_isomorphic_state(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier2-cp-up-{request.node.name}")
    bucket = iso.bucket("up-bucket")
    key = iso.key("upload-target")
    s3.create_bucket(Bucket=bucket)
    (tmp_workdir / "src.txt").write_text("iso-content")
    r = cli("s3", "cp", "--no-progress", "src.txt", f"s3://{bucket}/{key}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.upload_line("src.txt", bucket, key))
    assert moto_state.object_body(s3, bucket, key) == b"iso-content"


def test_cp_download_isomorphic_state(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier2-cp-down-{request.node.name}")
    bucket = iso.bucket("down-bucket")
    key = iso.key("download-target")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=key, Body=b"down-iso-payload")
    r = cli("s3", "cp", "--no-progress", f"s3://{bucket}/{key}", "out.txt")
    assert r.returncode == 0
    assert (tmp_workdir / "out.txt").read_bytes() == b"down-iso-payload"


def test_cp_roundtrip_isomorphic(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier2-cp-rt-{request.node.name}")
    bucket = iso.bucket("rt-bucket")
    key = iso.key("roundtrip")
    payload = bytes(range(128)) * 3
    s3.create_bucket(Bucket=bucket)
    (tmp_workdir / "in.bin").write_bytes(payload)
    cli("s3", "cp", "--no-progress", "in.bin", f"s3://{bucket}/{key}")
    cli("s3", "cp", "--no-progress", f"s3://{bucket}/{key}", "out.bin")
    assert (tmp_workdir / "out.bin").read_bytes() == payload


def test_cp_dryrun_isomorphic_no_state(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier2-cp-dry-{request.node.name}")
    bucket = iso.bucket("dry-bucket")
    key = iso.key("dry-target")
    s3.create_bucket(Bucket=bucket)
    (tmp_workdir / "f.txt").write_text("x")
    r = cli("s3", "cp", "--no-progress", "f.txt", f"s3://{bucket}/{key}", "--dryrun")
    assert r.returncode == 0
    assert b"(dryrun) upload:" in r.stdout
    assert not moto_state.object_exists(s3, bucket, key)
