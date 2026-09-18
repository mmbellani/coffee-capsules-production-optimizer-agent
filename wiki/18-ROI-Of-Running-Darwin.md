# 18 — ROI of Running Darwin

This page quantifies the **return on investment** of using Darwin to optimize two
parts of this repo:

- **SQL / warehouse-build latency** — page [12](12-Darwin-Warehouse-Build-Speedup.md) (11.108 s → 3.582 s, 3.10×)
- **LLM narration token usage** — page [11](11-Darwin-Token-Optimization.md) (6,774 → 806 tokens, −88.1%)

ROI has two sides: a **one-time cost** (the Darwin search) and a **recurring
benefit** that accrues on every future build / agent run *forever*, at zero
marginal cost. The key question is therefore not "is each unit saving large?"
(it is small) but "how many future runs amortize the one-time search?"

> **All monetary figures below are illustrative.** They use explicit, clearly
> labelled unit prices — substitute your own cloud/LLM rates and run volumes to
> get your actual numbers. The *token and time savings themselves* (−88.1% and
> 3.10×) are measured; only the pricing is assumed.

---

## Assumptions (substitute your own)

> **Single source of truth.** Edit the values in the block below and every table on
> this page follows from them. Nothing downstream introduces a new number — each
> result cell shows the formula it comes from, so you only ever change inputs here.

```yaml
# ---- Darwin one-time search cost (from pages 11–12) ----
darwin_agent_model:        claude-sonnet-5
build_cost_usd:            60      # measured: ~$57 LLM + a few cents compute
token_cost_usd:            40      # estimated (page 11 reports no token table)

# ---- LLM prices ($ per 1M tokens) ----
llm_fresh_input_per_m:     3.00    # Sonnet-class list price
llm_cache_read_per_m:      0.30    # ~10% of fresh input (prompt cache)
llm_output_per_m:          15.00   # Sonnet-class list price

# ---- Narration model input price ($ per 1M tokens) ----
narrator_budget_per_m:     0.15    # e.g. gpt-4o-mini (repo's OpenAI default)
narrator_premium_per_m:    3.00    # e.g. GPT-4o / Sonnet-class

# ---- Time / compute valuation ----
developer_time_per_hr:     75.00   # fully-loaded; => $0.0208 / s for build waits
ci_compute_per_vcpu_hr:    0.20    # for pure-compute build valuation

# ---- Measured savings (do NOT change — these are results, not assumptions) ----
build_seconds_saved:       7.526   # 11.108 s -> 3.582 s  (3.10x, page 12)
narration_tokens_saved:    5968    # 6,774 -> 806 tokens  (-88.1%, page 11)

# ---- Your expected usage (drives the ROI-at-volume tables) ----
builds_per_year:           5000    # dev + CI rebuilds of the warehouse
agent_runs_per_year:       10000   # llm.narrate() executions
narrator_tier:             premium # premium | budget
```

| Assumption | Value used | Notes |
|---|---|---|
| Darwin agent model | `claude-sonnet-5` | as reported in pages 11–12 |
| LLM fresh input price | $3.00 / M tokens | Sonnet-class list price |
| LLM cache-read price | $0.30 / M tokens | ~10% of fresh input (prompt cache) |
| LLM output price | $15.00 / M tokens | Sonnet-class list price |
| Narration model (budget) | $0.15 / M input | e.g. `gpt-4o-mini`, the repo's OpenAI default |
| Narration model (premium) | $3.00 / M input | e.g. GPT-4o / Sonnet-class |
| Developer time value | $75 / hr = $0.0208 / s | fully-loaded, for wall-clock build waits |
| CI compute | $0.20 / vCPU-hr | for pure-compute build valuation |

### Derived unit values (auto-follow from the block above)

