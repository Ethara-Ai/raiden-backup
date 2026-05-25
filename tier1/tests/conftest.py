import os
import subprocess
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/opt/s3rl-verifier")

from helpers import moto_state

pytest_plugins = ["helpers.markers"]


TRIAL_NAMESPACE = os.environ.get("RL_TRIAL_NAMESPACE", uuid.uuid4().hex[:6])


@pytest.fixture(autouse=True)
def reset_moto():
    requests.post(f"{moto_state.MOTO_ENDPOINT}/moto-api/reset", timeout=5)
    yield


@pytest.fixture
def s3():
    return moto_state.make_s3_client()


@pytest.fixture
def random_bucket():
    return f"b-{TRIAL_NAMESPACE}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def tmp_workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def cli(tmp_workdir):
    def _run(*args, input_bytes=None, timeout=60):
        return subprocess.run(
            ["/app/awscli", *args],
            input=input_bytes,
            env=os.environ.copy(),
            capture_output=True,
            timeout=timeout,
            cwd=str(tmp_workdir),
        )
    return _run
