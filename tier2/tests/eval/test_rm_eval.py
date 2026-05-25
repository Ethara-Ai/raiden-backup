from helpers import format_assertions as fa
from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_rm_isomorphic_state(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier2-rm-{request.node.name}")
    bucket = iso.bucket("rm-bucket")
    key = iso.key("rm-target")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=key, Body=b"x")
    r = cli("s3", "rm", f"s3://{bucket}/{key}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.delete_line(bucket, key))
    assert not moto_state.object_exists(s3, bucket, key)
