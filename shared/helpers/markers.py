"""pytest plugin: auto-classifies tests into 'format' / 'state' categories.

Loaded by each tier's conftest.py via `pytest_plugins = ["helpers.markers"]`.
Markers land in each test's `keywords` field of pytest-json-report output, and
reward_compute.py reads them to populate format_reward / state_reward subscores.

Eliminates the brittle nodeid-substring matching previously used (Oracle B5.3 —
tests like test_ls_objects_show_basename were uncategorized despite asserting
on stdout). The fallback substring matching in reward_compute.py is retained
for defense-in-depth.
"""
from __future__ import annotations

import inspect

import pytest

_FORMAT_HINTS = (
    ".stdout",
    ".stderr",
    "fa.upload_line",
    "fa.download_line",
    "fa.delete_line",
    "fa.copy_line",
    "fa.move_line",
    "fa.make_bucket_line",
    "fa.remove_bucket_line",
    "fa.dryrun_prefix",
    "(dryrun)",
    "Total Objects:",
    "Total Size:",
    "PRE ",
    "human_readable",
    "format_size",
)

_STATE_HINTS = (
    "s3.head_object",
    "s3.head_bucket",
    "s3.list_buckets",
    "s3.list_objects_v2",
    "s3.get_object",
    "s3.put_object",
    "s3.delete_object",
    "s3.delete_objects",
    "s3.copy_object",
    "s3.create_bucket",
    "s3.delete_bucket",
    "moto_state.bucket_exists",
    "moto_state.object_exists",
    "moto_state.list_objects",
    "moto_state.get_object_bytes",
    "moto_state.bucket_object_count",
    "state_diff.",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "format: test asserts on stdout/stderr byte content",
    )
    config.addinivalue_line(
        "markers",
        "state: test asserts on moto state via boto3",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    for item in items:
        func = getattr(item, "function", None)
        if func is None:
            continue
        try:
            src = inspect.getsource(func)
        except (OSError, TypeError):
            continue

        if any(h in src for h in _FORMAT_HINTS):
            item.add_marker(pytest.mark.format)
        if any(h in src for h in _STATE_HINTS):
            item.add_marker(pytest.mark.state)
