from helpers import format_assertions as fa
from helpers import moto_state


def test_mv_s3_s3_deletes_source(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key="src.txt", Body=b"data")
    r = cli("s3", "mv", "--no-progress", f"s3://{src_bucket}/src.txt", f"s3://{dst_bucket}/dst.txt")
    assert r.returncode == 0
    assert fa.move_line(src_bucket, "src.txt", dst_bucket, "dst.txt") in r.stdout
    assert moto_state.object_body(s3, dst_bucket, "dst.txt") == b"data"
    assert not moto_state.object_exists(s3, src_bucket, "src.txt")


def test_mv_upload_deletes_local(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "f.txt").write_text("up")
    r = cli("s3", "mv", "--no-progress", "f.txt", f"s3://{random_bucket}/f.txt")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "f.txt")
    assert not (tmp_workdir / "f.txt").exists()


def test_mv_download_deletes_s3(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="f.txt", Body=b"data")
    r = cli("s3", "mv", "--no-progress", f"s3://{random_bucket}/f.txt", "out.txt")
    assert r.returncode == 0
    assert (tmp_workdir / "out.txt").read_bytes() == b"data"
    assert not moto_state.object_exists(s3, random_bucket, "f.txt")


def test_mv_self_move_rejected(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="k", Body=b"x")
    r = cli("s3", "mv", "--no-progress", f"s3://{random_bucket}/k", f"s3://{random_bucket}/k")
    assert r.returncode != 0
    assert moto_state.object_exists(s3, random_bucket, "k")


def test_mv_failed_copy_preserves_source(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="k", Body=b"x")
    r = cli("s3", "mv", "--no-progress", f"s3://{random_bucket}/k", "s3://no-such-bucket-zzz/k")
    assert r.returncode == 1
    assert moto_state.object_exists(s3, random_bucket, "k")


def test_mv_recursive_s3_s3(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    for k in ("a.txt", "sub/b.txt"):
        s3.put_object(Bucket=src_bucket, Key=k, Body=k.encode())

    r = cli("s3", "mv", "--no-progress", f"s3://{src_bucket}/", f"s3://{dst_bucket}/", "--recursive")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, dst_bucket, "a.txt")
    assert moto_state.object_exists(s3, dst_bucket, "sub/b.txt")
    assert moto_state.list_keys(s3, src_bucket) == []


def test_mv_dryrun_no_state(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key="k", Body=b"x")
    r = cli("s3", "mv", "--no-progress", f"s3://{src_bucket}/k", f"s3://{dst_bucket}/k", "--dryrun")
    assert r.returncode == 0
    assert b"(dryrun) move:" in r.stdout
    assert moto_state.object_exists(s3, src_bucket, "k")
    assert not moto_state.object_exists(s3, dst_bucket, "k")
