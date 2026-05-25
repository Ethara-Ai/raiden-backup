"""Unit tests for shared/helpers/* — runnable WITHOUT Docker, moto, or Harbor.

Validates the test infrastructure itself before we trust it as the
ground truth in real test runs. Run with:

    python -m pytest tools/test_helpers.py -v
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import pytest


def test_format_assertions_make_bucket_line():
    from helpers import format_assertions as fa
    assert fa.make_bucket_line("foo") == b"make_bucket: foo\n"


def test_format_assertions_remove_bucket_line():
    from helpers import format_assertions as fa
    assert fa.remove_bucket_line("foo") == b"remove_bucket: foo\n"


def test_format_assertions_upload_line():
    from helpers import format_assertions as fa
    assert fa.upload_line("a.txt", "b", "k") == b"upload: ./a.txt to s3://b/k\n"
    assert fa.upload_line("./a.txt", "b", "k") == b"upload: ./a.txt to s3://b/k\n"
    assert fa.upload_line("/abs/a.txt", "b", "k") == b"upload: /abs/a.txt to s3://b/k\n"
    assert fa.upload_line("-", "b", "k") == b"upload: - to s3://b/k\n"


def test_format_assertions_download_line():
    from helpers import format_assertions as fa
    assert fa.download_line("b", "k", "a.txt") == b"download: s3://b/k to ./a.txt\n"
    assert fa.download_line("b", "k", "-") == b"download: s3://b/k to -\n"


def test_format_assertions_copy_line():
    from helpers import format_assertions as fa
    assert fa.copy_line("b1", "k1", "b2", "k2") == b"copy: s3://b1/k1 to s3://b2/k2\n"


def test_format_assertions_move_line():
    from helpers import format_assertions as fa
    assert fa.move_line("b1", "k1", "b2", "k2") == b"move: s3://b1/k1 to s3://b2/k2\n"


def test_format_assertions_delete_line():
    from helpers import format_assertions as fa
    assert fa.delete_line("b", "k") == b"delete: s3://b/k\n"


def test_format_assertions_dryrun_prefix():
    from helpers import format_assertions as fa
    line = fa.make_bucket_line("foo")
    assert fa.dryrun_prefix(line) == b"(dryrun) make_bucket: foo\n"


def test_format_assertions_stdout_equals_passes():
    from helpers import format_assertions as fa
    fa.assert_stdout_equals(b"hello\n", b"hello\n")


def test_format_assertions_stdout_equals_fails():
    from helpers import format_assertions as fa
    with pytest.raises(AssertionError):
        fa.assert_stdout_equals(b"hello\n", b"world\n")


def test_isomorphic_bucket_stable_within_instance():
    from helpers.isomorphic import IsomorphicTransform
    iso = IsomorphicTransform(seed="test1")
    a = iso.bucket("logical")
    b = iso.bucket("logical")
    assert a == b


def test_isomorphic_bucket_different_seed_different_value():
    from helpers.isomorphic import IsomorphicTransform
    iso1 = IsomorphicTransform(seed="seed-a")
    iso2 = IsomorphicTransform(seed="seed-b")
    assert iso1.bucket("logical") != iso2.bucket("logical")


def test_isomorphic_bucket_dns_compliant():
    from helpers.isomorphic import IsomorphicTransform
    import re
    iso = IsomorphicTransform(seed="dns-test")
    name = iso.bucket("UPPER Case_Name!@#")
    assert re.match(r"^[a-z0-9][a-z0-9\-]+[a-z0-9]$", name), \
        f"bucket name {name!r} is not DNS-compliant"


def test_isomorphic_key_includes_logical():
    from helpers.isomorphic import IsomorphicTransform
    iso = IsomorphicTransform(seed="k-test")
    k = iso.key("my-logical-key")
    assert "my-logical-key" in k


def test_isomorphic_respects_trial_namespace(monkeypatch):
    """Same seed across DIFFERENT trial namespaces must yield DIFFERENT bucket names."""
    from helpers.isomorphic import IsomorphicTransform

    monkeypatch.setenv("RL_TRIAL_NAMESPACE", "trial-A")
    iso_a = IsomorphicTransform(seed="shared-test-name")
    bucket_a = iso_a.bucket("logical")

    monkeypatch.setenv("RL_TRIAL_NAMESPACE", "trial-B")
    iso_b = IsomorphicTransform(seed="shared-test-name")
    bucket_b = iso_b.bucket("logical")

    assert bucket_a != bucket_b, (
        f"Iso transform must vary by trial namespace; got same bucket {bucket_a!r} "
        f"across trials. This would defeat the anti-memorization defense."
    )


def test_isomorphic_stable_within_same_trial(monkeypatch):
    """Same seed and same trial namespace must yield SAME bucket name (reproducibility)."""
    from helpers.isomorphic import IsomorphicTransform

    monkeypatch.setenv("RL_TRIAL_NAMESPACE", "trial-X")
    a = IsomorphicTransform(seed="reproducible").bucket("logical")
    b = IsomorphicTransform(seed="reproducible").bucket("logical")
    assert a == b


def test_pbt_filter_test_imports_cleanly():
    """Verifies tier3 PBT test file imports without syntax/hypothesis-decorator errors."""
    import importlib.util
    import pathlib
    pbt_path = pathlib.Path(__file__).parent.parent / "tier3" / "tests" / "eval" / "test_filters_eval.py"
    spec = importlib.util.spec_from_file_location("test_filters_eval", pbt_path)
    mod = importlib.util.module_from_spec(spec)
    assert mod is not None


def test_reward_compute_no_hack_basic():
    from tempfile import NamedTemporaryFile
    import json
    import subprocess

    pytest_report = {
        "summary": {"total": 2, "passed": 2, "failed": 0},
        "tests": [
            {"nodeid": "train/test_mb.py::test_a", "outcome": "passed"},
            {"nodeid": "eval/test_mb.py::test_b", "outcome": "passed"},
        ],
    }
    with NamedTemporaryFile("w", suffix=".json", delete=False) as f_in:
        json.dump(pytest_report, f_in)
        f_in_path = f_in.name
    with NamedTemporaryFile(suffix=".json", delete=False) as f_out:
        f_out_path = f_out.name

    repo = os.path.join(os.path.dirname(__file__), "..")
    r = subprocess.run(
        [sys.executable, os.path.join(repo, "shared/reward_compute.py"),
         "--report", f_in_path,
         "--out", f_out_path,
         "--smoke-ok", "1",
         "--aws-cli-hack", "0"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.load(open(f_out_path))
    assert data["reward"] == 1.0
    assert data["train_reward"] == 1.0
    assert data["eval_reward"] == 1.0
    assert data["aws_cli_hack_detected"] == 0.0


def test_reward_compute_hack_zeroes_reward():
    from tempfile import NamedTemporaryFile
    import json
    import subprocess

    pytest_report = {
        "summary": {"total": 1, "passed": 1},
        "tests": [
            {"nodeid": "train/test_x.py::test_y", "outcome": "passed"},
        ],
    }
    with NamedTemporaryFile("w", suffix=".json", delete=False) as f_in:
        json.dump(pytest_report, f_in)
        f_in_path = f_in.name
    with NamedTemporaryFile(suffix=".json", delete=False) as f_out:
        f_out_path = f_out.name

    repo = os.path.join(os.path.dirname(__file__), "..")
    r = subprocess.run(
        [sys.executable, os.path.join(repo, "shared/reward_compute.py"),
         "--report", f_in_path, "--out", f_out_path,
         "--smoke-ok", "1", "--aws-cli-hack", "1"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.load(open(f_out_path))
    assert data["reward"] == 0.0
    assert data["train_reward"] == 0.0
    assert data["aws_cli_hack_detected"] == 1.0


def test_reward_compute_train_only_in_primary():
    from tempfile import NamedTemporaryFile
    import json
    import subprocess

    pytest_report = {
        "summary": {"total": 4, "passed": 2},
        "tests": [
            {"nodeid": "train/t1.py::a", "outcome": "passed"},
            {"nodeid": "train/t1.py::b", "outcome": "failed"},
            {"nodeid": "eval/e1.py::a", "outcome": "passed"},
            {"nodeid": "eval/e1.py::b", "outcome": "passed"},
        ],
    }
    with NamedTemporaryFile("w", suffix=".json", delete=False) as f_in:
        json.dump(pytest_report, f_in)
        f_in_path = f_in.name
    with NamedTemporaryFile(suffix=".json", delete=False) as f_out:
        f_out_path = f_out.name

    repo = os.path.join(os.path.dirname(__file__), "..")
    subprocess.run(
        [sys.executable, os.path.join(repo, "shared/reward_compute.py"),
         "--report", f_in_path, "--out", f_out_path,
         "--smoke-ok", "1", "--aws-cli-hack", "0"],
        check=True, capture_output=True,
    )
    data = json.load(open(f_out_path))
    assert data["train_reward"] == 0.5
    assert data["eval_reward"] == 1.0
    assert data["reward"] == data["train_reward"]


def test_state_diff_equal_states():
    from helpers.state_diff import S3State, states_equal
    s1 = S3State(buckets={"a"}, objects={("a", "k"): b"v"})
    s2 = S3State(buckets={"a"}, objects={("a", "k"): b"v"})
    assert states_equal(s1, s2)


def test_state_diff_detects_missing():
    from helpers.state_diff import S3State, diff
    expected = S3State(buckets={"a", "b"}, objects={})
    actual = S3State(buckets={"a"}, objects={})
    d = diff(expected, actual)
    assert "b" in d["missing_buckets"]
    assert not d["extra_buckets"]


def test_state_diff_detects_wrong_content():
    from helpers.state_diff import S3State, diff
    expected = S3State(buckets={"a"}, objects={("a", "k"): b"v1"})
    actual = S3State(buckets={"a"}, objects={("a", "k"): b"v2"})
    d = diff(expected, actual)
    assert "a/k" in d["wrong_content"]
