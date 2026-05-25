import argparse
import json
import pathlib
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", help="Path to result.json (or read from stdin)")
    p.add_argument("--min", type=float, default=None)
    p.add_argument("--max", type=float, default=None)
    p.add_argument("--metric", default="reward")
    args = p.parse_args()

    if args.path:
        text = pathlib.Path(args.path).read_text()
    else:
        text = sys.stdin.read().strip()
        if text and not text.startswith("{"):
            text = pathlib.Path(text).read_text()

    data = json.loads(text)
    rewards = data.get("rewards") or data
    val = rewards.get(args.metric)
    if val is None:
        print(f"FAIL: metric '{args.metric}' not in {sorted(rewards)}", file=sys.stderr)
        return 1

    val = float(val)
    if args.min is not None and val < args.min:
        print(f"FAIL: {args.metric}={val:.4f} < min={args.min}", file=sys.stderr)
        return 1
    if args.max is not None and val > args.max:
        print(f"FAIL: {args.metric}={val:.4f} > max={args.max}", file=sys.stderr)
        return 1

    print(f"OK: {args.metric}={val:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
