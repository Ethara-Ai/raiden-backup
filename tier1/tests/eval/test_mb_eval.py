import pytest

from helpers import format_assertions as fa
from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


def test_mb_isomorphic_stdout(cli, s3, request):
    iso = IsomorphicTransform(seed=f"mb-eval-{request.node.name}")
    bucket = iso.bucket("logical-test-bucket")

    r = cli("s3", "mb", f"s3://{bucket}")
    assert r.returncode == 0
    fa.assert_stdout_equals(r.stdout, fa.make_bucket_line(bucket))


def test_mb_state_isomorphic_appears_in_list(cli, s3, request):
    iso = IsomorphicTransform(seed=f"mb-state-{request.node.name}")
    bucket = iso.bucket("eval-bucket")

    cli("s3", "mb", f"s3://{bucket}")
    assert moto_state.bucket_exists(s3, bucket)
