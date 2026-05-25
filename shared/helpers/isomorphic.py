"""Isomorphic perturbation for eval tests.

Maps logical test identifiers (bucket, key) to runtime-randomized concrete
values. The same logical test runs against different concrete inputs each
invocation — defeats template memorization.
"""
from __future__ import annotations

import hashlib
import os
import random


class IsomorphicTransform:
    def __init__(self, seed):
        trial_ns = os.environ.get("RL_TRIAL_NAMESPACE", "default-trial")
        if isinstance(seed, str):
            full = f"{trial_ns}::{seed}"
            seed_int = int(hashlib.sha256(full.encode()).hexdigest()[:8], 16)
        else:
            full = f"{trial_ns}::{seed}"
            seed_int = int(hashlib.sha256(full.encode()).hexdigest()[:8], 16)
        self.rng = random.Random(seed_int)
        self.bucket_map = {}
        self.key_map = {}

    def bucket(self, logical: str) -> str:
        if logical not in self.bucket_map:
            suffix = self.rng.randbytes(4).hex()
            # Ensure DNS-compliant: lowercase, no leading digit/hyphen.
            safe_logical = "".join(c if c.isalnum() else "-" for c in logical.lower())[:20]
            self.bucket_map[logical] = f"iso-{suffix}-{safe_logical}".rstrip("-")
        return self.bucket_map[logical]

    def key(self, logical: str) -> str:
        if logical not in self.key_map:
            prefix = self.rng.randbytes(3).hex()
            self.key_map[logical] = f"{prefix}/{logical}"
        return self.key_map[logical]
