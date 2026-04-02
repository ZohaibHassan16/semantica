"""
Track 22 — NL-to-Governed-Decision (Real LLM)

Tests that injecting governed metric definitions from the semantic layer into
LLM decision prompts produces better, more grounded decisions than a baseline
without semantic layer context.

All tests require SEMANTICA_REAL_LLM=1 and ANTHROPIC_API_KEY — skipped in
normal CI. Run weekly via .github/workflows/benchmark_real_llm.yml.

Metrics:
    governed_decision_delta         > 0.35  (accuracy lift from semantic layer injection)
    semantic_hallucination_rate    <= 0.05  (hallucinated metric names not in semantic layer)

Evidence basis:
    dbt Labs 2025 benchmark shows semantic layer raises LLM metric accuracy from ~40%
    to 83% (+43pp lift). Conservative threshold of 0.35 delta is set below that to
    account for narrower evaluation scope.
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List

FIXTURES = Path(__file__).parent / "fixtures" / "semantic_layer"

pytestmark = pytest.mark.real_llm


def _load(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def jaffle_metrics():
    return {m["name"]: m for m in _load("jaffle_shop_metrics.json")["metrics"]}


@pytest.fixture(scope="module")
def nl_queries():
    return _load("jaffle_shop_metrics.json")["nl_queries"]


def _build_semantic_layer_context(metrics: Dict) -> str:
    """Render governed metric definitions as a structured context block."""
    lines = ["## Governed Metrics (Semantic Layer)\n"]
    for name, m in metrics.items():
        lines.append(f"**{name}**")
        lines.append(f"  Expression: {m.get('expression', 'N/A')}")
        lines.append(f"  Grain: {m.get('grain', 'N/A')}")
        dims = ", ".join(m.get("dimensions", []))
        lines.append(f"  Dimensions: {dims}")
        aliases = ", ".join(m.get("aliases", []))
        if aliases:
            lines.append(f"  Aliases: {aliases}")
        lines.append("")
    return "\n".join(lines)


def _build_decision_prompt(query: str, context: str = "") -> str:
    base = (
        "You are a data analyst making a business decision.\n"
        "Answer with ONLY a JSON object: "
        '{"metric": "<metric_name>", "decision": "<approve|reject|escalate>", '
        '"reasoning": "<1 sentence>"}\n\n'
    )
    if context:
        base += f"{context}\n\n"
    base += f"Query: {query}"
    return base


def _parse_response(response: str) -> Dict:
    """Extract JSON from LLM response."""
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


class TestNLGovernedDecision:
    """Track 22 — NL-to-Governed-Decision (real LLM required)."""

    def test_governed_decision_delta(self, real_llm, nl_queries, jaffle_metrics):
        """Semantic layer injection improves decision accuracy over unguided baseline."""
        sl_context = _build_semantic_layer_context(jaffle_metrics)
        canonical_names = set(jaffle_metrics.keys())

        baseline_correct = 0
        sl_correct = 0
        total = 0

        for q in nl_queries:
            expected_metric = q.get("governed_metric")
            if not expected_metric or expected_metric not in canonical_names:
                continue

            query_text = q["query"]
            total += 1

            # Baseline: no semantic layer context
            baseline_prompt = _build_decision_prompt(query_text)
            baseline_resp = _parse_response(real_llm.generate(baseline_prompt))
            baseline_hit = baseline_resp.get("metric", "").lower() == expected_metric.lower()
            if baseline_hit:
                baseline_correct += 1

            # With semantic layer context
            sl_prompt = _build_decision_prompt(query_text, context=sl_context)
            sl_resp = _parse_response(real_llm.generate(sl_prompt))
            sl_hit = sl_resp.get("metric", "").lower() == expected_metric.lower()
            if sl_hit:
                sl_correct += 1

        if total == 0:
            pytest.skip("No evaluable NL queries in fixture")

        baseline_acc = baseline_correct / total
        sl_acc = sl_correct / total
        delta = sl_acc - baseline_acc

        assert delta > 0.35, (
            f"governed_decision_delta = {delta:.3f} <= 0.35 "
            f"(baseline={baseline_acc:.3f}, with_sl={sl_acc:.3f}, n={total})"
        )

    def test_semantic_hallucination_rate(self, real_llm, nl_queries, jaffle_metrics):
        """LLM does not hallucinate non-existent metric names when given semantic layer."""
        sl_context = _build_semantic_layer_context(jaffle_metrics)
        canonical_names = set(jaffle_metrics.keys())

        hallucinated = 0
        total = 0

        for q in nl_queries:
            query_text = q.get("query", "")
            if not query_text:
                continue
            total += 1

            prompt = _build_decision_prompt(query_text, context=sl_context)
            resp = _parse_response(real_llm.generate(prompt))
            metric_returned = resp.get("metric", "")

            if metric_returned and metric_returned.lower() not in {
                m.lower() for m in canonical_names
            }:
                hallucinated += 1

        if total == 0:
            pytest.skip("No queries to evaluate")

        rate = hallucinated / total
        assert rate <= 0.05, (
            f"semantic_hallucination_rate = {rate:.3f} > 0.05 "
            f"({hallucinated}/{total} hallucinated metric names)"
        )
