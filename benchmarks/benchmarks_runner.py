import argparse
import os
import subprocess
import sys
from datetime import datetime


def run_effectiveness_suite(strict: bool = False) -> int:
    """
    Run the Context Graph Effectiveness benchmark suite (pytest-based, no
    pytest-benchmark fixture).  Uses pytest directly — does NOT use
    --benchmark-only which would skip these tests entirely.

    Args:
        strict: If True, exit(1) on any threshold failure.

    Returns:
        pytest exit code (0 = all passed/skipped, non-zero = failures).
    """
    print("\n" + "=" * 60)
    print("  Context Graph Effectiveness Suite")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "pytest",
        "benchmarks/context_graph_effectiveness/",
        "-p", "no:typeguard",
        "-p", "no:langsmith",
        "-m", "not real_llm",       # skip real-LLM tests in normal CI
        "-v", "--tb=short",
        "--no-header",
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n[EFFECTIVENESS] One or more effectiveness tests FAILED.")
        if strict:
            sys.exit(result.returncode)
    else:
        print("\n[EFFECTIVENESS] All effectiveness tests PASSED.")
    return result.returncode


def run_benchmarks():
    """
    Master Runner for Semantica Benchmarks.
    """
    parser = argparse.ArgumentParser(description="Run Semantica Benchmarks")
    parser.add_argument(
        "--strict", action="store_true", help="Fail script if performance regresses"
    )
    parser.add_argument(
        "--effectiveness", action="store_true",
        help="Run the Context Graph Effectiveness suite (pytest-based metrics)"
    )
    args = parser.parse_args()

    # Run effectiveness suite first if requested
    if args.effectiveness:
        run_effectiveness_suite(strict=args.strict)

    print("Starting Semantica Benchmark Suite...")

    timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
    os.makedirs("benchmarks/results", exist_ok=True)

    current_json = f"benchmarks/results/run_{timestamp}.json"
    baseline_json = "benchmarks/results/baseline.json"

    # Run Benchmarks
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "benchmarks/",
        "-p",
        "no:typeguard",
        "-p",
        "no:langsmith",
        "--benchmark-only",
        f"--benchmark-json={current_json}",
        "--benchmark-columns=min,mean,stddev,ops",
        "--benchmark-sort=mean",
    ]

    print(f"Executing benchmarks... (saving to {current_json})")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Benchmarks failed to execute (runtime errors).")
        sys.exit(result.returncode)

    print("Benchmarks completed execution.")

    # Compare against Baseline
    if os.path.exists(baseline_json):
        print(f"Comparing against Baseline ({baseline_json})...")

        if os.path.exists("benchmarks/infrastructure/compare.py"):
            compare_cmd = [
                sys.executable,
                "benchmarks/infrastructure/compare.py",
                baseline_json,
                current_json,
            ]

            compare_result = subprocess.run(compare_cmd)

            if compare_result.returncode != 0:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("   PERFORMANCE REGRESSION DETECTED")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                if args.strict:
                    sys.exit(1)
            else:
                print("Performance is within acceptable limits.")
        else:
            print(
                "Comparison script not found (benchmarks/infrastructure/compare.py). Skipping comparison."
            )
    else:
        print("No baseline found. This run effectively sets the new baseline.")

    print(f"\n[Action] To update baseline: cp {current_json} {baseline_json}")


if __name__ == "__main__":
    run_benchmarks()
