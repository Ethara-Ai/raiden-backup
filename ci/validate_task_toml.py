import argparse
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.stderr.write("install tomli (Python <3.11) or use Python >=3.11\n")
        sys.exit(2)

REQUIRED_TOP = ["schema_version", "task", "agent", "verifier", "environment"]
REQUIRED_TASK = ["name", "description", "authors"]
ORG_NAME_RE = r"^[a-z0-9][a-z0-9\-]{0,38}/[a-z0-9][a-z0-9\-]{0,62}$"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path")
    args = p.parse_args()

    with open(args.path, "rb") as f:
        data = tomllib.load(f)

    errors = []

    for k in REQUIRED_TOP:
        if k not in data:
            errors.append(f"missing top-level [{k}]")

    if "task" in data:
        for k in REQUIRED_TASK:
            if k not in data["task"]:
                errors.append(f"missing [task].{k}")
        import re
        name = data["task"].get("name", "")
        if not re.match(ORG_NAME_RE, name):
            errors.append(f"[task].name '{name}' does not match org/name pattern")

    if "agent" in data and "timeout_sec" not in data["agent"]:
        errors.append("missing [agent].timeout_sec")

    if "verifier" in data and "timeout_sec" not in data["verifier"]:
        errors.append("missing [verifier].timeout_sec")

    if "environment" in data:
        env = data["environment"]
        for k in ("memory_mb", "storage_mb", "cpus"):
            if k in env and not isinstance(env[k], int):
                errors.append(f"[environment].{k} must be int, got {type(env[k]).__name__}")
        if "allow_internet" in env and not isinstance(env["allow_internet"], bool):
            errors.append("[environment].allow_internet must be bool")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"OK: {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
