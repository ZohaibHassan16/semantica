from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .metrics import accuracy_score, absolute_lift, relative_lift, safe_mean


def coverage_summary(
    *,
    executed: int,
    eligible: int,
    required: int | None = None,
) -> dict[str, float | int | bool]:
    eligible = max(int(eligible), 0)
    executed = max(int(executed), 0)
    required = eligible if required is None else max(int(required), 0)
    executed_ratio = executed / eligible if eligible else 0.0
    required_ratio = required / eligible if eligible else 0.0
    return {
        "eligible": eligible,
        "executed": executed,
        "required": required,
        "executed_ratio": executed_ratio,
        "required_ratio": required_ratio,
        "meets_required_coverage": executed >= required,
    }


def paired_lift_report(
    expected: Sequence[str],
    baseline: Sequence[str],
    contextual: Sequence[str],
) -> dict[str, float]:
    baseline_accuracy = accuracy_score(expected, baseline)
    contextual_accuracy = accuracy_score(expected, contextual)
    return {
        "baseline_accuracy": baseline_accuracy,
        "contextual_accuracy": contextual_accuracy,
        "absolute_lift": absolute_lift(contextual_accuracy, baseline_accuracy),
        "relative_lift": relative_lift(contextual_accuracy, baseline_accuracy),
    }


def binary_rate(values: Iterable[bool]) -> float:
    collected = [1.0 if value else 0.0 for value in values]
    return safe_mean(collected)


def make_track_report(
    *,
    name: str,
    sample_size: int,
    metrics: Mapping[str, Any],
    slices: Mapping[str, Any] | None = None,
    baselines: Mapping[str, Any] | None = None,
    coverage: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report = {
        "name": name,
        "sample_size": int(sample_size),
        "metrics": dict(metrics),
        "slices": dict(slices or {}),
        "baselines": dict(baselines or {}),
        "coverage": dict(coverage or {}),
        "metadata": dict(metadata or {}),
    }
    for key, value in metrics.items():
        report[key] = value
    return report


def credibility_guard(
    report: Mapping[str, Any],
    *,
    min_sample_size: int = 1,
    min_executed_ratio: float = 1.0,
    required_metrics: Sequence[str] = (),
) -> dict[str, Any]:
    reasons: list[str] = []
    sample_size = int(report.get("sample_size", 0))
    coverage = report.get("coverage", {}) or {}
    executed_ratio = float(coverage.get("executed_ratio", 0.0 if sample_size == 0 else 1.0))

    if sample_size < min_sample_size:
        reasons.append(
            f"sample_size {sample_size} is below required minimum {min_sample_size}"
        )
    if executed_ratio < min_executed_ratio:
        reasons.append(
            f"executed_ratio {executed_ratio:.3f} is below required minimum {min_executed_ratio:.3f}"
        )

    metrics = report.get("metrics", {}) or {}
    for key in required_metrics:
        if key not in metrics:
            reasons.append(f"required metric '{key}' is missing")

    return {
        "reportable": not reasons,
        "reasons": reasons,
        "min_sample_size": min_sample_size,
        "min_executed_ratio": min_executed_ratio,
    }


def require_reportable(
    report: Mapping[str, Any],
    *,
    min_sample_size: int = 1,
    min_executed_ratio: float = 1.0,
    required_metrics: Sequence[str] = (),
) -> None:
    verdict = credibility_guard(
        report,
        min_sample_size=min_sample_size,
        min_executed_ratio=min_executed_ratio,
        required_metrics=required_metrics,
    )
    if verdict["reportable"]:
        return
    raise AssertionError("; ".join(verdict["reasons"]))
