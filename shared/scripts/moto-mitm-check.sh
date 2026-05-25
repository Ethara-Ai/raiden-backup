#!/usr/bin/env bash
set -e

curl -fsS http://127.0.0.1:5000/moto-api/ >/dev/null 2>&1
python3 -c "import socket; s=socket.socket(); s.settimeout(1.0); s.connect(('127.0.0.1', 8080)); s.close()" 2>/dev/null
