# 18 — ROI of Running Darwin

## Executive summary

**Darwin's key selling point is engineering leverage: automate the search for
better-performing code, keep engineers in control of review and validation, and
reuse the resulting improvements on future runs without repeating the search.**
The value is not just a cheaper execution; it is reducing the human effort needed
to discover and test optimizations that continue to deliver benefits.

For this coffee capsule optimizer, the business case has three parts:

| Value driver | Evidence or planning assumption | Business significance |
|---|---|---|
| **Faster SQL warehouse execution** | **Measured:** 11.108 s → 3.582 s per cold build; 3.10× speedup | Refreshed tables become available 7.526 s sooner; at 5,000 comparable builds, cumulative execution time falls by **10.45 hours** |
| **Less narration input per run** | **Measured:** 6,774 → 806 input tokens; **88.1% reduction** | Lower narration input cost on each applicable run, without changing the deterministic production plan |
| **Less engineering effort to optimize** | **Illustrative:** 40 manual hours versus 8 Darwin-assisted hours | **32 engineering hours released**; $3,000 manual labor versus approximately $700 for Darwin labor plus search, a **$2,300 lower one-time cost** |

**The strongest commercial argument here is the engineering capacity released,
not the small per-run cloud saving.** At the selected $75/hour rate, the assumed
manual-versus-Darwin cost reduction is **76.7%**, including Darwin's approximately
$100 API/compute spend. This is a planning scenario, not measured proof of a
fivefold engineering-productivity gain; it assumes equivalent validated outcomes.
Manual tooling and compute costs are not included.

