# Scaling: From One Env to Ten

How to extend this pattern to additional AWS services / CLI tools.

## Honest harness-reuse numbers

| Component | Reusable for next AWS service |
|---|---|
| `shared/Dockerfile` (swap deps) | 70% |
| `shared/scripts/entrypoint.sh`, `moto-startup-check.sh` | 100% |
| `shared/test_base.sh` | 95% |
| `shared/reward_compute.py` | 100% |
| `shared/helpers/cli_runner.py` | 100% |
| `shared/helpers/moto_state.py` | 60% (S3 client → service-specific client) |
| `shared/helpers/state_diff.py` | 30% (S3 state shape ≠ DynamoDB shape) |
| `shared/helpers/format_assertions.py` | **5%** (every service has unique stdout templates) |
| `shared/helpers/isomorphic.py` | 100% |
| `shared/helpers/generators.py` | 50% (some patterns reusable, most service-specific) |
| `agents/null_agent/agent.py` | 100% |
| `ci/*.{py,sh,yml}` | 90% |
| `tools/build_shared_image.sh` | 100% |
| Per-tier `task.toml` | 90% (swap name + timeouts) |
| Per-tier `solve.sh` | 90% |
| Per-tier `instruction.md` | **0%** (bespoke per service) |
| Per-tier test files | **0%** (bespoke per command) |

**Weighted by LOC: ~30% reuse.** Each new service is 5-7 weeks of focused
work, NOT 1 week.

## Phased roadmap

| Phase | Scope | Duration |
|---|---|---|
| 1 (this pilot) | aws-cli-s3 tier 1 + 2 + 3 (mb/rb/cp/ls/mv/rm) | 6 weeks |
| 1b | + `sync` as Tier 4 | 2 weeks |
| 2 | aws-cli-dynamodb (3 tiers) | 5-7 weeks |
| 3a | aws-cli-sqs (3 tiers) | 5-7 weeks |
| 3b | aws-cli-sns (3 tiers) | 5-7 weeks |
| 4 | aws-cli-iam (3 tiers, broader surface) | 6-8 weeks |
| 5 | aws-cli-lambda (limited moto coverage; may need LocalStack) | 8-10 weeks |
| 6 | aws-cli-ec2 (large surface) | 10-12 weeks |

**No "1 week per service" claims.** Each environment is real work.

## Behavior-spec extraction process

The bottleneck for new services is NOT the harness — it's encoding the
service's actual CLI behavior in spec + tests. The process:

1. Clone `aws/aws-cli` source.
2. Identify the customization module: `awscli/customizations/<service>/`.
3. Grep `subcommands.py` for output format strings — these are the byte-exact
   templates that go into `helpers/format_assertions.py`.
4. Read `results.py` for transfer-type definitions.
5. Document every flag, every error code, every edge case in
   `instruction.md` (~600-800 lines per tier).
6. Write tests against the documented behaviors, with state-side assertions
   via boto3 / moto.
7. Calibrate with oracle + null + frontier (~$300-900 per tier).

Total: 3-5 person-days BEFORE any test is written.

## Tinker integration notes

The Tinker recipe (`tinker-cookbook/recipes/harbor_rl/`) expects:
- `environment/Dockerfile` (single Dockerfile, no docker-compose) ✓
- `tests/test.sh` (single entry) ✓
- `instruction.md` (plain markdown) ✓
- `task.toml` consumed as a dict, NOT validated by Harbor's Pydantic model

**Critical caveat**: Tinker uses its OWN `ModalSandbox` wrapper, bypassing
Harbor's runner. This means `task.toml`'s `allow_internet`, `cpus`,
`memory_mb` etc. may NOT be enforced when running under Tinker — the
Dockerfile alone controls runtime constraints. Bake all sandboxing into
the Dockerfile, not into Harbor-level fields.

The first-party `harbor.rl` API (with `RLEnvironment`, `BashTool`) is on
the unmerged PR #1291 / `feature/harbor-rl-4d0` branch as of v0.8.0. Do
not depend on it; use Tinker's existing wrapper or wait for v0.9.

## Async-readiness guarantee

This codebase is structured to support downstream async RL training (AReaL,
SkyRL, veRL, OpenRLHF) without re-architecting. The key properties:

1. **Idempotent moto reset**: `/moto-api/reset` is safe at any point. The
   autouse `reset_moto` fixture ensures cross-test isolation.
2. **Per-trial namespacing**: `RL_TRIAL_NAMESPACE` env var randomizes
   bucket prefixes. Concurrent trials cannot collide.
3. **Pure reward computation**: `reward_compute.py` has no global state.
   Same `(report, smoke, hack)` inputs always produce the same reward.
4. **Per-test reward vector**: enables veRL's `filter_groups` and DAPO's
   group-filter (drop all-pass / all-fail groups) without re-instrumentation.

Documented as the "async portability guarantee" of this env.

## Reward shaping for downstream RL algorithms

The `reward.json` exposes multiple keys. Algorithms that use them:

| Algorithm | Reads | Why |
|---|---|---|
| PPO / GRPO (DeepSeek-R1 style) | `reward` | Single scalar; group-relative advantage |
| Process RM training | `t_<nodeid>` vector | Per-test labels |
| DAPO dynamic filtering | per-group reward distribution | Drop saturated groups |
| Curriculum trainer | `train_reward` + tier | Move to harder tier when ready |
| Eval monitor | `eval_reward` | Track generalization, never in gradient |

The lab can choose its own weighting; v3 sets `reward = train_reward` as
the safe default.
