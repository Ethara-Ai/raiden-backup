#!/usr/bin/env bash
# Quick moto reachability check. Used by Harbor's environment.healthcheck.
# Exits 0 if moto is up, non-zero otherwise.

curl -fsS http://127.0.0.1:5000/moto-api/ >/dev/null 2>&1
