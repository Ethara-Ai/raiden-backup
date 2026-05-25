from helpers import format_assertions as fa
from helpers import moto_state


def test_rm_stdout_state(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="rm-me.txt", Body=b"x")
    r = cli("s3", "rm", f"s3://{random_bucket}/rm-me.txt")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.delete_line(random_bucket, "rm-me.txt"))
    assert not moto_state.object_exists(s3, random_bucket, "rm-me.txt")


def test_rm_nonexistent_key_exits_zero(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    r = cli("s3", "rm", f"s3://{random_bucket}/never-existed")
    assert r.returncode == 0
    assert fa.delete_line(random_bucket, "never-existed") in r.stdout


def test_rm_dryrun_no_state_change(cli, s3, random_bucket):
    s3.create_bucket(Bucket=random_bucket)
    s3.put_object(Bucket=random_bucket, Key="keep.txt", Body=b"x")
    r = cli("s3", "rm", f"s3://{random_bucket}/keep.txt", "--dryrun")
    assert r.returncode == 0
    assert fa.dryrun_prefix(fa.delete_line(random_bucket, "keep.txt")) in r.stdout
    assert moto_state.object_exists(s3, random_bucket, "keep.txt")
