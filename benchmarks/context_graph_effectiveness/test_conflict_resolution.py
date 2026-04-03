from __future__ import annotations

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.conflicts.conflict_analyzer import ConflictAnalyzer
from semantica.conflicts.conflict_detector import Conflict, ConflictDetector, ConflictType
from semantica.conflicts.conflict_resolver import ConflictResolver, ResolutionStrategy
from semantica.conflicts.investigation_guide import InvestigationGuideGenerator


def _value_entities():
    return [
        {"id": "company_1", "type": "Company", "revenue": 10, "source": {"document": "a", "confidence": 0.7}},
        {"id": "company_1", "type": "Company", "revenue": 12, "source": {"document": "b", "confidence": 0.9}},
    ]


def test_detection_recall_by_conflict_type():
    detector = ConflictDetector()
    value_conflicts = detector.detect_value_conflicts(_value_entities(), "revenue")
    type_conflicts = detector.detect_type_conflicts([
        {"id": "entity_x", "type": "Person"},
        {"id": "entity_x", "type": "Organization"},
    ])
    temporal_conflicts = detector.detect_temporal_conflicts([
        {"id": "entity_t", "type": "Policy", "timestamp": "2026-01-01T00:00:00", "source": {"document": "a"}},
        {"id": "entity_t", "type": "Policy", "timestamp": "2024-01-01T00:00:00", "source": {"document": "b"}},
    ])
    logical_conflicts = detector.detect_logical_conflicts([
        {"id": "entity_l", "type": "Person"},
        {"id": "entity_l", "type": "Organization"},
    ])
    detected = sum(bool(group) for group in [value_conflicts, type_conflicts, temporal_conflicts, logical_conflicts])
    recall = detected / 4
    assert recall >= THRESHOLDS["conflict_detection_recall"][1]


def test_detection_precision():
    detector = ConflictDetector()
    conflicts = detector.detect_value_conflicts(_value_entities(), "revenue")
    precision = len([conflict for conflict in conflicts if conflict.property_name == "revenue"]) / max(len(conflicts), 1)
    assert precision >= THRESHOLDS["conflict_detection_precision"][1]


def test_resolution_strategy_voting():
    resolver = ConflictResolver(strategy=ResolutionStrategy.VOTING)
    conflict = Conflict(
        conflict_id="c1",
        conflict_type=ConflictType.VALUE_CONFLICT,
        entity_id="x",
        property_name="status",
        conflicting_values=["approved", "approved", "rejected"],
        sources=[{"source": "a", "confidence": 0.8}, {"source": "b", "confidence": 0.7}, {"source": "c", "confidence": 0.6}],
    )
    result = resolver.resolve_conflict(conflict, strategy=ResolutionStrategy.VOTING)
    assert result.resolved_value == "approved"


def test_resolution_strategy_credibility_weighted():
    resolver = ConflictResolver()
    conflict = Conflict(
        conflict_id="c2",
        conflict_type=ConflictType.VALUE_CONFLICT,
        entity_id="x",
        property_name="amount",
        conflicting_values=[100, 120],
        sources=[{"source": "a", "credibility": 0.2}, {"source": "b", "credibility": 0.9}],
    )
    result = resolver.resolve_conflict(conflict, strategy=ResolutionStrategy.CREDIBILITY_WEIGHTED)
    assert result.resolved is True


def test_resolution_strategy_most_recent():
    resolver = ConflictResolver()
    conflict = Conflict(
        conflict_id="c3",
        conflict_type=ConflictType.TEMPORAL_CONFLICT,
        entity_id="x",
        property_name="status",
        conflicting_values=["old", "new"],
        sources=[
            {"source": "a", "timestamp": "2024-01-01T00:00:00"},
            {"source": "b", "timestamp": "2025-01-01T00:00:00"},
        ],
    )
    result = resolver.resolve_conflict(conflict, strategy=ResolutionStrategy.MOST_RECENT)
    assert result.resolved is True


def test_resolution_strategy_highest_confidence():
    resolver = ConflictResolver()
    conflict = Conflict(
        conflict_id="c4",
        conflict_type=ConflictType.VALUE_CONFLICT,
        entity_id="x",
        property_name="status",
        conflicting_values=["old", "new"],
        sources=[{"source": "a", "confidence": 0.2}, {"source": "b", "confidence": 0.95}],
    )
    result = resolver.resolve_conflict(conflict, strategy=ResolutionStrategy.HIGHEST_CONFIDENCE)
    assert result.resolved is True


def test_severity_scoring_calibration():
    analyzer = ConflictAnalyzer()
    high = Conflict(conflict_id="h", conflict_type=ConflictType.VALUE_CONFLICT, severity="high", entity_id="1")
    low = Conflict(conflict_id="l", conflict_type=ConflictType.VALUE_CONFLICT, severity="low", entity_id="2")
    analysis = analyzer.analyze_conflicts([high, low])
    high_count = analysis["by_severity"]["counts"].get("high", 0)
    low_count = analysis["by_severity"]["counts"].get("low", 0)
    assert high_count == low_count == 1


def test_investigation_guide_completeness():
    generator = InvestigationGuideGenerator()
    conflict = Conflict(
        conflict_id="guide-1",
        conflict_type=ConflictType.VALUE_CONFLICT,
        entity_id="company_1",
        property_name="revenue",
        conflicting_values=[10, 12],
        severity="high",
        sources=[{"document": "a"}, {"document": "b"}],
    )
    guide = generator.generate_guide(conflict)
    assert len(guide.investigation_steps) > 0
