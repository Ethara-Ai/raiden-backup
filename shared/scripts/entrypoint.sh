#!/usr/bin/env bash
# Container entrypoint: starts moto in background, then execs CMD.
# Idempotent — safe to call from inside test.sh or by Harbor.

set -euo pipefail

# Start moto in background if not already running.
if ! pgrep -f "moto_server" >/dev/null 2>&1; then
    nohup moto_server -H 127.0.0.1 -p 5000 \
        >/var/log/moto.log 2>&1 &
fi

# Hand off to the original CMD (bash by default, pytest at verifier time, etc).
exec "$@"
