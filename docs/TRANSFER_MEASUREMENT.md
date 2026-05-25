# Transfer Measurement Plan

The lab's measurement protocol for evaluating whether RL training on
this env actually improves the underlying model.

## The claim under test

"Training on `aws-cli-s3-tier1/2/3` improves model performance on
downstream code-gen benchmarks, not just on `aws-cli-s3` itself."

Without this measurement, "we improved pass@1 on our env" is benchmark
theatre — the model may have just memorized the specific tests it was
trained against.

## Measurement design

### Baseline checkpoint
Pick one frontier checkpoint and **lock the version hash**. Suggested
choices (any one is fine):
- Claude Opus 4.6 / 4.7
- Llama 3.1 70B Instruct
- Qwen 2.5 Coder 32B

### Pre-training scores

Run the baseline model on **four** external benchmarks. No fine-tuning yet.

| Benchmark | Subset | Metric | Why |
|---|---|---|---|
| SWE-bench Lite | All 300 instances | pass@1 | Code generation in real repos |
| HumanEval | All 164 problems | pass@1 | Classical code gen |
| MBPP | 500 problems | pass@1 | Smaller-scale code gen |
| Terminal-Bench 2.0 | 30 representative tasks | success rate | Closest in-distribution to our env |

For each, run **n=3 seeds** and report mean ± SEM.

### RL training phase

Train the baseline model on `aws-cli-s3` envs in curriculum order:
1. Tier 1 to convergence (mean reward plateaus).
2. Tier 2 to convergence.
3. Tier 3 to convergence.

Use the partner-recommended hyperparameters or the lab's standard RL
recipe (GRPO, PPO, etc).

### Post-training scores

Run the **same four benchmarks** with the **same n=3 seeds**.

### Acceptance criteria

- **Primary**: at least **2 of 4** benchmarks show a positive, statistically
  significant delta (p < 0.05, paired t-test across seeds).
- **Secondary**: no benchmark shows a negative significant delta beyond
  -2 percentage points (regression guard).

If acceptance fails: the env is a benchmark artifact, not a training
asset. Lab uses this as a signal for env design quality.

## Pre-registration

Before any RL training run on this env, the lab files a pre-registration
document with:

- Baseline checkpoint hash and provider.
- Eval benchmark versions and configurations.
- Training hyperparameters (algorithm, batch size, learning rate, n epochs).
- Expected delta direction per benchmark.
- Stop conditions (max steps, divergence thresholds).
- Sample size justification.

Modeled on AI eval pre-registration practices (Apollo Research, METR).

## What the partner is and is NOT responsible for

**Partner's scope**:
- Deliver an env where the measurement is well-defined.
- Demonstrate that oracle/null/frontier calibration gates pass.
- Document the env contract such that the lab can plug it in.

**NOT partner's scope**:
- Actually running the transfer measurement (lab's training compute).
- Designing the lab's RL algorithm.
- Tuning the lab's training pipeline.

## Cost (lab side)

Rough estimate for the transfer measurement:

| Item | Estimate |
|---|---|
| Pre-training scores (baseline × 4 benchmarks × n=3) | $200-800 |
| RL training (10K rollouts/epoch × 3 epochs × ~$1-3/rollout) | $30K-90K |
| Post-training scores | $200-800 |
| **Total** | **~$30K-90K per measurement** |

Lower if smaller-model rollouts (Haiku, 7B distilled) are used during
training.

## Reporting

The lab publishes:
- Delta table (4 benchmarks × pre/post means + p-values).
- Curve plots of in-distribution reward over training steps.
- A 1-page summary: did training on this env make the model better?

If yes, the env earns its slot in the lab's portfolio. If no, it goes
in the discard pile regardless of how well it scored on its own metrics.

## Cross-env transfer (Phase 2+)

Once the lab has 2+ envs from this partner (e.g., S3 + DynamoDB),
the next measurement asks: does training on S3 transfer to DynamoDB
(or vice versa)?

Acceptance: post-S3-training on DynamoDB shows positive delta vs
baseline-on-DynamoDB. This separates "narrow CLI memorization" from
"generalizable agentic coding skill."

This is the long-term test that justifies the harness investment.
