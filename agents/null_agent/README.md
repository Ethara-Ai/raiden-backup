# Null Agent

Submits an empty `/app/awscli` (`#!/bin/sh\nexit 0`). Used to validate that tests
are discriminative — a null submission must score ≤ 0.05 on each tier.

If null agent scores higher, tests rely too much on stdout templating and not
enough on S3-side state verification. Fix the tests, not the threshold.

## Invocation

From the repo root:

```bash
harbor run -p tier1 \
    --agent-import-path agents.null_agent.agent:NullAgent \
    --env docker -o ./out/null-t1
```

The `--agent-import-path module:Class` form is Harbor's documented way to load a
custom subclass of `BaseAgent`. The `-a` flag accepts only `AgentName` enum values
(oracle, claude-code, etc.) and rejects file paths.