| Derived quantity | Formula | Value at defaults |
|---|---|---:|
| Build saving / build (dev-time) | `build_seconds_saved × developer_time_per_hr ÷ 3600` | $0.157 |
| Build saving / build (CI compute) | `build_seconds_saved × ci_compute_per_vcpu_hr ÷ 3600` | $0.00042 |
| Token saving / run (premium) | `narration_tokens_saved × narrator_premium_per_m ÷ 1e6` | $0.0179 |
| Token saving / run (budget) | `narration_tokens_saved × narrator_budget_per_m ÷ 1e6` | $0.000895 |
| Build break-even | `build_cost_usd ÷ (build saving / build)` | ≈ 382 builds |
| Token break-even (premium) | `token_cost_usd ÷ (token saving / run)` | ≈ 2,235 runs |

To re-run the whole page for your numbers: change the block, recompute the six
derived unit values above with the given formulas, then read the ROI at your
`builds_per_year` / `agent_runs_per_year` in [Part 4](#part-4--roi-at-representative-volumes-year-1).

---

## Part 1 — Cost of running Darwin (one-time)

### Warehouse-build experiment (page 12, measured)

The run reported **84 evaluations**: 86.6 M input tokens (of which **83.2 M
cache-read**, so **3.4 M fresh**) and **1.45 M output**.

$$\text{cost} = 3.4\text{M}\times\$3 + 83.2\text{M}\times\$0.30 + 1.45\text{M}\times\$15$$

| Component | Tokens | Unit price | Cost |
|---|---:|---:|---:|
| Fresh input | 3.4 M | $3.00 / M | $10.20 |
| Cache-read input | 83.2 M | $0.30 / M | $24.96 |
| Output | 1.45 M | $15.00 / M | $21.75 |
| **Total LLM** | | | **≈ $56.91** |

Compute for 84 cold builds (~11 s each ≈ 15 min of one core) is a few cents.
**Round to ≈ $60 all-in.** Prompt caching is doing heavy lifting here — without
it the gross 86.6 M input would have cost ~$260; caching cut the search's actual
bill by ~78%.

### Token-optimization experiment (page 11, estimated)

Page 11 does not report a token-spend table. Its winning program appears at
**iteration 8** (a shorter lineage than the build run's 60+ iterations), so its
search cost is plausibly *smaller* than the build run's ≈ $57. To stay
**conservative (over-stating cost lowers ROI)** we assume **≈ $40 all-in**.

---

## Part 2 — Recurring benefit per unit

### Warehouse build: 7.526 s saved per build

| Valuation basis | Rate | Saving per build |
|---|---|---:|
| Developer wall-clock wait | $0.0208 / s | **$0.157** |
| CI compute only | $0.20 / vCPU-hr | $0.00042 |

The developer-time basis is the meaningful one: the build sits in the inner
dev/CI feedback loop, and 3.10× faster feedback compounds across a working day.

### Token narration: 5,968 input tokens saved per agent run

| Narration model | Input rate | Saving per run |
|---|---|---:|
| Premium (GPT-4o / Sonnet-class) | $3.00 / M | **$0.0179** |
| Budget (`gpt-4o-mini`) | $0.15 / M | $0.000895 |

Plus a **latency** benefit: ~6 k fewer prompt tokens removes roughly 0.1–0.5 s of
prefill per narration (model-dependent), improving dashboard responsiveness.

---

## Part 3 — Break-even (how many runs amortize Darwin)

$$\text{break-even units} = \frac{\text{one-time Darwin cost}}{\text{saving per unit}}$$

| Optimization | One-time cost | Saving/unit | Break-even |
|---|---:|---:|---:|
| Build (developer-time) | $60 | $0.157 | **≈ 382 builds** |
| Build (CI compute only) | $60 | $0.00042 | ≈ 143,000 builds |
| Tokens (premium model) | $40 | $0.0179 | **≈ 2,235 runs** |
| Tokens (budget model) | $40 | $0.000895 | ≈ 44,700 runs |

Read this as: on developer-time value, the **build speedup pays for itself in
~382 rebuilds** — often a week or two of active development. Token payback depends
heavily on the narration model: a **premium narrator pays back in ~2,200 runs**; a
cheap one needs high volume.

---

## Part 4 — ROI at representative volumes (year 1)

$$\text{ROI} = \frac{\text{annual benefit} - \text{one-time cost}}{\text{one-time cost}}$$

### Warehouse build (developer-time value $0.157/build, cost $60)

| Builds / yr | Annual benefit | Net (yr 1) | ROI (yr 1) |
|---:|---:|---:|---:|
| 500 | $79 | +$19 | **+31%** |
| 5,000 | $785 | +$725 | **+1,208%** |
| 50,000 | $7,850 | +$7,790 | **+12,983%** |

### Token narration — premium narrator ($0.0179/run, cost $40)

| Runs / yr | Annual benefit | Net (yr 1) | ROI (yr 1) |
|---:|---:|---:|---:|
| 1,000 | $18 | −$22 | −55% |
| 10,000 | $179 | +$139 | **+348%** |
| 100,000 | $1,790 | +$1,750 | **+4,375%** |

### Token narration — budget narrator ($0.000895/run, cost $40)

| Runs / yr | Annual benefit | Net (yr 1) | ROI (yr 1) |
|---:|---:|---:|---:|
| 10,000 | $9 | −$31 | −78% |
| 100,000 | $90 | +$50 | **+124%** |
| 1,000,000 | $895 | +$855 | **+2,138%** |

Because the improvement is **permanent**, every subsequent year is essentially
pure benefit (no repeated Darwin cost), so multi-year ROI is far higher than the
year-1 figures above.

---

## Part 5 — Sensitivity: what moves the ROI

- **Run/build volume** — the dominant lever. Both optimizations are one-time
  costs amortized over unlimited future units; ROI scales linearly with volume.
- **Narration model price** — a 20× swing ($0.15 → $3.00 per M) moves token ROI by
  the same 20×. High-value narration models make the token win pay back fastest.
- **How you value build time** — pure CI compute makes the build speedup marginal;
  developer wall-clock time (the honest basis for an inner-loop build) makes it
  strongly positive.
- **Darwin cost** — dominated by cache-read tokens (cheap). Without prompt
  caching the search would cost ~4–5× more, roughly quadrupling break-even counts.

---

## Part 6 — Non-monetary ROI (often the real value)

- **Permanence & compounding** — unlike a consultant fix, the improvement is
  committed code that applies to *every future run at zero marginal cost*. The
  one-time cost never recurs.
- **Correctness-guaranteed** — the build speedup ships with a hard equivalence
  gate (byte-identical tables, see pages [12](12-Darwin-Warehouse-Build-Speedup.md)
  and [17](17-SQL-Result-Equality-Literature-Review.md)); the token cut leaves the
  canonical result hash unchanged. There is no quality/accuracy debt to pay back.
- **Faster feedback loop** — 3.10× quicker warehouse rebuilds shorten the
  dev/CI cycle, which has second-order value (more iterations/day) that the
  per-build dollar figure understates.
- **Engineer time saved** — the search is autonomous. The alternative (a human OR
  engineer profiling SQL or hand-compacting prompts) costs far more than $40–60 of
  API spend and is not guaranteed to find the same tightening.

---

## Bottom line

| | Warehouse build (SQL) | Token narration |
|---|---|---|
| Measured improvement | **3.10× faster** (−7.526 s/build) | **−88.1%** (−5,968 tokens/run) |
| One-time Darwin cost | ≈ $60 | ≈ $40 (est.) |
| Saving per unit | $0.157 (dev-time) | $0.0179 (premium) / $0.0009 (budget) |
| Break-even | ≈ **382 builds** | ≈ **2,235** (premium) / 44,700 (budget) runs |
| Best ROI driver | developer/CI feedback speed | high run volume + premium narrator |

**Conclusion.** Each individual saving is small (cents), but both optimizations are
**one-time costs that pay back over unlimited future runs**. The **SQL build
speedup has the clearer, faster payback** — a few hundred rebuilds on any active
project — because build time sits in the developer inner loop. The **token
optimization's ROI is volume- and model-sensitive**: it is compelling for
high-frequency agent use or a premium narration model, and marginal for
low-volume use with a cheap model. In both cases the improvement is permanent,
correctness-guaranteed, and found autonomously for tens of dollars of mostly
cache-priced API spend — so at any non-trivial usage volume, running Darwin is
strongly ROI-positive.
