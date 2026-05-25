#!/usr/bin/env bash
set -euo pipefail

if ! pgrep -f "moto_server" >/dev/null 2>&1; then
    nohup moto_server -H 127.0.0.1 -p 5000 \
        >/var/log/moto.log 2>&1 &
fi

if ! pgrep -f "mitmdump" >/dev/null 2>&1; then
    nohup mitmdump \
        --listen-host 127.0.0.1 \
        --listen-port 8080 \
        --set confdir=/opt/mitmproxy-ca \
        --set block_global=false \
        --set keep_host_header=false \
        --set ssl_insecure=true \
        -s /opt/s3rl-verifier/mitm_addon.py \
        --quiet \
        >/var/log/mitmdump.log 2>&1 &
fi

exec "$@"
