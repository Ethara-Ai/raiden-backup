from helpers import format_assertions as fa
from helpers import moto_state


def test_cp_upload_stdout_state(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "hello.txt").write_text("hi")
    r = cli("s3", "cp", "--no-progress", "hello.txt", f"s3://{random_bucket}/hello.txt")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.upload_line("hello.txt", random_bucket, "hello.txt"))
    assert moto_state.object_exists(s3, random_bucket, "hello.txt")
    assert moto_state.object_body(s3, random_bucket, "hello.txt") == b"hi"


def test_cp_upload_preserves_bytes(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    payload = bytes(range(256)) * 4
    (tmp_workdir / "raw.bin").write_bytes(payload)
    r = cli("s3", "cp", "--no-progress", "raw.bin", f"s3://{random_bucket}/raw.bin")
    assert r.returncode == 0
    assert moto_state.object_body(s3, random_bucket, "raw.bin") == payload


def test_cp_upload_to_trailing_slash_uses_basename(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "a.txt").write_text("a")
    r = cli("s3", "cp", "--no-progress", "a.txt", f"s3://{random_bucket}/")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "a.txt")


def test_cp_upload_dryrun_no_state_change(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "f.txt").write_text("data")
    r = cli("s3", "cp", "--no-progress", "f.txt", f"s3://{random_bucket}/f.txt", "--dryrun")
    assert r.returncode == 0
    assert fa.dryrun_prefix(fa.upload_line("f.txt", random_bucket, "f.txt")) in r.stdout
    assert not moto_state.object_exists(s3, random_bucket, "f.txt")


def test_cp_upload_missing_source_fails(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "cp", "--no-progress", "nonexistent.txt", f"s3://{random_bucket}/x.txt")
    assert r.returncode != 0
    assert not moto_state.object_exists(s3, random_bucket, "x.txt")


def test_cp_upload_to_missing_bucket_fails(cli, tmp_workdir):
    (tmp_workdir / "f.txt").write_text("x")
    r = cli("s3", "cp", "--no-progress", "f.txt", "s3://no-such-bucket-xyz/f.txt")
    assert r.returncode == 1


def test_cp_upload_quiet_suppresses_success(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "q.txt").write_text("q")
    r = cli("s3", "cp", "--no-progress", "q.txt", f"s3://{random_bucket}/q.txt", "--quiet")
    assert r.returncode == 0
    assert r.stdout == b""
    assert moto_state.object_exists(s3, random_bucket, "q.txt")
