# Context Graph Effectiveness Benchmark Suite
# Measures semantic effectiveness of Semantica context graphs:
# accuracy, temporal validity, causal grounding, provenance integrity,
# decision quality delta, and skill injection fidelity.
#
# All tests compute real metrics against committed datasets.
# No hardcoded assertion values.
#
# Run (non-LLM):
#   pytest benchmarks/context_graph_effectiveness/ -v
#
# Run (real-LLM, requires SEMANTICA_REAL_LLM=1 + ANTHROPIC_API_KEY):
#   SEMANTICA_REAL_LLM=1 pytest benchmarks/context_graph_effectiveness/ -v -m real_llm
