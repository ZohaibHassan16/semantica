# Skill Injection Conventions

Context graphs in Semantica can encode behavioral scaffolding: structured context that should change an agent's behavior in measurable ways when injected into a prompt.

## Evaluated Skill Types

### 1. Temporal Awareness
- Encoding: node with `valid_from` / `valid_until` linked to the decision path
- Expected behavior: the agent qualifies answers with correct time bounds

### 2. Causal Reasoning
- Encoding: causal chain with multiple hops
- Expected behavior: the agent explains the cause before the effect and keeps the chain grounded

### 3. Policy Compliance
- Encoding: policy nodes and exception nodes linked to the scenario
- Expected behavior: the agent follows applicable rules and identifies exceptions

### 4. Precedent Citation
- Encoding: precedent nodes linked to similar prior decisions
- Expected behavior: the agent cites relevant prior decisions instead of improvising unsupported rationale

### 5. Uncertainty Flagging
- Encoding: query with no matching or insufficient context
- Expected behavior: the agent says it is uncertain or asks for escalation rather than hallucinating

### 6. Approval Escalation
- Encoding: approval-chain node with multi-level requirements
- Expected behavior: the agent escalates when authority is insufficient

## Measurement Rules

Skill injection is a manual real-LLM benchmark.

That means:
- it should run only when `SEMANTICA_REAL_LLM=1`
- it should compare at least two real runs such as no-context vs injected-context
- it should use fixed prompts and a fixed model configuration
- it should be scored with labeled rubric checks, not hardcoded values

Recommended rubric dimensions:
- temporal-awareness correctness
- uncertainty-flagging correctness
- policy-grounding correctness
- escalation correctness
- citation groundedness

## Reporting

Report skill-injection results as manual benchmark evidence, not as CI status.

Use labels such as:
- `measured` for real scored runs
- `skipped` when no real LLM is enabled
- `partial` if the rubric or dataset still needs work

Do not use `MockLLM` output as evidence that a skill was activated.
