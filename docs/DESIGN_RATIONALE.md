# Design Rationale

Every nontrivial decision, the alternatives considered, and why this one won.

## 1. Curriculum: 3 tiers instead of 1 monolithic env

**Decision**: ship `tier1`, `tier2`, `tier3` as three separate Harbor tasks.

**Alternatives considered**:
- Monolithic 80-test env covering 6 commands.
- Curriculum field in `task.toml` consumed by the trainer.

**Why this won**: production RL code-gen training (DRIVE-RLVR, DeepSeek-R1
post-trainings, Qwen3-Coder) consistently uses two-stage curricula —
entropy-expansion then hard-focus. A monolithic env produces a single big
reward spike early in training (`0` from import errors, `0.05` from one
or two trivial passes) with no gradient toward the harder behaviors.
Splitting into nested-difficulty tasks gives the trainer 3 independent
reward distributions to learn from, and lets the lab order them as a
curriculum.

**Cost**: 3× the calibration trials, more files to author. Worth it.

## 2. Train/eval test split

**Decision**: each tier has `tests/train/` and `tests/eval/`. Only the
`train_reward` aggregate is fed back as the primary `reward`. The
`eval_reward` is computed and exposed in `reward.json` but never read by
the trainer.

**Alternatives considered**:
- Single test suite (textbook leakage).
- Separate eval task with held-out behaviors.

**Why this won**: eval tests exercise behaviors absent from train (e.g.
filter-exclude-then-include in train, the reversed order in eval; 1-byte
in train, the `2..1023 Bytes` PBT range in eval). This lets the lab
measure generalization without paying for a separate task. The reward
shape (continuous `passed/total`) is unaffected.

**Cost**: 25% more tests to author (but train+eval together exercise
behaviors more thoroughly than train alone).

## 3. Reward shape: continuous + per-test vector + format/state split

**Decision**: `reward.json` writes:
- `reward` = `train_reward` = `train_passed / train_total` (1-D primary).
- `eval_reward` (held-out; never read by trainer).
- `format_reward`, `state_reward` (categorized; downstream may weight).
- `t_<sanitized_nodeid>: 0|1` for every test (per-test vector).
- `smoke_imports_ok`, `aws_cli_hack_detected` (diagnostic flags).

**Alternatives considered**:
- Binary reward (1 if all pass, else 0).
- Reward = `passed/total` only, no other keys.
- Nested-object reward with `metrics: {...}` sub-dict.

**Why this won**: the **per-test vector** unlocks PRM / process-reward
training without a re-instrumentation pass. The categorized sub-rewards
(`format`, `state`) match the DeepSeek-R1 `R_acc + R_format` pattern that
the field has converged on. The flat schema matches Harbor's documented
`dict[str, float|int]` contract. Nested objects would be silently
dropped.

## 4. moto as embedded sidecar inside the agent container (not docker-compose)

**Decision**: a single Dockerfile per tier (all `FROM aws-cli-s3-shared`).
moto runs as a background process started by the entrypoint script;
Harbor's `[environment.healthcheck]` waits for it before unlocking the
agent phase.

**Alternatives considered**:
- `docker-compose.yaml` with separate `s3-mock` service.
- LocalStack instead of moto.
- Real AWS with sandbox account.

**Why this won**: Harbor's cloud sandbox providers (Modal, Daytona, E2B,
RunLoop, GKE) only accept a single Dockerfile — compose is local-only.
For an RL env that must scale to ≥100 concurrent rollouts on a training
cluster, compose was a structural blocker. moto's image footprint is
99MB vs LocalStack's 475MB; startup is ~1s vs ~3.3s. LocalStack also has
a commercial-use grey area on the free tier.

## 5. botocore + boto3 both available, real aws-cli baked in

**Decision**: the image installs `boto3`, `botocore`, and the real
`aws-cli` v2 (the last at a privileged path, owned by root, agent user
cannot read or execute it).

**Alternatives considered**:
- botocore-only (force the agent to write its own transfer manager).
- aws-cli installed but agent forbidden by instruction only.

**Why this won**: the v2-vs-v1 critique on plan v2 showed that the
"botocore-only adds difficulty" hypothesis is illusory — `put_object`
covers 90% of the use case in 5 lines. The real difficulty is byte-exact
CLI behavior, not API surface. Real aws-cli must be present so the
oracle agent has a working reference; we control access via Linux
permissions + agent-user separation + forensic detection in the
reward computer.

## 6. Oracle via single image + permission/user separation (no multi-stage build)

**Decision**: `[agent].user = "agent"` in task.toml. The agent process
runs as uid 1000 in group `s3rl`. The baked-in aws-cli is `chmod 700`,
owned by root, so the `agent` user gets EACCES if it tries to execute
it. The oracle's `solve.sh` runs as root by default, so it can `chmod`
the binaries before symlinking into `/app/awscli`.

**Alternatives considered**:
- Multi-stage Dockerfile with `--target=oracle` build target (Harbor
  doesn't support build targets — discovered during v2 critique).
- Use `[verifier.environment_mode] = "separate"` with a separate
  verifier image (overkill for our case; `separate` is for proprietary
  grading code, not for oracle/agent asymmetry).
- Pure convention (instruction.md forbids; nothing enforces).

**Why this won**: filesystem permissions + user separation is the
documented Harbor pattern for this kind of asymmetric capability.
Layered with the forensic check in `reward_compute.py` (grep submission
for path literals), it gives defense in depth.

## 7. Property-based testing in tier3, UUID randomization in tier1/tier2

**Decision**: tier3 eval tests use `@hypothesis.given(...)` decorators
for filter semantics and human-readable byte boundaries. Tier1/tier2
use `random_bucket` UUID fixtures instead.

**Alternatives considered**:
- PBT everywhere (over-engineered for tier1's simple mb/rb).
- No PBT at all (claimed but never delivered in plan v2).

**Why this won**: PBT pays off where the input space is large and the
implementation is most likely to be wrong in the tail (byte boundaries,
filter pattern matching). For mb/rb's small input space, UUID
randomization is sufficient defense against template memorization.

## 8. Isomorphic perturbation in eval only

**Decision**: `helpers/isomorphic.py` maps logical identifiers (bucket,
key) to per-trial-randomized concrete names. Used only in `tests/eval/`.

**Alternatives considered**:
- Apply isomorphic perturbation to train tests too.
- No perturbation; rely on UUID randomization.

**Why this won**: train tests need to be reproducible for the trainer
to extract a clean gradient. Eval tests use perturbation precisely to
detect when the model has memorized template strings vs learned
semantics. Two different purposes, two different patterns.

## 9. allow_internet = false (container-wide)

**Decision**: every tier sets `allow_internet = false` in `[environment]`.
All deps baked into the image at build time.

**Alternatives considered**:
- `allow_internet = true` (lets the agent install whatever).
- Phase-conditional internet (oracle gets it, agent doesn't) — not
  supported by Harbor; container-wide.

**Why this won**: prevents the obvious reward hack of `pip install
awscli && wrap`. Also forces the partner to bake everything reproducibly.

## 10. No-comments-default in test files

**Decision**: test files have minimal docstrings. Helpers have module-level
docstrings explaining their purpose; functions are not commented.

**Why**: the user's CLAUDE.md guidance is "default to writing no
comments. Only add one when the WHY is non-obvious." Test names are
descriptive enough. Module-level docstrings on helpers explain
non-obvious concepts (ground-truth client, anti-reward-hack).
