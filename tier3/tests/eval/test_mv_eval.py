from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_mv_isomorphic_deletes_source(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier3-mv-{request.node.name}")
    src_bucket = iso.bucket("mv-src")
    dst_bucket = iso.bucket("mv-dst")
    key = iso.key("mv-key")
    s3.create_bucket(Bucket=src_bucket)
    s3.create_bucket(Bucket=dst_bucket)
    s3.put_object(Bucket=src_bucket, Key=key, Body=b"mv-payload")

    r = cli("s3", "mv", "--no-progress", f"s3://{src_bucket}/{key}", f"s3://{dst_bucket}/{key}")
    assert r.returncode == 0
    assert moto_state.object_body(s3, dst_bucket, key) == b"mv-payload"
    assert not moto_state.object_exists(s3, src_bucket, key)


def test_mv_self_move_isomorphic_rejected(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier3-mv-self-{request.node.name}")
    bucket = iso.bucket("self-bucket")
    key = iso.key("self-key")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=key, Body=b"keep")

    r = cli("s3", "mv", "--no-progress", f"s3://{bucket}/{key}", f"s3://{bucket}/{key}")
    assert r.returncode != 0
    assert moto_state.object_body(s3, bucket, key) == b"keep"
