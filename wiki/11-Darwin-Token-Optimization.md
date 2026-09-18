# 11 — Darwin Token Optimization

## Summary

Reduces the LLM "executive narration" prompt from **6,774 → 806 tokens (−88.1%)**
while leaving the deterministic production schedule, findings, and plan KPIs
**byte‑for‑byte identical**.

The agent first runs a deterministic optimisation engine (MILP production
schedule + rule‑based findings), then calls `llm.narrate()` only to turn the
already‑computed results into a business‑language executive brief. The narration
payload was serialising the *full* internal data structures — including large
fields the model never needs to cite. This change sends compact, narration‑only
views of those structures instead.

## How the token reduction is made

Two "full‑fidelity vs. narration‑only" splits, following one pattern:

1. **Plan compaction** — new `ProductionPlan.as_narration_dict()` in
   `agent/planner.py` sends only `start_date`, `end_date`, `demand`, `capacity`,
   and `summary` to the LLM, dropping the full per‑line/per‑day `schedule` table,
   the per‑event `maintenance` table, `params`, and `rationale`.
2. **Findings compaction** — new `Finding.as_narration_dict()` in
   `agent/analyzers.py` sends only `id`, `area`, `severity`, `scope`,
   `impact_capsules`, and `impact_eur` for the top‑10 findings, dropping the
   verbose `title`, `detail`, `recommendation`, and `evidence` prose.
   `agent/agent.py` uses this compact view when assembling the `narrate()`
   payload.

`as_dict()` — used for `AgentReport`, the `findings.json` artifact, and the
canonical result hash — is left untouched, so downstream consumers still get the
complete structures. The dropped fields are prose the system prompt already
instructs the model to write itself, and they are **not** part of the hashed
result, so trimming them cannot change the output.

## Why it is safe (schedule unchanged)

Verified by running the deterministic engine on this branch **and** on the
pristine baseline and diffing the outputs: identical planned capsules,
changeovers, maintenance events, `total_impact_eur`, `impact_by_area_eur`, and
finding ids — a byte‑identical canonical hash. Only the LLM prompt shrinks.

## The idea

> Separate full‑fidelity structures (reports / artifacts / canonical hash) from
> compact narration‑only views for the LLM. Add `.as_narration_dict()` helpers
> that keep only the fields the model needs to cite — id / area / severity /
> scope / impact for findings, and date / demand / capacity / summary for the
> plan — dropping verbose prose and per‑day tables that are not part of the
> hashed result.

## Darwin lineage

This change was discovered automatically by Darwin (an evolutionary coding
agent) using its MAP‑Elites island search. The winning program's ancestry
(island 2):

| iter | idea | change | prompt tokens | savings |
|---:|---:|---|---:|---:|
| 0 | — | seed: unmodified baseline agent | 6,774 | — |
| 2 | 4 | compact `json.dumps` separators + drop the `[:12000]` truncation inside `narrate()` | 6,774 | 0% |
| 5 | 13 | **`ProductionPlan.as_narration_dict()`** (plan compaction) | 1,653 | 75.6% |
| 8 | 26 | **`Finding.as_narration_dict()`** (findings compaction) — winner | 806 | 88.1% |

The iter‑2 step was a dead end: it compacted serialisation *inside* `narrate()`,
which the token metric cannot see (the payload is measured before `narrate()`
re‑serialises it). The search then found the two structural compactions that
compound — the plan split (−75.6%), then the findings split on top of it
(−88.1% total). This PR is the winning program (iteration 8), which contains
both compactions across `agent/planner.py`, `agent/analyzers.py`, and
`agent/agent.py`.
