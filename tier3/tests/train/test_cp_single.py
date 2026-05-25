from helpers import format_assertions as fa
from helpers import moto_state


def test_cp_upload_single(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "f.txt").write_text("up")
    r = cli("s3", "cp", "--no-progress", "f.txt", f"s3://{random_bucket}/f.txt")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.upload_line("f.txt", random_bucket, "f.txt"))


def test_cp_download_single(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="f.txt", Body=b"down")
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/f.txt", "out.txt")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.download_line(random_bucket, "f.txt", "out.txt"))
    assert (tmp_workdir / "out.txt").read_bytes() == b"down"


def test_cp_upload_trailing_slash_dest(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "x.txt").write_text("x")
    r = cli("s3", "cp", "--no-progress", "x.txt", f"s3://{random_bucket}/")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "x.txt")


def test_cp_upload_to_keyed_dest_uses_dest_key(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "src.txt").write_text("src")
    r = cli("s3", "cp", "--no-progress", "src.txt", f"s3://{random_bucket}/sub/dest.txt")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "sub/dest.txt")


def test_cp_local_to_local_rejected(cli, tmp_workdir):
    (tmp_workdir / "a.txt").write_text("a")
    r = cli("s3", "cp", "--no-progress", "a.txt", "b.txt")
    assert r.returncode != 0


def test_cp_missing_local_source(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "cp", "--no-progress", "nope.txt", f"s3://{random_bucket}/x.txt")
    assert r.returncode != 0


def test_cp_dryrun_no_state(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "f.txt").write_text("x")
    r = cli("s3", "cp", "--no-progress", "f.txt", f"s3://{random_bucket}/f.txt", "--dryrun")
    assert r.returncode == 0
    assert fa.dryrun_prefix(fa.upload_line("f.txt", random_bucket, "f.txt")) in r.stdout
    assert not moto_state.object_exists(s3, random_bucket, "f.txt")
