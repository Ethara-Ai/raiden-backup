"""Structural compatibility smoke for Tinker's HarborTask dataclass.

Tinker's RL trainer wraps each Harbor task as:
    HarborTask(task_name: str, instruction: str, task_dir: str, config: Any)
    -- see tinker_cookbook/recipes/harbor_rl/harbor_env.py

This script confirms our tier directories can populate every field:
    task_name      <- [task].name in task.toml
    instruction    <- contents of instruction.md
    task_dir       <- absolute path to tier directory
    config         <- parsed task.toml (or harbor's TaskConfig if importable)

Runs without Tinker installed. If `tinker_cookbook` is on PYTHONPATH, the real
HarborTask dataclass is used; otherwise a local twin with identical fields.
"""
from __future__ import annotations

import dataclasses
import pathlib
import sys
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

try:
    from tinker_cookbook.recipes.harbor_rl.harbor_env import HarborTask  # noqa: F401
    USING_REAL_TINKER = True
except Exception:
    USING_REAL_TINKER = False

    @dataclasses.dataclass
    class HarborTask:
        task_name: str
        instruction: str
        task_dir: str
        config: Any


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TIERS = ["tier1", "tier2", "tier3"]


def load_task(tier: str) -> HarborTask:
    tier_dir = REPO_ROOT / tier
    toml_path = tier_dir / "task.toml"
    instr_path = tier_dir / "instruction.md"
    if not toml_path.exists():
        raise FileNotFoundError(toml_path)
    if not instr_path.exists():
        raise FileNotFoundError(instr_path)

    config = tomllib.loads(toml_path.read_text())
    task_section = config.get("task", {})
    task_name = task_section.get("name") or tier

    return HarborTask(
        task_name=task_name,
        instruction=instr_path.read_text(),
        task_dir=str(tier_dir),
        config=config,
    )


def main() -> int:
    print(f"Using {'REAL' if USING_REAL_TINKER else 'LOCAL-MOCK'} HarborTask")
    failures = []
    for tier in TIERS:
        try:
            task = load_task(tier)
        except Exception as e:
            print(f"FAIL  {tier}: {type(e).__name__}: {e}")
            failures.append(tier)
            continue

        if not task.task_name or "/" not in task.task_name:
            print(f"FAIL  {tier}: task_name '{task.task_name}' missing org/name format")
            failures.append(tier)
            continue
        if len(task.instruction) < 500:
            print(f"FAIL  {tier}: instruction.md too short ({len(task.instruction)} bytes)")
            failures.append(tier)
            continue
        if not pathlib.Path(task.task_dir).is_dir():
            print(f"FAIL  {tier}: task_dir '{task.task_dir}' is not a directory")
            failures.append(tier)
            continue
        if not isinstance(task.config, dict) or "task" not in task.config:
            print(f"FAIL  {tier}: config malformed (missing [task] section)")
            failures.append(tier)
            continue

        print(
            f"PASS  {tier:6}  name={task.task_name:40}  "
            f"instruction={len(task.instruction)}B  "
            f"toml-keys={len(task.config)}"
        )

    if failures:
        print(f"\nFAIL: {len(failures)}/{len(TIERS)} tiers incompatible with HarborTask",
              file=sys.stderr)
        return 1
    print(f"\nPASS: all {len(TIERS)} tiers structurally compatible with Tinker HarborTask")
    return 0


if __name__ == "__main__":
    sys.exit(main())
