from helpers import format_assertions as fa
from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_rb_isomorphic_force_deletes_many_objects(cli, s3, request):
    iso = IsomorphicTransform(seed=f"rb-force-{request.node.name}")
    bucket = iso.bucket("force-bucket")

    s3.create_bucket(Bucket=bucket)
    for i in range(7):
        key = iso.key(f"obj-{i}")
        s3.put_object(Bucket=bucket, Key=key, Body=f"data-{i}".encode())

    r = cli("s3", "rb", f"s3://{bucket}", "--force")
    assert r.returncode == 0
    assert not moto_state.bucket_exists(s3, bucket)


def test_rb_state_isomorphic_remove_empty(cli, s3, request):
    iso = IsomorphicTransform(seed=f"rb-empty-{request.node.name}")
    bucket = iso.bucket("empty-bucket")

    s3.create_bucket(Bucket=bucket)
    r = cli("s3", "rb", f"s3://{bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.remove_bucket_line(bucket))
    assert not moto_state.bucket_exists(s3, bucket)
