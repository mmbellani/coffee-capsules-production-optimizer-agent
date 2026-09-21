# Clipchamp Video Script — "Darwin: Optimization Proven in Production" (1:45)

**Runtime:** 1 min 45 s · **Narration:** ~190 words (≈125 wpm plus visual pauses) · **Tone:** confident, upbeat, technical-but-accessible

Format per row: **[timecode] VISUAL** — *Voiceover (VO)*

---

### 0:00–0:12 · Meet Darwin
**VISUAL:** Darwin logo → code branches evolve while benchmark scores rise.
**VO:** "What if software could improve itself — and prove every improvement before you ship it? That's Darwin: an evolutionary coding agent built to find measurable, verified code optimizations."

### 0:12–0:30 · How Darwin works
**VISUAL:** Animated loop: inspect → mutate code → execute benchmark → validate → retain winner.
**VO:** "Darwin searches beyond a single AI-generated answer. It creates competing code variants, runs them, measures them against a clear objective, and evolves the strongest candidates. Each experiment turns engineering goals — speed, cost, fulfilment, or margin — into executable evidence."

### 0:30–0:45 · Real-world test
**VISUAL:** Darwin connects to the Coffee Capsule Production Optimizer; dashboard, SQL warehouse, agent, and MILP schedule appear briefly.
**VO:** "We tested Darwin on a real application: a coffee capsule production optimizer processing twenty-seven million sensor readings, warehouse analytics, LLM narration, and production-planning solvers. A varied codebase, with real operational constraints."

### 0:45–1:20 · Darwin's measured results
**VISUAL:** Four bold result cards animate in one by one, each with a big number and a green ✓.
**VO:** "Darwin improved four very different workloads.
It made warehouse builds three-point-one times faster, with verified-identical tables.
It cut LLM prompt tokens by eighty-eight percent, with canonical output unchanged.
It raised demand fulfilment to one hundred percent, with zero changeovers.
And it found extra margin in an already-optimized solver, while preserving feasibility."

### 1:20–1:38 · Why Darwin is usable
**VISUAL:** Candidate variants fail at a red gate; the verified winner enters the codebase. Checklist: correct ✓ feasible ✓ measurable ✓.
**VO:** "That is what makes Darwin practical. Hard gates reject candidates that break correctness or feasibility. The winning optimization is committed as ordinary application code, so its measured benefit continues across future runs."

### 1:38–1:45 · Close
**VISUAL:** Darwin logo leads; the app appears as a smaller case-study badge. Tagline: *"Evolve code. Measure results. Keep what works."*
**VO:** "Real software. Verified gains. Darwin turns optimization into an evolutionary process."

---

## Key numbers (for on-screen lower-thirds)

| Result card | Big number | Sub-line |
|---|---|---|
| Warehouse build | **3.10× faster** | 11.1 s → 3.58 s · byte-identical |
| LLM narration | **−88.1% tokens** | 6,774 → 806 · identical output |
| Planner fulfilment | **100%** | +1.76 pp · 0 changeovers · feasible |
| Optimizer margin | **+0.19%** | provably feasible · already-optimal MILP |

## Production notes

- **Clipchamp voice pace:** target about 125 words per minute. Keep the pauses shown
  by the timecodes; do not use the default fast read just to fill every second.
- **Pace:** the 0:45–1:20 results block is the climax — let each number land with a
  beat and a ✓ sound. Don't rush the four wins.
- **B-roll sources in repo:** dashboard (`app/dashboard.py`), the MILP schedule and
  Pareto plots, and the `report/*.png` charts from the warehouse-speedup run.
- **Accuracy:** all figures trace to wiki pages 11–14; keep the "correctness/
  feasibility gate" framing so no claim overstates what was measured.
- **Optional 5 s tag** (if trimming to fit): drop the app-detail line at 0:12–0:30
  to buy headroom.
