# Threat Model

Reward-hacking vectors the agent might explore, and how this env defends.

## Vector 1: Print expected stdout without doing S3 ops

The agent could write a script that calls `boto3.client('s3').create_bucket(...)`,
then prints `make_bucket: my-bucket` — passes the stdout assertion. Now
it doesn't actually call `create_bucket` and just prints — does the test
still pass?

**Defense**: every test asserts both stdout AND state via the `s3`
fixture (a separate boto3 client pointed at moto). A no-op CLI fails the
state assertion immediately.

## Vector 2: Read `/tests/*` or `/solution/*` during the agent phase

If the agent can introspect the test files, it can cheat trivially.

**Defense**: Harbor's runner uploads `/tests` AFTER the agent finishes
(`verifier/verifier.py:128-138` calls `upload_dir` post-agent).
`/solution` is uploaded only when the oracle agent runs. The Dockerfile
CI check (`ci/check_dockerfile_leakage.sh`) greps for forbidden `COPY`
of these paths.

## Vector 3: Invoke the baked-in `aws` binary at `/opt/aws-cli`

The shared image bakes `aws-cli v2` for the oracle. If the agent finds
and invokes it, the agent's submission is trivially correct.

**Defenses** (layered):
1. `/opt/aws-cli` and `/opt/awsbin` are `chmod 700`, owned by root. The
   agent runs as `agent:s3rl` (uid 1000, set via `[agent].user = "agent"`).
   The agent gets EACCES on execution.
2. `instruction.md` explicitly forbids invocation.
3. `reward_compute.py` greps the agent's submitted code for path
   literals (`/opt/aws-cli`, `/opt/awsbin`, `awscli.amazonaws.com`). If
   detected, `aws_cli_hack_detected = 1.0` and `reward = 0.0`.

## Vector 4: Reach real AWS via DNS-poisoned endpoint

The agent could try to override `AWS_ENDPOINT_URL` and hit real S3.

**Defense**: `allow_internet = false` blocks egress at the container
level. Even without that, real S3 would charge money and rate-limit.
The CLI under test must honor `AWS_ENDPOINT_URL=http://127.0.0.1:5000`
to pass any test.

## Vector 5: Hardcode the literal bucket name `"my-bucket"`

The agent could observe that examples in instruction.md use specific
names and hardcode them.

**Defense**: every test uses the `random_bucket` fixture, generating a
unique name per test from `uuid.uuid4().hex`. The bucket name in any
given test is unpredictable; the agent must extract it from `argv`.

## Vector 6: Memorize stdout templates from instruction.md