The bottom-up manual-effort estimates are **3–4 engineer-days for SQL**,
**1–2 for prompt-payload optimization**, and **3–5 for application/MILP
optimization**. The SQL-plus-prompt central estimate remains **40 hours**;
the separate MILP estimate is **32 hours** and is **not included** in the $700
investment or recurring ROI calculations. See
[Illustrative engineering effort by optimization area](#illustrative-engineering-effort-by-optimization-area).

The runtime benefits are supported by controlled build benchmarks and checks on
the resulting tables and deterministic outputs. That makes the performance case
more concrete than a suggestion to rewrite code, while **human review and
validation remain necessary**. The measured SQL speedup applies to the warehouse
build, not every downstream query, and reduced narration tokens do not by
themselves prove unchanged narrative quality.

**Investment decision:** at 5,000 builds and 10,000 agent runs annually, the
approximately **$700 investment** has modeled first-year economic ROI of
**37.6% with a premium narrator** or **13.3% with a budget narrator**, with payback
in **8.7–10.6 months**. Those returns depend on saved build-wait time becoming
useful engineering time; compute and token savings alone do not repay the
investment in year 1. The $2,300 advantage over manual optimization is a separate
comparison and is not added to those recurring benefits.

**Position Darwin as an optimization accelerator, not a replacement for
engineers or a guarantee of savings:** it is most compelling where manual
profiling and experimentation are expensive, results can be benchmarked and
validated, and the improved code will be reused often.

---

This page quantifies the **return on investment** of using Darwin to optimize two
parts of this repo:

- **SQL / warehouse-build latency** — page [12](12-Darwin-Warehouse-Build-Speedup.md) (11.108 s → 3.582 s, 3.10×)
- **LLM narration token usage** — page [11](11-Darwin-Token-Optimization.md) (6,774 → 806 tokens, −88.1%)

It also documents a separate manual-effort estimate for the **application/MILP
margin improvement** — page [13](13-Darwin-Optimizer-Margin-Gain.md)
(approximately +0.19% optimized gross margin). MILP search spend and assisted
human effort are not reported, so no MILP net savings or payback are calculated.

ROI has two sides: a **one-time cost** (the Darwin search plus engineering
setup, supervision, review, and validation) and a **recurring
benefit** that accrues on every future build / agent run *forever*, at zero
marginal cost. The key question is therefore not "is each unit saving large?"
(it is small) but "how many future runs amortize the one-time search?"

> **All monetary figures below are illustrative.** They use explicit, clearly
> labelled unit prices — substitute your own cloud/LLM rates and run volumes to
> get your actual numbers. The *token and time savings themselves* (−88.1% and
> 3.10×) are measured; pricing, engineering effort, and future usage are assumptions.

---

## Assumptions (substitute your own)

> **SQL-plus-prompt ROI inputs.** The block below defines the inputs for the
> financial calculations; update the corresponding tables when changing them.
> The manual-effort ranges and task allocations in Part 1 are separate planning
> estimates. Their SQL-plus-prompt central values reconcile to the 40-hour input;
> the application/MILP estimate is outside this financial model.

```yaml
# ---- Darwin one-time search cost (from pages 11–12) ----
darwin_agent_model:        claude-sonnet-5
build_cost_usd:            60      # measured: ~$57 LLM + a few cents compute
token_cost_usd:            40      # estimated (page 11 reports no token table)
engineering_hours:         8       # user-selected budget across BOTH experiments
manual_engineering_hours:  40      # illustrative manual alternative, same scope

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
| Engineering effort | 8 hours total | setup, supervision, review, and result validation across both experiments |
| Manual optimization effort | 40 hours total | user-selected, unmeasured alternative covering both optimizations and validation |
| CI compute | $0.20 / vCPU-hr | for pure-compute build valuation |

### Derived unit values (auto-follow from the block above)

| Derived quantity | Formula | Value at defaults |
|---|---|---:|
| Build saving / build (dev-time) | `build_seconds_saved × developer_time_per_hr ÷ 3600` | $0.157 |
| Build saving / build (CI compute) | `build_seconds_saved × ci_compute_per_vcpu_hr ÷ 3600` | $0.00042 |
| Token saving / run (premium) | `narration_tokens_saved × narrator_premium_per_m ÷ 1e6` | $0.0179 |
| Token saving / run (budget) | `narration_tokens_saved × narrator_budget_per_m ÷ 1e6` | $0.000895 |
| Build break-even (excluding engineering) | `build_cost_usd ÷ (build saving / build)` | ≈ 382 builds |
| Token break-even (premium, excluding engineering) | `token_cost_usd ÷ (token saving / run)` | ≈ 2,235 runs |
| Engineering cost | `engineering_hours × developer_time_per_hr` | $600 |
| Combined one-time cost | `build_cost_usd + token_cost_usd + engineering cost` | $700 |
| Manual engineering cost | `manual_engineering_hours × developer_time_per_hr` | $3,000 |
| Engineering hours avoided with Darwin | `manual_engineering_hours - engineering_hours` | 32 hours |
| Net one-time cost avoided versus manual | `manual engineering cost - combined one-time cost` | $2,300 |

To re-run the whole page for your numbers: change the block, recompute the
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
**Round to ≈ $60 for API and compute, excluding engineering.** Prompt caching is doing heavy lifting here — without
it the gross 86.6 M input would have cost ~$260; caching cut the search's actual
bill by ~78%.

### Token-optimization experiment (page 11, estimated)

Page 11 does not report a token-spend table. Its winning program appears at
**iteration 8** (a shorter lineage than the build run's 60+ iterations), so its
search cost is plausibly *smaller* than the build run's ≈ $57. To stay
**conservative (over-stating cost lowers ROI)** we assume **≈ $40 for API and
compute, excluding engineering**.

### Engineering effort and combined investment

Allow **8 engineering hours total at $75/hour**, covering setup, launching and
supervising Darwin, reviewing the generated changes, checking benchmark results,
and validating correctness. This is a user-selected effort budget, not a measured
timesheet or Darwin's unattended elapsed runtime.

| Component | Calculation | One-time cost |
|---|---|---:|
| Warehouse-build search (API + compute) | `build_cost_usd` | $60 |
| Token-optimization search (API + compute) | `token_cost_usd` | $40 |
| Engineering across both experiments | `engineering_hours × developer_time_per_hr` | $600 |
| **Combined investment** | `$60 + $40 + $600` | **$700** |

Engineering is **85.7% of the combined investment**. No split of the eight hours
between experiments has been specified, so engineering-inclusive ROI is calculated
for the two experiments together rather than assigning arbitrary per-experiment
costs. Any future reruns, maintenance, or additional validation require extra budget.

### Manual optimization versus Darwin-assisted optimization

For comparison, assume **40 engineering hours at $75/hour** to perform both
optimizations manually: profile the SQL build and narration payload, investigate
alternatives, implement changes, benchmark them, review the code, and validate
correctness. Compare that with the **8 engineering hours** budgeted for Darwin
setup, supervision, review, and validation.

**Both effort figures are user-selected planning assumptions, not measured
timesheets or an industry benchmark.** The comparison assumes the manual approach
reaches equivalent performance and correctness outcomes; that outcome has not been
demonstrated in a separate manual experiment.

| Cost / effort | Manual optimization | Darwin-assisted optimization | Reduction with Darwin |
|---|---:|---:|---:|
| Engineering hours across both optimizations | 40 hr | 8 hr | **32 hr (80%)** |
| Engineering cost at $75/hr | $3,000 | $600 | **$2,400 (80%)** |
| Search API + compute included in this comparison | Not budgeted | $100 | $100 additional Darwin expense |
| **Compared one-time cost** | **$3,000 engineering only** | **$700 engineering + search** | **$2,300 (76.7%)** |

Manual tooling and benchmark-compute costs are not estimated or included; this
does not mean they are free. The comparison includes Darwin's search expense
without assigning an unsupported extra cost to the manual alternative.

```text
manual engineering cost = manual_engineering_hours × developer_time_per_hr
engineering cost avoided = (manual_engineering_hours - engineering_hours) × developer_time_per_hr
net cost avoided = manual engineering cost - (engineering_hours × developer_time_per_hr
                                           + build_cost_usd + token_cost_usd)
                = $3,000 - $700 = $2,300
cost reduction = $2,300 / $3,000 = 76.7%
```

Under these assumptions, Darwin releases **32 engineering hours** for other work
and costs **$2,300 less** after its API/compute spend. This is an opportunity-cost
comparison, not necessarily a payroll reduction or a 32-hour improvement in
calendar delivery time: unattended search runtime is separate from engineering
effort.

The cost-parity threshold is **$700 / $75 = 9.33 manual engineering hours**
(9 hours 20 minutes), excluding manual non-labor expenses. With Darwin's budget
held fixed, a manual solution taking less than that would be cheaper on this
basis; one taking more would be more expensive.

**Keep the comparison baselines separate:** the $2,300 is a **one-time cost
avoided versus manual optimization**, whereas Parts 2–4 measure **recurring
runtime benefits versus leaving the code unoptimized**. If both methods produce
equivalent optimized code, both earn those recurring benefits. Do not add the
$2,300 to Part 4's annual savings or treat it as a saving on every optimizer run.

### Illustrative engineering effort by optimization area

**These are estimates, not measurements.** The experiment reports measure code
performance or optimization outcomes, not human working hours. The figures below
are bottom-up budgets for independently **discovering, implementing, testing and
validating comparable refinements without Darwin**. They do not estimate the
much smaller task of copying Darwin's already-known solution.

#### Scope and assumptions

- One **engineer-day means eight hours of active human work**, not a calendar day
  of elapsed delivery time.
- An experienced engineer is familiar with the application and the relevant
  technology: DuckDB/SQL, Python and LLM payloads, or operations research/MILP.
- The existing model, dataset, runnable application and evaluation tooling are
  available; no greenfield application or benchmark platform is being built.
- Discovery includes investigating unsuccessful candidates and reviewing results.
  Darwin's iteration/evaluation counts are **not converted into human hours**.
- Estimates exclude major data remediation, learning the technology from scratch,
  production rollout, unattended compute time, and future maintenance.
- Equivalent outcomes are a comparison assumption, not a guarantee that manual
  work within these budgets would reproduce the exact measured improvements.
- Ranges reflect planning uncertainty; they are not statistical confidence
  intervals or industry-standard benchmarks.

#### Recommended manual-effort figures

| Optimization area | Documented outcome | Manual effort without Darwin | Central planning value |
|---|---|---:|---:|
| **SQL warehouse build** | 11.108 s → 3.582 s; **67.8% lower build time / 3.10× speedup**; result-equivalence checks passed | **24–32 hours / 3–4 engineer-days** | **28 hours / 3.5 days** |
| **Prompt-payload optimization** | 6,774 → 806 narration input tokens; **88.1% fewer tokens**; deterministic production outputs unchanged | **8–16 hours / 1–2 engineer-days** | **12 hours / 1.5 days** |
| **SQL + prompt subtotal** | Scope of this page's financial ROI model | **32–48 hours / 4–6 engineer-days** | **40 hours / 5 days** |
| **Application/MILP optimization** | **Approximately +0.19% optimized gross margin**, with evaluated feasibility checks passed | **24–40 hours / 3–5 engineer-days** | **32 hours / 4 days** |

The subtotal adds the two scoped work estimates without assuming an additional
shared setup task. The **28-hour SQL / 12-hour prompt split is a new illustrative
allocation** of the existing 40-hour manual budget, not recovered time-tracking
data. It does not allocate the eight-hour Darwin-assisted budget.

#### SQL warehouse optimization: 24–32 hours

| Manual activity | Illustrative effort |
|---|---:|
| Reproduce the cold-build baseline; profile individual statements and identify bottlenecks | 6–8 hours |
| Develop and compare SQL/build-setting alternatives; re-profile as bottlenecks change | 10–12 hours |
| Run result-equivalence checks and repeated benchmarks; review and document the selected changes | 8–12 hours |
| **Total** | **24–32 hours** |

The [SQL experiment report](12-Darwin-Warehouse-Build-Speedup.md) documents
iterative profiling, scan/window restructuring and build-setting experiments,
followed by **10 paired cold-build measurements**. This supports allowing several
days for discovery and validation rather than estimating effort from the final
code-change size. The measured gain applies to the warehouse build, not all SQL
queries or end-to-end application latency.

#### Prompt-payload optimization: 8–16 hours

| Manual activity | Illustrative effort |
|---|---:|
| Trace payload construction, establish the token baseline and identify unnecessary content | 2–4 hours |
| Implement compact narration-only representations while preserving full reporting outputs | 3–5 hours |
| Verify token reduction and deterministic-output equivalence; review sample narratives and document changes | 3–7 hours |
| **Total** | **8–16 hours** |

The [prompt experiment report](11-Darwin-Token-Optimization.md) describes two
targeted structural changes: compacting the production plan and findings supplied
to narration while preserving full-fidelity reporting outputs. This is narrower
than warehouse performance tuning; it is not model training or a redesign of the
whole agent.

**Narrative review is budgeted as a recommended activity, not claimed as a
completed quality evaluation.** Unchanged deterministic outputs do not prove
unchanged narrative quality. A formal narrative-quality evaluation, if required,
may need additional effort beyond this sample-review allowance.

#### Application/MILP optimization: 24–40 hours

| Manual activity | Illustrative effort |
|---|---:|
| Reproduce the baseline; inspect the formulation, solver settings and objective | 4–6 hours |
| Identify candidate refinements: tighter bounds, relaxation strength, optimality gaps and solver-budget allocation | 6–10 hours |
| Implement and benchmark alternatives; investigate unsuccessful candidates | 8–14 hours |
| Validate feasibility and regression behavior; review and document the selected change | 6–10 hours |
| **Total** | **24–40 hours** |

The [MILP experiment report](13-Darwin-Optimizer-Margin-Gain.md) describes
data-derived uplift bounds and reallocation of solver time and optimality-gap
budgets. These are specialist optimization tasks, not generic API development.
Here, **"APIs/APPs" refers to the application's scenario-optimization logic**;
no separate API endpoint performance benchmark was reported.

The outcome is approximately **€3.588M → €3.595M in modeled gross margin**,
or approximately **€7K more for the evaluated production plan**. It is a relative
gross-margin improvement, **not execution-speed improvement, an increase of
0.19 percentage points in margin rate, or measured annual profit**. The evaluated
checks cover demand, capacity and the ≤15% uplift cap. This estimate does not
cover the separate planner-fulfilment experiment.

#### Reconciling effort with the existing ROI

At the existing central assumptions:

```text
SQL manual effort + prompt manual effort = 28 + 12 = 40 hours
Illustrative human effort released = 40 - 8 = 32 hours = 4 engineer-days
Illustrative human-effort reduction = (40 - 8) / 40 = 80%
```

The **eight assisted hours and 80% reduction remain planning assumptions**, not
measured results or effects validated by the external references. No per-area
Darwin-assisted effort has been recorded, so per-area days saved should not be
claimed. The MILP estimate is separate: without its search cost and assisted
human effort, neither its net engineering savings nor its ROI can be calculated.

#### External evidence and limits of applicability

The following sources support the rationale for engineering leverage and retained
human validation. **None establishes the task-specific day estimates above.**

| Reference | Relevant finding | Appropriate interpretation here |
|---|---|---|
| **[1] McKinsey** | Reports **20–50% productivity improvements** across development tasks from early AI-assisted coding adoption; distinguishes coding assistance from broader AI-native workflow redesign | Supports the potential for AI-enabled productivity, not a MILP/SQL/prompt effort benchmark. Productivity increases are not numerically interchangeable with percentage reductions in engineering hours. |
| **[2] Accenture** | Reports **roughly 60–75% reductions in delivery time** in environments where AI operates across the lifecycle; emphasizes process bottlenecks | Supports automating discovery, implementation and evaluation together. Delivery time is not human effort, so these percentages are not applied to our budgets. |
| **[3] arXiv review** | Describes mixed, context-dependent productivity evidence and the continuing importance of human verification, correctness and maintainability | Supports explicit review/validation budgets and cautious scenario-based claims, not a universal productivity multiplier. |

1. **McKinsey — [AI-native development: Rethinking software from the ground up](https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/tech-forward/ai-native-development-rethinking-software-from-the-ground-up).**
   The quantitative statement was corroborated through web-search retrieval of
   the article; direct page retrieval timed out.
2. **Accenture — [AI-native software delivery](https://www.accenture.com/en-us/blogs/cloud/ai-native-software-delivery).**
   The delivery-time passage was retrieved directly.
3. **[The Rise of AI-Native Software Engineering: Implications for Practice, Education, and the Future Workforce](https://arxiv.org/html/2606.12986v1), arXiv:2606.12986v1.**
   The introduction was retrieved directly; use this preprint as contextual
   synthesis, not independent validation of Darwin's results.

Source review date: **7 October 2026**. The bottom-up allocations are judgment-based
planning estimates informed by repository scope; they were not calculated by
applying the external percentage claims to an assumed baseline.

#### Executive-table wording

| Data Warehousing (SQL based) | Agentic Apps (Prompt based) | APIs/APPs (MILP application logic) |
|---|---|---|
| **Illustrative manual effort: 3–4 engineer-days.** Baseline profiling, iterative SQL/build tuning, result-equivalence checks and controlled benchmarking. | **Illustrative manual effort: 1–2 engineer-days.** Payload analysis, compact narration views, token measurement, regression checks and narrative review. | **Illustrative manual effort: 3–5 engineer-days.** Formulation analysis, solver tuning, comparative experiments and feasibility/regression checks targeting a comparable gross-margin improvement. |

Suggested shared footnote: *Bottom-up planning estimates, not measured savings;
assume experienced engineers, existing evaluation tooling and eight-hour
engineer-days. References [1–3] provide context, not task-specific benchmarks.
Darwin-assisted effort by area was not measured.*

---

## Part 2 — Recurring benefit per unit

### SQL warehouse execution: results ready in 3.582 s instead of 11.108 s

The primary recurring benefit is **less time waiting for the SQL warehouse build
to finish**, not just a smaller compute bill. Darwin reduced elapsed time by
**7.526 seconds per build**, or **67.8%**, giving a **3.10× speedup**.

| Measured timing | Before Darwin | After Darwin | Improvement |
|---|---:|---:|---:|
| Mean cold warehouse-build time | 11.108 s | 3.582 s | **7.526 s saved per build** |
| Relative elapsed time | 100% | 32.2% | **67.8% less waiting** |

These results come from **10 paired cold builds per version**, after a discarded
warm-up, under controlled conditions. The speedup's 95% confidence interval was
**3.08× to 3.12×**; the aggregate/fact tables passed the result-equivalence checks.
See [page 12](12-Darwin-Warehouse-Build-Speedup.md) for the benchmark and validation.

**Measurement scope:** this is the end-to-end warehouse initialization/build
benchmark, including data loading and the SQL that materializes aggregate/fact
tables. It is **not a measured 3.10× speedup for every individual SQL query**,
downstream dashboard query, or complete optimizer run. An agent run that reuses
the existing warehouse does not earn another 7.526-second build saving.

#### How the saved execution time accumulates

For `N` equivalent builds, cumulative elapsed time saved is
`N × build_seconds_saved`. At the measured timings:

| Warehouse builds | Total time before | Total time after | Cumulative time saved |
|---:|---:|---:|---:|
| 1 | 11.108 s | 3.582 s | **7.526 s** |
| 100 | 18.51 min | 5.97 min | **12.54 min** |
| 1,000 | 185.13 min | 59.70 min | **125.43 min (2.09 hr)** |
| 5,000 (annual assumption) | 925.67 min | 298.50 min | **627.17 min (10.45 hr)** |

These are sums of per-build durations, assuming comparable data, hardware, and
execution conditions. Parallel builds do not necessarily shorten calendar time
by the full sum, and unattended builds do not automatically save human work hours.

Operationally, the faster SQL build means:

- **Earlier availability of refreshed tables:** downstream analysis can start
  about 7.5 seconds sooner when it is waiting on this build.
- **Shorter development feedback loops:** a developer rebuilding after a SQL or
  data change waits about 3.6 seconds rather than 11.1 seconds for this stage.
- **Less time in the build stage of CI:** the stage finishes sooner, although the
  total pipeline improves only to the extent that this stage is on its critical path.

#### Financial value alongside the time saving

The elapsed-time improvement is measured; the dollar amounts below are
**illustrative valuations**, not observed billing reductions.

| Valuation basis | Rate | Before / build | After / build | Saving / build |
|---|---|---:|---:|---:|
| Developer wait-time value | $75 / hr | $0.2314 | $0.0746 | **$0.1568** |
| Compute estimate (one billed vCPU for the build duration) | $0.20 / vCPU-hr | $0.000617 | $0.000199 | **$0.000418** |

At **5,000 builds per year**, the same **10.45 hours of cumulative execution time
saved** represents either approximately **$783.96 of developer-time value** or
**$2.09 of compute savings** under these assumptions. Use developer-time value
only when a person is actually blocked and can use the released time productively;
use compute valuation for unattended builds. These are alternative ROI bases here,
not amounts to add together for the same build.

Actual infrastructure savings depend on billed resources, billing granularity,
and whether the shorter build reduces paid usage. A fixed-price, always-on machine
may finish sooner without lowering its bill. **The main demonstrated gain is
faster SQL warehouse execution; cash savings depend on how it is operated.**

### Token narration: 5,968 input tokens saved per agent run

| Narration model | Input rate | Saving per run |
|---|---|---:|
| Premium (GPT-4o / Sonnet-class) | $3.00 / M | **$0.0179** |
| Budget (`gpt-4o-mini`) | $0.15 / M | $0.000895 |

Plus a **latency** benefit: ~6 k fewer prompt tokens removes roughly 0.1–0.5 s of
prefill per narration (model-dependent), improving dashboard responsiveness.

### Budget versus premium: what actually changes

These tiers describe the **LLM that writes the executive summary**, not different
optimization engines or different versions of Darwin. The agent has two stages:

1. A deterministic optimization engine calculates the production schedule,
   findings, and KPIs.
2. The narrator LLM turns those already-computed results into a business-language
   summary.

Changing the narrator affects the second stage only. A more expensive narrator
does **not automatically produce a better production schedule**.

| Comparison | Budget narrator | Premium narrator |
|---|---|---|
| Role | Explain the computed results | Explain the same computed results |
| Assumed input price | $0.15 / million tokens | $3.00 / million tokens |
| Relative input price | 1× | 20× |
| Potential advantage | Lower narration cost | Potentially better explanations and instruction-following |
| Production plan | Same deterministic calculation | Same deterministic calculation |

The model names above are examples of pricing tiers, **not verified current
quotes**. Any premium narration-quality advantage must be evaluated; this
experiment measures token reduction, not a quality comparison between models.
These narrator rates are separate from the model and rates used for Darwin's
one-time search.

### Narration input cost before and after Darwin

The measured input shrank from **6,774 to 806 tokens per run** (see
[page 11](11-Darwin-Token-Optimization.md)). Each cost below is
`input tokens × narrator input rate / 1e6`; annual savings use the assumed
`agent_runs_per_year = 10,000`.

| Narration input cost | Budget | Premium |
|---|---:|---:|
| Before Darwin, per run | $0.0010161 | $0.020322 |
| After Darwin, per run | $0.0001209 | $0.002418 |
| Saving per run | $0.0008952 | $0.017904 |
| Saving over 10,000 runs | **$8.95** | **$179.04** |

Both tiers achieve the **same 88.1% input-token reduction**, but premium saves
**20× more dollars** because each removed token costs 20× more. These are
**narration input costs only**, not full end-to-end run costs: generated output
tokens, optimizer compute, and hosting are excluded.

### Why engineering changes the comparison

The combined investment remains **$700 in either scenario**: $600 for eight
engineering hours plus approximately $100 for both Darwin searches. At 10,000
agent runs, narration input savings alone recover only **$8.95 (budget)** or
**$179.04 (premium)** of that investment.

The positive first-year economic ROI in Part 4 also includes **$783.96 of saved
developer wait time across 5,000 warehouse builds**. That benefit is the same
for both narrator tiers and is the largest contributor. It should only be counted
as developer-time value when those saved seconds release useful engineering time.

**Decision rule:** budget is cheaper to operate, while premium makes token
reduction more financially valuable but remains more expensive per run after
optimization. Choose premium for demonstrated narration-quality needs, **not to
make Darwin's ROI look better**.

---

## Part 3 — Break-even (how many runs amortize Darwin)

The per-experiment table below **excludes engineering**. It isolates API and
compute payback; use the combined analysis in Part 4 for the $700 investment.

$$\text{break-even units} = \frac{\text{one-time Darwin cost}}{\text{saving per unit}}$$

| Optimization | One-time cost | Saving/unit | Break-even |
|---|---:|---:|---:|
| Build (developer-time) | $60 | $0.157 | **≈ 382 builds** |
| Build (CI compute only) | $60 | $0.00042 | ≈ 143,000 builds |
| Tokens (premium model) | $40 | $0.0179 | **≈ 2,235 runs** |
| Tokens (budget model) | $40 | $0.000895 | ≈ 44,700 runs |

Read this as: excluding engineering, on developer-time value, the **build speedup pays for itself in
~382 rebuilds** — often a week or two of active development. Token payback depends
heavily on the narration model: a **premium narrator pays back in ~2,200 runs**; a
cheap one needs high volume.

---

## Part 4 — ROI at representative volumes (year 1)

$$\text{ROI} = \frac{\text{annual benefit} - \text{one-time cost}}{\text{one-time cost}}$$

The next three per-experiment tables **exclude engineering**. The combined
engineering-inclusive analysis follows them.

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
year-1 figures above, provided no further engineering or search work is needed.

### Combined ROI including engineering

At the assumed **5,000 warehouse builds and 10,000 agent runs per year**:

```text
annual build benefit = builds_per_year × build_seconds_saved × developer_time_per_hr / 3600
annual token benefit = agent_runs_per_year × narration_tokens_saved × narrator_rate / 1e6
annual benefit = annual build benefit + annual token benefit
net benefit = annual benefit - combined one-time cost
ROI = net benefit / combined one-time cost
payback years = combined one-time cost / annual benefit
```

Using unrounded unit savings:

| Narrator tier | Annual build benefit (dev-time) | Annual token benefit | Combined investment | Net benefit (yr 1) | ROI (yr 1) | Payback at steady usage |
|---|---:|---:|---:|---:|---:|---:|
| Premium | $783.96 | $179.04 | $700 | **+$263.00** | **+37.6%** | **8.7 months** |
| Budget | $783.96 | $8.95 | $700 | **+$92.91** | **+13.3%** | **10.6 months** |

This is **economic ROI, not necessarily a reduction in cash spending**: the build
benefit assumes every saved second releases useful engineering time. For unattended
CI builds, use compute valuation instead, not both valuations for the same build.
With all 5,000 builds valued only at the assumed one-vCPU compute rate, annual
combined savings are just **$181.13 (premium)** or **$11.04 (budget)**; neither
recovers the $700 investment in year 1.

### Allocating the investment per optimizer run

The investment does not change the **pre-Darwin running cost**. To express it per
run, choose an amortization volume. Allocating the entire combined investment over
the assumed first year's **10,000 agent runs** gives:

| Cost allocation | Formula | Cost per agent run |
|---|---|---:|
| Engineering | `$600 / 10,000` | $0.060 |
| Darwin API + compute | `($60 + $40) / 10,000` | $0.010 |
| **Combined one-time investment allocation** | `$700 / 10,000` | **$0.070** |

Thus engineering adds **6 cents per run**, and the total Darwin investment adds
**7 cents per run**, over that amortization volume. For any other volume `N`, use
`$700 / N`. This allocates both experiments to agent runs for accounting purposes;
it does not imply that a warehouse rebuild occurs on every agent run. It is an
allocation, not a recurring API charge, and is additional to post-Darwin narration
input/output, optimizer compute, and hosting costs. It must not also be charged
to warehouse builds.

---

## Part 5 — Sensitivity: what moves the ROI

- **Run/build volume** — the dominant lever. Both optimizations are one-time
  costs amortized over unlimited future units; ROI scales linearly with volume.
- **Narration model price** — a 20× swing ($0.15 → $3.00 per M) moves token ROI by
  the same 20×. High-value narration models make the token win pay back fastest.
- **How you value build time** — pure CI compute makes the build speedup marginal;
  developer wall-clock time (the honest basis for an inner-loop build) makes it
  strongly positive.
- **Engineering effort** — at eight hours, labor contributes $600 of the $700
  investment. Every additional hour adds $75 and extends payback.
- **Manual alternative** — the 40-hour estimate drives the illustrative $2,300
  one-time cost advantage. Each hour less manual effort reduces that advantage
  by $75; this comparison does not change recurring runtime savings.
- **Darwin API cost** — prompt caching lowers search spend, but engineering
  dominates the combined investment at these assumptions.

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
- **Engineer time saved** — the search is autonomous, but setup, review, and
  validation are not free: the investment includes eight hours of engineering.
  Against the illustrative 40-hour manual alternative in Part 1, Darwin avoids
  **32 engineering hours**. This is a planning estimate, not a measured
  manual-versus-Darwin productivity result.

---

## Bottom line

| | Warehouse build (SQL) | Token narration |
|---|---|---|
| Measured improvement | **3.10× faster** (−7.526 s/build) | **−88.1%** (−5,968 tokens/run) |
| One-time API + compute cost (excluding engineering) | ≈ $60 | ≈ $40 (est.) |
| Saving per unit | $0.157 (dev-time) | $0.0179 (premium) / $0.0009 (budget) |
| Break-even (excluding engineering) | ≈ **382 builds** | ≈ **2,235** (premium) / 44,700 (budget) runs |
| Best ROI driver | developer/CI feedback speed | high run volume + premium narrator |

**Conclusion.** Including **8 engineering hours ($600)** brings the combined
one-time investment to **$700**, not just $100 of API and compute spend. At
5,000 builds and 10,000 agent runs per year, valuing build waits as productive
developer time gives **+37.6% first-year ROI with a premium narrator** or
**+13.3% with a budget narrator**. Payback is approximately **8.7 or 10.6 months**,
respectively. Allocating the investment across those 10,000 agent runs adds
**$0.07 per run**. Positive first-year ROI depends on realizing the developer-time
benefit; compute and token savings alone do not cover the investment at this volume.

**Versus manual optimization:** at the assumed **40 manual engineering hours**,
the alternative costs **$3,000 in labor**, compared with Darwin's **$700 including
labor and search**. That is **32 engineering hours avoided** and an illustrative
**$2,300 lower one-time cost (76.7%)**, assuming equivalent validated results.
This is separate from the recurring ROI above and depends on the unmeasured
manual-effort estimate.
