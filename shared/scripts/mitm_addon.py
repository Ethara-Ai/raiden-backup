"""Rewrite S3 hosts to local moto. Matches s3.amazonaws.com,
s3.<region>.amazonaws.com, s3-<region>.amazonaws.com, s3-accelerate.amazonaws.com,
and virtual-hosted-style <bucket>.s3*.amazonaws.com. Bucket is hoisted into
path-style before forwarding so moto routes uniformly."""
from __future__ import annotations

import re

from mitmproxy import http

_S3_HOST_RE = re.compile(
    r'^(?P<bucket>(?:[^.]+\.)*?[^.]+\.)?s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$',
    re.IGNORECASE,
)


def request(flow: http.HTTPFlow) -> None:
    host = flow.request.host
    match = _S3_HOST_RE.match(host)
    if not match:
        return

    bucket = match.group('bucket')
    if bucket:
        bucket = bucket.rstrip('.')
        flow.request.path = f"/{bucket}{flow.request.path}"

    flow.request.scheme = 'http'
    flow.request.host = '127.0.0.1'
    flow.request.port = 5000
    flow.request.headers['Host'] = '127.0.0.1:5000'
