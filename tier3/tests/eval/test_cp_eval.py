from helpers import format_assertions as fa
from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_cp_recursive_isomorphic_roundtrip(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-cp-rt-{request.node.name}")
    bucket = iso.bucket("rt-bucket")
    s3.create_bucket(Bucket=bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    for name in ("alpha.txt", "beta.txt"):
        (src / name).write_text(name)

    cli("s3", "cp", "--no-progress", "src/", f"s3://{bucket}/", "--recursive")
    cli("s3", "cp", "--no-progress", f"s3://{bucket}/", "out/", "--recursive")

    assert (tmp_workdir / "out" / "alpha.txt").read_text() == "alpha.txt"
    assert (tmp_workdir / "out" / "beta.txt").read_text() == "beta.txt"


def test_cp_s3_s3_isomorphic_stdout(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier3-cp-s3-{request.node.name}")
    src_bucket = iso.bucket("src-bucket")
    dst_bucket = iso.bucket("dst-bucket")
    key = iso.key("transfer-key")
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key=key, Body=b"iso")

    r = cli("s3", "cp", "--no-progress", f"s3://{src_bucket}/{key}", f"s3://{dst_bucket}/{key}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.copy_line(src_bucket, key, dst_bucket, key))


def test_cp_recursive_state_isomorphic(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-cp-state-{request.node.name}")
    bucket = iso.bucket("state-bucket")
    s3.create_bucket(Bucket=bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "x.txt").write_text("x")
    (src / "deep").mkdir()
    (src / "deep" / "y.txt").write_text("y")

    r = cli("s3", "cp", "--no-progress", "src/", f"s3://{bucket}/", "--recursive")
    assert r.returncode == 0
    keys = set(moto_state.list_keys(s3, bucket))
    assert keys == {"x.txt", "deep/y.txt"}
