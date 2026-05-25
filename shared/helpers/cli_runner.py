"""Subprocess wrapper for /app/awscli.

Black-box invocation: never imports the agent's code. Captures stdout/stderr
as bytes so tests can do byte-exact comparisons.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CLIResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def run_cli(
    *args,
    cwd: Path,
    input_bytes=None,
    timeout: float = 60.0,
    extra_env=None,
) -> CLIResult:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["/app/awscli", *args],
        input=input_bytes,
        env=env,
        capture_output=True,
        timeout=timeout,
        cwd=str(cwd),
    )
    return CLIResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
