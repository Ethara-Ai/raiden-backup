from helpers import moto_state


def test_cp_recursive_upload(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    (src / "b.txt").write_text("b")
    (src / "sub").mkdir()
    (src / "sub" / "c.txt").write_text("c")

    r = cli("s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/", "--recursive")
    assert r.returncode == 0
    keys = set(moto_state.list_keys(s3, random_bucket))
    assert keys == {"a.txt", "b.txt", "sub/c.txt"}


def test_cp_recursive_download(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    for k, v in [("a.txt", b"a"), ("b.txt", b"b"), ("sub/c.txt", b"c")]:
        s3.put_object(Bucket=random_bucket, Key=k, Body=v)

    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/", "out/", "--recursive")
    assert r.returncode == 0
    assert (tmp_workdir / "out" / "a.txt").read_text() == "a"
    assert (tmp_workdir / "out" / "b.txt").read_text() == "b"
    assert (tmp_workdir / "out" / "sub" / "c.txt").read_text() == "c"


def test_cp_recursive_creates_local_dest_dir(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="only.txt", Body=b"x")
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/", "newdir/", "--recursive")
    assert r.returncode == 0
    assert (tmp_workdir / "newdir" / "only.txt").exists()


def test_cp_recursive_s3_to_s3(cli, s3, random_bucket, tmp_workdir):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key="a.txt", Body=b"a")
    s3.put_object(Bucket=src_bucket, Key="sub/b.txt", Body=b"b")

    r = cli("s3", "cp", "--no-progress", f"s3://{src_bucket}/", f"s3://{dst_bucket}/", "--recursive")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, dst_bucket, "a.txt")
    assert moto_state.object_exists(s3, dst_bucket, "sub/b.txt")


def test_cp_recursive_skips_non_matching(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "keep.txt").write_text("keep")
    (src / "drop.log").write_text("drop")

    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/",
        "--recursive", "--exclude", "*", "--include", "*.txt",
    )
    assert r.returncode == 0
    keys = set(moto_state.list_keys(s3, random_bucket))
    assert keys == {"keep.txt"}


def test_cp_recursive_dryrun_no_state(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    r = cli("s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/", "--recursive", "--dryrun")
    assert r.returncode == 0
    assert b"(dryrun) upload:" in r.stdout
    assert moto_state.list_keys(s3, random_bucket) == []
