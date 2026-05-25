"""State-equivalence helpers.

Computes diffs between expected and actual S3 state. Used by tests to assert
that the agent's CLI produced the right SIDE EFFECT (not just the right stdout).
"""
from dataclasses import dataclass, field
from . import moto_state


@dataclass
class S3State:
    buckets: set[str] = field(default_factory=set)
    objects: dict[tuple[str, str], bytes] = field(default_factory=dict)


def snapshot(s3) -> S3State:
    """Capture the current moto state as a comparable object."""
    state = S3State()
    for b in s3.list_buckets().get("Buckets", []):
        state.buckets.add(b["Name"])
        for key in moto_state.list_keys(s3, b["Name"]):
            state.objects[(b["Name"], key)] = moto_state.object_body(s3, b["Name"], key)
    return state


def diff(expected: S3State, actual: S3State) -> dict:
    """Return a dict describing how `actual` differs from `expected`."""
    return {
        "missing_buckets": sorted(expected.buckets - actual.buckets),
        "extra_buckets": sorted(actual.buckets - expected.buckets),
        "missing_objects": sorted([f"{b}/{k}" for (b, k) in expected.objects.keys() - actual.objects.keys()]),
        "extra_objects": sorted([f"{b}/{k}" for (b, k) in actual.objects.keys() - expected.objects.keys()]),
        "wrong_content": sorted([
            f"{b}/{k}"
            for (b, k) in (expected.objects.keys() & actual.objects.keys())
            if expected.objects[(b, k)] != actual.objects[(b, k)]
        ]),
    }


def states_equal(expected: S3State, actual: S3State) -> bool:
    d = diff(expected, actual)
    return all(not v for v in d.values())
