from helpers import format_assertions as fa


def test_cp_download_stdout_state(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="src.txt", Body=b"down")
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/src.txt", "dst.txt")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.download_line(random_bucket, "src.txt", "dst.txt"))
    assert (tmp_workdir / "dst.txt").read_bytes() == b"down"


def test_cp_download_missing_key_fails(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/missing", "dst.txt")
    assert r.returncode == 1
    assert not (tmp_workdir / "dst.txt").exists()


def test_cp_download_preserves_bytes(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    payload = b"\x00\x01\xff\xfe" * 4096
    s3.put_object(Bucket=random_bucket, Key="b.bin", Body=payload)
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/b.bin", "out.bin")
    assert r.returncode == 0
    assert (tmp_workdir / "out.bin").read_bytes() == payload


def test_cp_download_dryrun_no_local_file(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="a", Body=b"a")
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/a", "out.txt", "--dryrun")
    assert r.returncode == 0
    assert b"(dryrun) download:" in r.stdout
    assert not (tmp_workdir / "out.txt").exists()
