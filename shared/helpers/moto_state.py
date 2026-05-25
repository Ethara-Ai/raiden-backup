"""moto state helpers: reset, fixture setup, post-test assertions.

The boto3 client returned here is the GROUND TRUTH — used by tests to verify
that the agent's CLI actually mutated S3 state correctly. The agent cannot
intercept this client; it talks to moto directly.
"""
import os
import boto3
import requests

MOTO_ENDPOINT = os.environ.get("S3RL_MOTO_URL") or "http://127.0.0.1:5000"


def reset_moto() -> None:
    """Wipe all moto state. Instant in-memory operation."""
    requests.post(f"{MOTO_ENDPOINT}/moto-api/reset", timeout=5)


def make_s3_client():
    """Return an authoritative boto3 S3 client pointed at moto."""
    return boto3.client(
        "s3",
        endpoint_url=MOTO_ENDPOINT,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="us-east-1",
    )


def bucket_exists(s3, name: str) -> bool:
    return name in {b["Name"] for b in s3.list_buckets().get("Buckets", [])}


def object_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError:
        return False


def object_body(s3, bucket: str, key: str) -> bytes:
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def list_keys(s3, bucket: str, prefix: str = "") -> list[str]:
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            keys.append(obj["Key"])
    return sorted(keys)
