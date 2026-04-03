from __future__ import annotations

import pytest

from benchmarks.context_graph_effectiveness.thresholds import THRESHOLDS

pytestmark = pytest.mark.real_llm


def _activation_score(response: str, required_terms: set[str]) -> float:
    normalized = response.lower()
    hits = sum(1 for term in required_terms if term in normalized)
    return hits / len(required_terms)


def _run(real_llm, prompt: str) -> str:
    return real_llm.generate(prompt)


def test_temporal_awareness_skill(real_llm):
    prompt = (
        "Context graph:\n"
        "- Policy A valid_from=2024-01-01 valid_until=2024-12-31\n"
        "- Policy B valid_from=2025-01-01 valid_until=open\n"
        "Question: Which policy applied on 2024-06-15? Respond with time-aware reasoning."
    )
    score = _activation_score(_run(real_llm, prompt), {"2024", "policy a", "valid", "applied"})
    assert score >= THRESHOLDS["skill_activation_rate"][1]


def test_causal_reasoning_skill(real_llm):
    prompt = (
        "Context graph:\n"
        "A CAUSED B\nB CAUSED C\n"
        "Question: Explain why C happened and mention the causal chain."
    )
    score = _activation_score(_run(real_llm, prompt), {"a", "b", "c", "cause"})
    assert score >= THRESHOLDS["skill_activation_rate"][1]


def test_policy_compliance_skill(real_llm):
    prompt = (
        "Context graph:\n"
        "Policy: max_dti=0.43, min_score=680\n"
        "Applicant: dti=0.52, score=710\n"
        "Question: Decide approve/reject/escalate and reference policy constraints."
    )
    score = _activation_score(_run(real_llm, prompt), {"dti", "0.43", "policy", "reject"})
    assert score >= THRESHOLDS["skill_activation_rate"][1]


def test_precedent_citation_skill(real_llm):
    prompt = (
        "Context graph:\n"
        "Precedent P1 outcome=approve similarity=0.91\n"
        "Precedent P2 outcome=reject similarity=0.42\n"
        "Question: Make a decision and cite the strongest precedent."
    )
    score = _activation_score(_run(real_llm, prompt), {"precedent", "p1", "approve"})
    assert score >= THRESHOLDS["skill_activation_rate"][1]


def test_uncertainty_flagging_skill(real_llm):
    prompt = "No matching context nodes were retrieved. Answer the question without inventing facts."
    score = _activation_score(_run(real_llm, prompt), {"insufficient", "context", "cannot", "review"})
    assert score >= THRESHOLDS["skill_activation_rate"][1]


def test_approval_escalation_skill(real_llm):
    prompt = (
        "Context graph:\n"
        "Approval chain: analyst -> manager -> director\n"
        "The request exceeds analyst and manager limits. What should happen next?"
    )
    score = _activation_score(_run(real_llm, prompt), {"escalate", "director", "approval"})
    assert score >= THRESHOLDS["skill_activation_rate"][1]
