from helpers import format_assertions as fa
from helpers import moto_state


def test_rm_single(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="k", Body=b"x")
    r = cli("s3", "rm", f"s3://{random_bucket}/k")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.delete_line(random_bucket, "k"))
    assert not moto_state.object_exists(s3, random_bucket, "k")


def test_rm_recursive_removes_all(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    for i in range(5):
        s3.put_object(Bucket=random_bucket, Key=f"k-{i}", Body=b"x")
    r = cli("s3", "rm", f"s3://{random_bucket}/", "--recursive")
    assert r.returncode == 0
    assert moto_state.list_keys(s3, random_bucket) == []


def test_rm_recursive_filter(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="keep.txt", Body=b"k")
    s3.put_object(Bucket=random_bucket, Key="drop.log", Body=b"d")
    r = cli(
        "s3", "rm", f"s3://{random_bucket}/",
        "--recursive", "--exclude", "*", "--include", "*.log",
    )
    assert r.returncode == 0
    assert moto_state.object_exists(s3, random_bucket, "keep.txt")
    assert not moto_state.object_exists(s3, random_bucket, "drop.log")


def test_rm_nonexistent_exits_zero(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "rm", f"s3://{random_bucket}/never-existed")
    assert r.returncode == 0
    assert fa.delete_line(random_bucket, "never-existed") in r.stdout
