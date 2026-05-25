import argparse
import pathlib
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jobs_dir")
    args = p.parse_args()

    root = pathlib.Path(args.jobs_dir)
    results = sorted(root.rglob("result.json"))
    if not results:
        print(f"No result.json found under {root}", file=sys.stderr)
        return 1
    print(results[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
