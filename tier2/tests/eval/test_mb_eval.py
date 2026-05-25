from helpers import format_assertions as fa
from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_mb_isomorphic(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier2-mb-{request.node.name}")
    bucket = iso.bucket("eval-bucket-mb")
    r = cli("s3", "mb", f"s3://{bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.make_bucket_line(bucket))
    assert moto_state.bucket_exists(s3, bucket)


def test_mb_state_isomorphic_two_buckets(cli, s3, request):
    iso = IsomorphicTransform(seed=f"tier2-mb-two-{request.node.name}")
    a = iso.bucket("alpha")
    b = iso.bucket("beta")
    cli("s3", "mb", f"s3://{a}")
    cli("s3", "mb", f"s3://{b}")
    names = {bb["Name"] for bb in s3.list_buckets().get("Buckets", [])}
    assert {a, b}.issubset(names)
