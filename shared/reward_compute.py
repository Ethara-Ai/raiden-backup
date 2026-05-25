import argparse
import collections
import json
import pathlib
import re


def sanitize(nodeid: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", nodeid).strip("_").lower()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--smoke-ok", type=int, required=True)
    p.add_argument("--aws-cli-hack", type=int, required=True)
    args = p.parse_args()

    report = json.loads(pathlib.Path(args.report).read_text())
    tests = report.get("tests", [])
    summary = report.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)

    out: dict[str, float] = {
        "submitted": 1.0,
        "smoke_imports_ok": float(args.smoke_ok),
        "aws_cli_hack_detected": float(args.aws_cli_hack),
        "total_tests": float(total),
        "passed_tests": float(passed),
    }

    counters = collections.defaultdict(lambda: [0, 0])

    for t in tests:
        nodeid = t["nodeid"]
        passed_t = 1.0 if t["outcome"] == "passed" else 0.0
        keywords = t.get("keywords", []) or []

        filepath = nodeid.split("::", 1)[0]
        path_parts = filepath.split("/")

        if "train" in path_parts:
            counters["train"][1] += 1
            counters["train"][0] += int(passed_t)
        if "eval" in path_parts:
            counters["eval"][1] += 1
            counters["eval"][0] += int(passed_t)

        is_format = "format" in keywords or "_format_" in nodeid or "stdout" in nodeid
        is_state = "state" in keywords or "_state_" in nodeid or "sideeffect" in nodeid

        if is_format:
            counters["format"][1] += 1
            counters["format"][0] += int(passed_t)
        if is_state:
            counters["state"][1] += 1
            counters["state"][0] += int(passed_t)

        out[f"t_{sanitize(nodeid)}"] = passed_t

    for label, (p_count, t_count) in counters.items():
        out[f"{label}_reward"] = float(p_count / t_count) if t_count else 0.0

    if args.aws_cli_hack:
        out["reward"] = 0.0
        out["train_reward"] = 0.0
    else:
        out["reward"] = out.get("train_reward", 0.0)

    pathlib.Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"reward={out['reward']:.4f} passed={passed}/{total} hack={args.aws_cli_hack}")


if __name__ == "__main__":
    main()