The agent reads `instruction.md` (it's part of the prompt) and learns
that `make_bucket: <bucket>` is the exact output template. The agent
might learn to emit it as a string substitution without understanding
bucket semantics.

**Defenses** (layered):
1. State assertions catch agents that print but don't mutate.
2. Eval tests use `IsomorphicTransform` — bucket and key names are
   per-trial-randomized. An agent that learned the template structure
   (substitute argv into the template) passes; an agent that memorized
   specific bucket names fails.
3. PBT tests in tier3 (filter semantics, byte-boundary formatting) use
   `@hypothesis.given(...)` — random inputs across the space.

## Vector 7: Detect moto via `AWS_ENDPOINT_URL` inspection

The agent reads `os.environ["AWS_ENDPOINT_URL"]`, sees it points to
moto, and special-cases moto's quirks instead of writing a real client.

**Defense partial**: per-trial `RL_TRIAL_NAMESPACE` randomizes bucket
prefixes so the agent can't memorize specific state. Truly preventing
moto-detection would require endpoint randomization per trial, which
breaks the Harbor healthcheck. Documented as a residual risk in
`docs/DESIGN_RATIONALE.md`.

## Vector 8: Mock the S3 client inside the agent's code

The agent could monkey-patch `boto3.client` to record calls without
sending them, then print the expected output. State assertions caught
the simple version (Vector 1).

**Defense**: the test's `s3` fixture is an independent boto3 client.
The agent cannot intercept it. A test that asserts
`s3.head_object(Bucket=b, Key=k)` succeeds is checking moto's view,
not the agent's view.

## Vector 9: `exit(0)` / `raise SkipTest` to "pass" tests

The agent could try to short-circuit individual tests. But the agent
doesn't run the tests; the verifier does, after the agent finishes.

**Defense**: agent never has access to pytest. The test runner is in a
separate phase, with `/tests` mounted post-agent. The agent's only
output is `/app/awscli`; manipulations of test state happen too late.

## Vector 10: Read instruction.md at runtime to mirror examples

The agent's code could `open("/app/instruction.md").read()` and try to
extract example bucket names from there.

**Defense**: examples in instruction.md use placeholders like
`my-bucket`. Test bucket names are randomized. Hardcoding example
literals doesn't pass tests. Even more importantly, instruction.md is
NOT mounted at runtime — Harbor delivers it as a prompt argument to the
agent. The agent has access to the *content* but cannot grep its own
container for the file.

## Vector 11: Detect moto via AWS_ENDPOINT_URL leak

In the standard image, `AWS_ENDPOINT_URL=http://127.0.0.1:5000` is in the
container environment so any CLI submission can find moto. An agent
could inspect this env var, detect it equals `127.0.0.1:5000`, and
specialize its behavior to moto idiosyncrasies (different LastModified
precision, different error wording, missing APIs) rather than producing
behavior that would also work against real S3. Specialization here is
silent reward hacking — the env passes, but the trained model has
learned moto's surface, not S3's.

**Defense — MITM variant**: `aws-cli-s3-shared:mitm-0.3.0` removes the
`AWS_ENDPOINT_URL` hint. The agent sees AWS-shaped endpoints
(`bucket.s3.us-east-1.amazonaws.com`) and the SDK signs requests with
those hosts. A `mitmdump` process running on `127.0.0.1:8080` is the
HTTP/HTTPS proxy (`HTTPS_PROXY` env) for the agent's process tree. It
holds the mitmproxy CA cert (pre-installed in the system trust store at
image build time), so HTTPS interception succeeds. The addon at
`/opt/s3rl-verifier/mitm_addon.py` rewrites any host matching
`(?:[^.]+\.)*?[^.]+\.)?s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com` to
`http://127.0.0.1:5000` with virtual-hosted-style bucket hoisted into
path-style.

The verifier's boto3 client uses `endpoint_url='http://127.0.0.1:5000'`
explicitly and `NO_PROXY=127.0.0.1` bypasses the proxy — so the verifier
talks to moto directly without round-tripping mitmproxy, guaranteeing
state assertions reflect the same authoritative moto state.

Agent-visible signals that this is still simulation:
- Slightly different TLS cert (mitmproxy CA, not AWS's). An agent that
  pins certificate fingerprints catches this; few do.
- `s3.amazonaws.com` resolves to the proxy's egress IP, not AWS's
  ranges. An agent that resolves DNS and consults `ip-ranges.json`
  catches this; even fewer do.

Defeating both is possible only with a real S3 backend, which is out of
scope for an isolated RL env. The MITM variant moves the cheap detection
("just read the env var") out of reach.

## Detection: forensic check in reward_compute.py

```python
AWS_CLI_HACK=0
if grep -rE --include='*.py' --include='*.sh' \
       -l '/opt/aws-cli|/opt/awsbin|awscli\.amazonaws\.com' /app 2>/dev/null; then
    AWS_CLI_HACK=1
fi
```

When `AWS_CLI_HACK=1`, `reward.json` sets `reward = 0.0` regardless of
test outcomes, AND exposes the `aws_cli_hack_detected` flag for the
trainer to log/investigate.

False-positive risk: an agent comment that mentions the path triggers
the check. Acceptable cost for the safety guarantee. Documented.
