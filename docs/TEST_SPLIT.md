# Test Split: train vs eval

Each tier has `tests/train/` (reward signal for RL training) and
`tests/eval/` (held-out behaviors, never seen by the trainer's gradient).

## Tier 1 — mb, rb

### Train (12 tests across 2 files)

`test_mb.py`:
- `test_mb_stdout_state_happy_path` — basic create
- `test_mb_state_bucket_appears_in_list` — state-only verification
- `test_mb_state_idempotent_owned_fails` — duplicate in us-west-2
- `test_mb_stdout_no_extra_lines` — exactly 1 line of stdout
- `test_mb_invalid_uri_no_prefix` — validation
- `test_mb_state_us_east_1_no_location_constraint` — region handling

`test_rb.py`:
- `test_rb_stdout_state_removes_empty_bucket` — basic remove
- `test_rb_non_empty_without_force_fails` — error path
- `test_rb_state_with_force_deletes_all_then_bucket` — recursive delete
- `test_rb_stdout_force_emits_delete_lines` — emits delete lines
- `test_rb_invalid_uri_no_prefix` — validation
- `test_rb_with_key_in_uri_rejected` — URI validation

### Eval (4 tests across 2 files)

Held-out behaviors covered:
- `test_mb_isomorphic_stdout` — runtime-randomized bucket names (defeats
  hardcoded literals); train tests use UUID fixtures, eval uses the
  IsomorphicTransform.
- `test_mb_state_isomorphic_appears_in_list` — same with state check.
- `test_rb_isomorphic_force_deletes_many_objects` — 7 objects in
  isomorphic-renamed bucket; train tests use 2-3.
- `test_rb_state_isomorphic_remove_empty` — isomorphic empty-bucket case.

**Behaviors held out from train**: deep object counts (7+), isomorphic
identifier handling. An impl that hardcodes specific bucket names from
the worked examples in instruction.md fails on eval.

## Tier 2 — + cp single, ls, rm

### Train (28 tests across 6 files)

`test_mb.py` (5), `test_rb.py` (4), `test_cp_local_s3.py` (7),
`test_cp_s3_local.py` (4), `test_ls.py` (5), `test_rm.py` (3).

### Eval (10 tests across 4 files)

Held-out behaviors:

| Train covers | Eval covers (not in train) |
|---|---|
| Single upload | Isomorphic upload + roundtrip |
| Download known content | Download isomorphic-renamed key |
| ls with simple buckets | ls with isomorphic prefix patterns |
| ls --summarize with 2 objects | ls --summarize with 3 isomorphic objects |
| Missing prefix exit 1 | Missing isomorphic prefix |
| Single rm | Isomorphic rm |
| | Roundtrip: cp → cp back, byte-equal |

## Tier 3 — full curriculum (no sync)

### Train (50 tests across 9 files)

`test_mb_rb.py` (4), `test_cp_single.py` (7), `test_cp_recursive.py` (6),
`test_cp_s3_s3.py` (5), `test_mv.py` (7), `test_ls.py` (6),
`test_rm.py` (4), `test_filters.py` (5), `test_uri_parsing.py` (4) = 48.

### Eval (16 tests across 6 files)

Held-out behaviors:

| Train tests | Eval extends to |
|---|---|
| `--exclude '*' --include '*.txt'` | Reversed order: `--include '*.txt' --exclude '*'` (PBT-generated) |
| Single-source filter | `?` glob, `.gitignore`-style filter |
| `--human-readable` `1 Byte` singular, `1.0 KiB` boundary | PBT-generated `N Bytes` plural range (2..1023) |
| `--recursive` cp | Recursive roundtrip with deep dirs |
| mv s3→s3 | Isomorphic mv + recursive mv |
| ls non-recursive | Isomorphic ls + PRE/leaf mix |
| ls --summarize Total Objects=2,7 | Isomorphic with N=4 objects |
| URI a/b/c/d | Deep URI (a/b/c/d/e/f.txt) + trailing-slash basename preserve |
| mv self-move guard | Isomorphic self-move guard |

**Critical property held out**: filter-include-then-exclude (reversed
order from train). An impl that learned only one order of filter
processing fails eval.

## Why train/eval matters for RL

If train and eval share the same tests:
- Trainer optimizes the model to maximize `passed/total` on those tests.
- Reported pass@1 improves.
- But you can't tell if the model learned the actual S3 semantics or
  just memorized the test patterns.

By holding out behaviors entirely (not just instances), eval measures
generalization. A model with high `train_reward` and low `eval_reward`
has overfit. A model that gains on both is genuinely improving.

`reward.json` exposes both:
- `reward = train_reward` — primary gradient signal.
- `eval_reward` — diagnostic; never fed to gradient.
