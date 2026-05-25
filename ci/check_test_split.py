import pathlib
import sys


def check_tier(tier_dir: pathlib.Path) -> list[str]:
    errors = []
    train = tier_dir / "tests" / "train"
    eval_ = tier_dir / "tests" / "eval"

    if not train.is_dir():
        errors.append(f"{tier_dir.name}: missing tests/train/")
    if not eval_.is_dir():
        errors.append(f"{tier_dir.name}: missing tests/eval/")

    train_tests = list(train.glob("test_*.py")) if train.is_dir() else []
    eval_tests = list(eval_.glob("test_*.py")) if eval_.is_dir() else []

    if not train_tests:
        errors.append(f"{tier_dir.name}: no train tests")
    if not eval_tests:
        errors.append(f"{tier_dir.name}: no eval tests")

    return errors


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parent.parent
    all_errors = []
    for tier in ("tier1", "tier2", "tier3"):
        all_errors.extend(check_tier(repo / tier))

    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("OK: all tiers have train/ and eval/ test dirs populated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
