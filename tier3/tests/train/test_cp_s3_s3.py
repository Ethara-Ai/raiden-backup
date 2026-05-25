from helpers import format_assertions as fa
from helpers import moto_state


def test_cp_s3_s3_single(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key="src.txt", Body=b"data")
    r = cli("s3", "cp", "--no-progress", f"s3://{src_bucket}/src.txt", f"s3://{dst_bucket}/dst.txt")
    assert r.returncode == 0
    fa.assert_stdout_equals(
        r.stdout, fa.copy_line(src_bucket, "src.txt", dst_bucket, "dst.txt")
    )
    assert moto_state.object_body(s3, dst_bucket, "dst.txt") == b"data"
    assert moto_state.object_exists(s3, src_bucket, "src.txt")


def test_cp_s3_s3_same_bucket(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="a.txt", Body=b"x")
    r = cli("s3", "cp", "--no-progress", f"s3://{random_bucket}/a.txt", f"s3://{random_bucket}/b.txt")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "a.txt")
    assert moto_state.object_exists(s3, random_bucket, "b.txt")


def test_cp_s3_s3_trailing_slash_basename(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key="a/x.txt", Body=b"x")
    r = cli("s3", "cp", "--no-progress", f"s3://{src_bucket}/a/x.txt", f"s3://{dst_bucket}/")
    assert r.returncode == 0
    assert moto_state.object_exists(s3, dst_bucket, "x.txt")


def test_cp_s3_s3_missing_source(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    r = cli("s3", "cp", "--no-progress", f"s3://{src_bucket}/missing", f"s3://{dst_bucket}/x")
    assert r.returncode == 1


def test_cp_s3_s3_dryrun_no_state(cli, s3, random_bucket):
    src_bucket = random_bucket
    dst_bucket = f"{random_bucket}-dst"
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key="a", Body=b"a")
    r = cli("s3", "cp", "--no-progress", f"s3://{src_bucket}/a", f"s3://{dst_bucket}/b", "--dryrun")
    assert r.returncode == 0
    assert b"(dryrun) copy:" in r.stdout
    assert not moto_state.object_exists(s3, dst_bucket, "b")
