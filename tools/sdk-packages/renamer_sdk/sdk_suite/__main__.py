"""Command-line entry point for the ReNamer development SDK suite."""

from __future__ import annotations

from renamer_sdk.sdk_suite import run_policy_b_suite


def main() -> int:
    results = run_policy_b_suite()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}")
        for message in result.messages:
            print(f"  - {message}")

    failed = sum(not result.passed for result in results)
    print(f"Policy B scenarios: {len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
