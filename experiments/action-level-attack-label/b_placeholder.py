"""B — placeholder control (TASK.md §B). Cached-score distribution, placeholder vs not, per side.

Groups from g2_prep per_action: honest-placeholder, honest-non, attack-placeholder, attack-non.
For each pair: mean cached_mean, p(cached_mean >= 6), p(both monitor scores >= 6), Mann-Whitney U
(stdlib normal approximation with tie correction, two-sided). Raw carries the full cached_mean
array per group so every number recomputes without the model.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import math
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLUG = HERE.name
REPO = HERE.parents[1]
EXPORT = REPO / "checkpoints" / "local-monitor-activations" / "data" / "export"
G2 = REPO / "results" / "raw" / "local-monitor-activations" / "g2_prep_20260910T103431Z.json"
RAW_DIR = REPO / "results" / "raw" / SLUG
FIG_DIR = REPO / "results" / "figures" / SLUG
TS = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def mannwhitney(x, y):
    """Two-sided Mann-Whitney U, normal approximation, tie-corrected. Returns U1, z, p, AUC."""
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks, i, n = {}, 0, len(allv)
    tie_term = 0.0
    while i < n:
        j = i
        while j < n and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks.setdefault(k, r)
        t = j - i; tie_term += t ** 3 - t
        i = j
    r1 = sum(ranks[k] for k in range(n) if allv[k][1] == 0)
    n1, n2 = len(x), len(y)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    sigma = math.sqrt(n1 * n2 / 12.0 * ((n + 1) - tie_term / (n * (n - 1))))
    z = (u1 - mu) / sigma if sigma > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    return u1, z, p, u1 / (n1 * n2)


def main():
    g2 = json.load(open(G2))["per_action"]
    both = {}
    for fn in ("attack.jsonl", "honest.jsonl"):
        with open(EXPORT / fn) as f:
            for line in f:
                if line.strip():
                    a = json.loads(line); ms = a["monitor_scores"]
                    both[(a["traj_id"], a["action_idx"])] = (all(v >= 6 for v in ms)) if len(ms) == 2 else None
    groups = collections.defaultdict(list)
    for tid, idx, side, ph, cm in zip(g2["traj_id"], g2["action_idx"], g2["side"], g2["placeholder"], g2["cached_mean"]):
        groups[(side, "placeholder" if ph else "non_placeholder")].append((cm, both[(tid, idx)]))

    def stats(vals):
        cm = [v for v, _ in vals]; b2 = [b for _, b in vals if b is not None]
        return {"n": len(cm), "mean": sum(cm) / len(cm), "median": sorted(cm)[len(cm) // 2],
                "p_cached_mean_ge6": sum(v >= 6 for v in cm) / len(cm),
                "p_both_ge6": (sum(b2) / len(b2)) if b2 else None, "n_two_scores": len(b2),
                "hist": dict(sorted(collections.Counter(str(v) for v in cm).items(), key=lambda kv: float(kv[0])))}

    out = {"slug": SLUG, "script": f"experiments/{SLUG}/b_placeholder.py", "timestamp": TS,
           "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
           "g2_prep": str(G2.relative_to(REPO)), "groups": {}, "tests": {}, "cached_mean_arrays": {}}
    for side in ("honest", "attack"):
        for g in ("placeholder", "non_placeholder"):
            out["groups"][f"{side}_{g}"] = stats(groups[(side, g)])
            out["cached_mean_arrays"][f"{side}_{g}"] = [v for v, _ in groups[(side, g)]]
        x = [v for v, _ in groups[(side, "placeholder")]]; y = [v for v, _ in groups[(side, "non_placeholder")]]
        u, z, p, auc = mannwhitney(x, y)
        out["tests"][f"{side}_placeholder_vs_non"] = {"U1_placeholder": u, "z": z, "p_two_sided": p, "auc_placeholder_gt_non": auc,
                                                      "mean_diff_placeholder_minus_non": out["groups"][f"{side}_placeholder"]["mean"] - out["groups"][f"{side}_non_placeholder"]["mean"]}
    fig = None
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig_, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
        for ax, side in zip(axes, ("honest", "attack")):
            for g, c in (("non_placeholder", "#888"), ("placeholder", "#c44")):
                v = out["cached_mean_arrays"][f"{side}_{g}"]
                ax.hist(v, bins=[i / 2 for i in range(0, 22)], density=True, alpha=0.6, color=c, label=f"{g} (n={len(v)})")
            ax.set_title(f"{side}: cached_mean"); ax.legend(fontsize=7)
        FIG_DIR.mkdir(parents=True, exist_ok=True); fig = FIG_DIR / "b_placeholder_cached_hist.png"; fig_.tight_layout(); fig_.savefig(fig, dpi=150)
        out["figure"] = str(fig.relative_to(REPO))
    except ImportError as e:
        out["figure"] = None; print("!! no matplotlib:", e)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rp = RAW_DIR / f"b_placeholder_{TS}.json"; rp.write_text(json.dumps(out, separators=(",", ":")))
    print("raw ->", rp.relative_to(REPO), f"({rp.stat().st_size/1e6:.2f} MB)", "figure ->", out["figure"])
    for k, v in out["groups"].items():
        print(f"{k:24} n={v['n']:6} mean={v['mean']:.3f} median={v['median']} p(mean>=6)={v['p_cached_mean_ge6']:.4f} p(both>=6)={v['p_both_ge6']:.4f} (n2={v['n_two_scores']})")
    for k, v in out["tests"].items():
        print(f"{k:30} U1={v['U1_placeholder']:.0f} z={v['z']:.2f} p={v['p_two_sided']:.2e} AUC(ph>non)={v['auc_placeholder_gt_non']:.3f} mean diff={v['mean_diff_placeholder_minus_non']:+.3f}")


if __name__ == "__main__":
    main()
