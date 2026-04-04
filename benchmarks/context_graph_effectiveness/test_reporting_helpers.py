from __future__ import annotations

from benchmarks.context_graph_effectiveness.reporting import (
    coverage_summary,
    credibility_guard,
    make_track_report,
    paired_lift_report,
    require_reportable,
)


def test_paired_lift_report_computes_accuracy_delta():
    report = paired_lift_report(
        ["approve", "reject", "escalate"],
        ["approve", "approve", "approve"],
        ["approve", "reject", "escalate"],
    )
    assert report["baseline_accuracy"] == 1 / 3
    assert report["contextual_accuracy"] == 1.0
    assert report["absolute_lift"] > 0.0


def test_coverage_summary_tracks_execution_ratio():
    coverage = coverage_summary(executed=48, eligible=60, required=45)
    assert coverage["executed_ratio"] == 0.8
    assert coverage["meets_required_coverage"] is True


def test_credibility_guard_flags_undercovered_reports():
    report = make_track_report(
        name="demo",
        sample_size=12,
        metrics={"accuracy": 0.9},
        coverage=coverage_summary(executed=6, eligible=12, required=10),
    )
    verdict = credibility_guard(
        report,
        min_sample_size=10,
        min_executed_ratio=0.75,
        required_metrics=("accuracy", "precision"),
    )
    assert verdict["reportable"] is False
    assert verdict["reasons"]


def test_require_reportable_passes_for_complete_report():
    report = make_track_report(
        name="complete",
        sample_size=20,
        metrics={"accuracy": 0.9, "precision": 0.88},
        coverage=coverage_summary(executed=20, eligible=20, required=20),
    )
    require_reportable(
        report,
        min_sample_size=10,
        min_executed_ratio=1.0,
        required_metrics=("accuracy", "precision"),
    )
