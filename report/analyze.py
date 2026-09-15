#!/usr/bin/env python3
"""Track A report: stats (bootstrap CI, Welch t-test, Cohen's d), plots
(iteration-vs-score, cumulative tokens), and the idea->improvement table."""
import json, random, statistics, math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "wh_report_data.json").read_text())

base = D["noise"]["baseline"]; champ = D["noise"]["champion"]
nb, nc = len(base), len(champ)
bm, cm = statistics.mean(base), statistics.mean(champ)
bsd, csd = statistics.stdev(base), statistics.stdev(champ)
speedup = bm / cm

# bootstrap 95% CI for the speedup ratio
random.seed(0)
boot = []
for _ in range(20000):
    b = statistics.mean(random.choice(base) for _ in range(nb))
    c = statistics.mean(random.choice(champ) for _ in range(nc))
    boot.append(b / c)
boot.sort()
ci_lo, ci_hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]

# Welch's t-test (baseline vs champion build times)
se = math.sqrt(bsd**2 / nb + csd**2 / nc)
t = (bm - cm) / se
df = se**4 / ((bsd**2 / nb)**2 / (nb - 1) + (csd**2 / nc)**2 / (nc - 1))
# pooled SD for Cohen's d
psd = math.sqrt(((nb - 1) * bsd**2 + (nc - 1) * csd**2) / (nb + nc - 2))
cohend = (bm - cm) / psd
try:
    from scipy import stats as sst
    p = 2 * sst.t.sf(abs(t), df)
    pstr = f"{p:.2e}"
except Exception:
    pstr = "< 1e-12 (|t| huge)"

print("=== NOISE / SIGNIFICANCE ===")
print(f"baseline  n={nb} mean={bm:.3f}s sd={bsd:.3f} cv={bsd/bm*100:.2f}%")
print(f"champion  n={nc} mean={cm:.3f}s sd={csd:.3f} cv={csd/cm*100:.2f}%")
print(f"speedup   {speedup:.3f}x  95% CI [{ci_lo:.3f}, {ci_hi:.3f}]")
print(f"Welch t={t:.1f} df={df:.1f} p={pstr}  Cohen_d={cohend:.1f}")

# ---- Plot 1: iteration vs score ----
traj = sorted([p for p in D["trajectory"] if p["combined"] is not None], key=lambda p: p["iter"])
xs = [p["iter"] for p in traj]; ys = [p["combined"] for p in traj]
run = []; best = -1
for y in ys:
    best = max(best, y); run.append(best)
champ_iter = max(traj, key=lambda p: (p["combined"] if p["build_s"] else 0))
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.axhline(1.0, ls=":", c="gray", lw=1, label="baseline (1.0x)")
ax.scatter(xs, ys, s=26, c="#4C78A8", alpha=0.75, label="candidate speedup")
ax.plot(xs, run, c="#E45756", lw=2, label="best-so-far")
ax.scatter([40], [next(p["combined"] for p in traj if p["iter"] == 40)], s=140,
           marker="*", c="#F58518", edgecolor="k", zorder=5, label="champion (iter 40)")
ax.axvline(45.5, ls="--", c="#888", lw=1)
ax.text(46, ax.get_ylim()[0] + 0.1, "resume (+30 iters)", fontsize=8, color="#555")
ax.set_xlabel("iteration"); ax.set_ylabel("build speedup vs baseline (x)")
ax.set_title("Track A: warehouse-build speedup by iteration")
ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(HERE / "iteration_vs_score.png", dpi=130); plt.close(fig)

# ---- Plot 2: cumulative tokens ----
ags = [a for a in D["agents"] if a["start"]]
ags.sort(key=lambda a: a["start"])
cin = cout = cr = cw = 0; xi = []; tot = []; ins = []; outs = []
for i, a in enumerate(ags, 1):
    cin += a["in"]; cout += a["out"]; cr += a["cache_read"]; cw += a["cache_write"]
    xi.append(i); tot.append((cin + cout) / 1e6); ins.append(cin / 1e6); outs.append(cout / 1e6)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(xi, ins, c="#4C78A8", lw=2, label=f"input (cum {cin/1e6:.1f}M)")
ax.plot(xi, outs, c="#54A24B", lw=2, label=f"output (cum {cout/1e6:.2f}M)")
ax.plot(xi, tot, c="#E45756", lw=2.4, label=f"input+output (cum {(cin+cout)/1e6:.1f}M)")
ax.set_xlabel("agent invocation (evaluation)"); ax.set_ylabel("cumulative tokens (millions)")
ax.set_title("Track A: cumulative LLM tokens spent")
ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(HERE / "tokens_spent.png", dpi=130); plt.close(fig)
print(f"\ntotals: input={cin/1e6:.2f}M output={cout/1e6:.3f}M cache_read={cr/1e6:.1f}M cache_write={cw/1e6:.1f}M over {len(ags)} agents")

# ---- ideas that led to improvement ----
imps = sorted(D["improvements"], key=lambda r: -r["delta"])
print("\n=== IMPROVEMENT EVENTS (idea -> delta) ===")
for r in imps[:14]:
    idt = (r["idea"] or "").replace("\n", " ")
    print(f"iter {r['iter']:>2}  +{r['delta']:.3f} ({r['from']}->{r['to']})  idea#{r['idea_id']}: {idt[:120]}")
print(f"\n(total improvement events: {len(imps)})")
