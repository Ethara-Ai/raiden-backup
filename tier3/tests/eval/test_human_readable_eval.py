from hypothesis import HealthCheck, given, settings, strategies as st

from helpers.isomorphic import IsomorphicTransform


_PBT_SETTINGS = settings(
    max_examples=6,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


@_PBT_SETTINGS
@given(size=st.integers(min_value=2, max_value=1023))
def test_hr_n_bytes_plural(cli, s3, request, size):
    iso = IsomorphicTransform(seed=f"tier3-hr-plural-{request.node.name}-{size}")
    bucket = iso.bucket("hr-bucket")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key="f", Body=b"x" * size)

    r = cli("s3", "ls", f"s3://{bucket}/", "--human-readable")
    assert r.returncode == 0
    assert f"{size} Bytes".encode() in r.stdout


def test_hr_one_byte_singular(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier3-hr-one-{request.node.name}")
    bucket = iso.bucket("one-bucket")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key="single", Body=b"x")
    r = cli("s3", "ls", f"s3://{bucket}/", "--human-readable")
    assert r.returncode == 0
    assert b"1 Byte" in r.stdout
    assert b"1 Bytes" not in r.stdout
