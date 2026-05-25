from helpers import moto_state


def test_uri_key_with_slashes(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    (tmp_workdir / "f.txt").write_text("data")
    r = cli("s3", "cp", "--no-progress", "f.txt", f"s3://{random_bucket}/a/b/c/f.txt")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "a/b/c/f.txt")


def test_uri_no_prefix_fatal(cli):
    r = cli("s3", "mb", "not-an-s3-uri")
    assert r.returncode != 0


def test_uri_bucket_only_normalized(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="x-key", Body=b"x")
    r = cli("s3", "ls", f"s3://{random_bucket}")
    assert r.returncode == 0
    assert b"x-key" in r.stdout


def test_uri_split_first_slash_only(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="a/b/c", Body=b"deep")
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/a/b/c", "out.txt")
    assert r.returncode == 0
    assert (tmp_workdir / "out.txt").read_bytes() == b"deep"
