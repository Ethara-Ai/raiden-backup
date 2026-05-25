#!/usr/bin/env python3
"""Project reward.json's per-test fields into a flat (test_id, score) table for
downstream process-RL / PRM training. Reads either a single reward.json or a
directory of them and emits ndjson / csv / tsv suitable for jq/awk pipelines.

Reward.json schema (Harbor contract):
    {
        "reward": 0.85,
        "submitted": 1.0,
        "train_reward": 0.85,
        "format_reward": 0.92,
        "state_reward": 0.78,
        ...
        "t_train_test_mb_py__test_mb_stdout_state_happy_path": 1.0,
        "t_eval_test_rb_eval_py__test_rb_isomorphic_force_deletes": 0.0,
        ...
    }

Per-test keys are prefixed `t_`. This script extracts them; the rest is dropped.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from collections.abc import Iterator


def iter_reward_files(path: pathlib.Path) -> Iterator[pathlib.Path]:
    if path.is_file():
        yield path
        return
    if path.is_dir():
        yield from sorted(path.rglob("reward.json"))


def project_test_vector(reward: dict) -> dict[str, float]:
    return {k[2:]: float(v) for k, v in reward.items() if k.startswith("t_")}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "input",
        type=pathlib.Path,
        help="Path to reward.json OR directory containing reward.json files",
    )
    p.add_argument(
        "--format",
        choices=["ndjson", "csv", "tsv"],
        default="ndjson",
        help="Output format (default: ndjson — one trial per line)",
    )
    p.add_argument(
        "--include-meta",
        action="store_true",
        help="Include reward/train_reward/eval_reward/etc. as top-level fields",
    )
    args = p.parse_args()

    rows: list[dict] = []
    for f in iter_reward_files(args.input):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"warning: skipping {f}: {e}", file=sys.stderr)
            continue

        row: dict = {"trial_id": str(f.parent)}
        if args.include_meta:
            for k in ("reward", "train_reward", "eval_reward", "format_reward",
                      "state_reward", "passed_tests", "total_tests"):
                if k in data:
                    row[k] = data[k]
        row["tests"] = project_test_vector(data)
        rows.append(row)

    if not rows:
        print("warning: no reward.json files found", file=sys.stderr)
        return 1

    if args.format == "ndjson":
        for row in rows:
            print(json.dumps(row, separators=(",", ":")))
    else:
        delim = "," if args.format == "csv" else "\t"
        all_tests = sorted({t for r in rows for t in r["tests"]})
        meta_keys = sorted(
            {k for r in rows for k in r if k not in ("trial_id", "tests")}
        )
        header = ["trial_id", *meta_keys, *all_tests]
        w = csv.writer(sys.stdout, delimiter=delim)
        w.writerow(header)
        for r in rows:
            row_out = [r["trial_id"]]
            row_out.extend(r.get(k, "") for k in meta_keys)
            row_out.extend(r["tests"].get(t, "") for t in all_tests)
            w.writerow(row_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
