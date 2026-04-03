from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS
from semantica.reasoning.datalog_reasoner import DatalogReasoner
from semantica.reasoning.explanation_generator import ExplanationGenerator
from semantica.reasoning.reasoner import InferenceResult, Reasoner, Rule, RuleType
from semantica.reasoning.temporal_reasoning import IntervalRelation, TemporalInterval, TemporalReasoningEngine


def test_rule_inference_accuracy():
    reasoner = Reasoner()
    reasoner.add_fact("Person(Alice)")
    reasoner.add_fact("Employee(Alice)")
    rule = Rule(
        rule_id="r1",
        name="employee_implies_worker",
        conditions=["Employee(Alice)"],
        conclusion="Worker(Alice)",
        rule_type=RuleType.IMPLICATION,
    )
    reasoner.add_rule(rule)
    inferred = reasoner.forward_chain()
    conclusions = {item.conclusion for item in inferred}
    expected = {"Worker(Alice)"}
    accuracy = len(conclusions & expected) / len(expected)
    assert accuracy == 1.0


def test_datalog_recursive_accuracy():
    reasoner = DatalogReasoner()
    reasoner.add_fact("parent(alice,bob)")
    reasoner.add_fact("parent(bob,charlie)")
    reasoner.add_fact("parent(charlie,dana)")
    reasoner.add_rule("ancestor(X,Y) :- parent(X,Y).")
    reasoner.add_rule("ancestor(X,Y) :- parent(X,Z), ancestor(Z,Y).")
    results = reasoner.query("ancestor(alice,Y)")
    descendants = {row["Y"] for row in results}
    assert descendants == {"bob", "charlie", "dana"}


def test_allen_interval_relation_coverage():
    engine = TemporalReasoningEngine()
    cases = [
        (TemporalInterval(datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 5, tzinfo=timezone.utc)), TemporalInterval(datetime(2024, 1, 6, tzinfo=timezone.utc), datetime(2024, 1, 10, tzinfo=timezone.utc)), IntervalRelation.BEFORE),
        (TemporalInterval(datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 5, tzinfo=timezone.utc)), TemporalInterval(datetime(2024, 1, 5, tzinfo=timezone.utc), datetime(2024, 1, 10, tzinfo=timezone.utc)), IntervalRelation.MEETS),
        (TemporalInterval(datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 8, tzinfo=timezone.utc)), TemporalInterval(datetime(2024, 1, 5, tzinfo=timezone.utc), datetime(2024, 1, 10, tzinfo=timezone.utc)), IntervalRelation.OVERLAPS),
    ]
    correct = 0
    for left, right, expected in cases:
        if engine.relation(left, right) == expected:
            correct += 1
    assert correct / len(cases) == 1.0


def test_explanation_completeness():
    generator = ExplanationGenerator()
    rule = Rule(rule_id="r1", name="sample_rule", conditions=["A", "B"], conclusion="C")
    result = InferenceResult(conclusion="C", rule_used=rule, premises=["A", "B"], confidence=1.0)
    explanation = generator.generate_explanation(result)
    path = explanation.reasoning_path
    assert path is not None
    completeness = len(path.steps) / (len(result.premises) + 1)
    assert completeness >= THRESHOLDS["explanation_completeness"][1]


def test_sparql_result_correctness():
    try:
        from rdflib import Graph, Literal, Namespace
    except ImportError:
        pytest.skip("rdflib not installed")

    ex = Namespace("http://example.org/")
    graph = Graph()
    graph.add((ex.alice, ex.role, Literal("Engineer")))
    graph.add((ex.bob, ex.role, Literal("Designer")))
    query = """
    PREFIX ex: <http://example.org/>
    SELECT ?person WHERE {
      ?person ex:role "Engineer" .
    }
    """
    rows = list(graph.query(query))
    assert len(rows) == 1
    assert str(rows[0][0]).endswith("alice")


def test_reasoning_latency():
    reasoner = DatalogReasoner()
    for index in range(40):
        reasoner.add_fact(f"edge(n{index},n{index+1})")
    reasoner.add_rule("reachable(X,Y) :- edge(X,Y).")
    reasoner.add_rule("reachable(X,Y) :- edge(X,Z), reachable(Z,Y).")
    start = time.perf_counter()
    results = reasoner.query("reachable(n0,Y)")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert results
    assert elapsed_ms < 500
