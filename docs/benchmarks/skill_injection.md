# Skill Injection Conventions

Context graphs in Semantica can encode behavioral scaffolding — structured nodes that reliably elicit specific reasoning patterns when serialized into an agent prompt.

## Evaluated Skill Types

### 1. Temporal Awareness
- **Encoding**: Node with `valid_from` / `valid_until` + edge to decision.
- **Assertion**: Agent qualifies claims with time bounds.

### 2. Causal Reasoning
- **Encoding**: Causal chain with 3+ hops.
- **Assertion**: Agent explains cause before effect; cites chain.

### 3. Policy Compliance
- **Encoding**: Policy node with rules + `PolicyException` node.
- **Assertion**: Agent respects constraints; flags exceptions.

### 4. Precedent Citation
- **Encoding**: Precedent node linked to decision.
- **Assertion**: Agent references prior similar decision.

### 5. Uncertainty Flagging
- **Encoding**: Query with no matching context node.
- **Assertion**: Agent expresses uncertainty rather than hallucinating.

### 6. Approval Escalation
- **Encoding**: `ApprovalChain` node with multi-level requirements.
- **Assertion**: Agent escalates rather than deciding unilaterally.

All of these skills are tracked with a `skill_activation_rate` in the Context Graph Effectiveness benchmarks, which must remain `>= 0.70` to pass CI.
