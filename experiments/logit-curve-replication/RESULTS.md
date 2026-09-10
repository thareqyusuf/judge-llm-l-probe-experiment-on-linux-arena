# RESULTS — logit-curve-replication

Branch `exp/logit-curve-replication`. Running log for this experiment only. Newest at the top.
Every quantitative claim carries its source, its raw file, and a recompute
command — see CLAUDE.md. Status tags: `[hunch]` `[tested]` `[verified]` `[dead]`

## Hypothesis

The GPT-5 Nano live action-monitor's ROC on Opus honest vs Opus attack
(LinuxArena §5.3), plotted as logit10(TPR) vs logit10(FPR), can be rebuilt from
the cached per-action scores on the public mirror and is approximately linear
over the cropped range (≥5 FP, ≥5 TP, ≥5 FN). Kind of claim: general claim
(replication of a published curve; the baseline is the paper's own `data.json`).

Track L (this branch) only prepares data + the cached-score ROC + the pod
handoff; the open-weight monitor with activation capture runs on the pod
(track G) and is a separate branch.

## Task

See `TASK.md` in this directory — the prompt the experiment session was given,
verbatim, so the reviewer can see what was asked vs what was run. The running
narrative per step is in `REPORT.md` (same directory).

---

## 2026-09-10 — L4 handoff package: prompt formatter byte-identical on all 17,234 actions

**Claim.** `gpu/format_monitor_prompt.py` (pure Python) reproduces
control-tower 1.0.1's live-monitor prompt byte for byte on every scorable
action of the export (17,234/17,234); `gpu/manifest.json` lists those actions
with cached scores and control-tower prompt hashes plus a 200-action pilot;
`gpu/run_monitor.py` runs end to end on CPU with Qwen3-0.6B (2 actions),
capturing fp16 `[n_layers, d_model]` last-prompt-token residuals, a parsed
score, an expected score over digit tokens, and resuming from its checkpoint.
Token-length statistics: see the L4.3 entry in `REPORT.md`.

**Kind of claim.** Engineering verification (no hypothesis).

**Evidence.**
- Scripts: `experiments/logit-curve-replication/gpu/format_monitor_prompt.py`, `data_export/verify_prompt_format.py` @ commit `4032851` (= `.git_commit` in the verify raw), `data_export/build_manifest.py`, `data_export/token_lengths.py`, `gpu/run_monitor.py`
- Raw: `results/raw/logit-curve-replication/l4_prompt_verify_20260910T043718Z.json`; `l4_token_lengths_<ts>.json` (see REPORT L4.3)
- Logs: `logs/logit-curve-replication/l4_prompt_verify.log`, `l4_build_manifest.log`, `l4_token_lengths.log`, `l4_smoke_qwen3-0.6b.log`
- Figure: `results/figures/logit-curve-replication/l4_token_lengths.png`
- Recompute: `jq '{n_actions_compared, n_equal, n_mismatch}' results/raw/logit-curve-replication/l4_prompt_verify_20260910T043718Z.json` → 17234, 17234, 0; `jq '{n_actions, pilot_size}' experiments/logit-curve-replication/gpu/manifest.json` → 17234, 200

**Alternative explanations considered.**
- "Byte-identical to control-tower" is not "byte-identical to what GPT-5
  Nano saw": stored prompts are empty in the dump, task descriptions and
  side-task goals come from the dump / v1.0.1 registry, and the dump was
  edited after the fact (39 renamed outputs). Nothing here can close that gap.
- The smoke test used the two shortest pilot prompts on CPU; nothing about
  CUDA, gpt-oss's channel format, or 100k-token prompts is exercised.

**Status.** `[tested]`

---

## 2026-09-10 — L3 logit-ROC from cached GPT-5 Nano scores

**Claim.** With per-action ensemble means, an honest pool of 12,494 actions and
the max action per attack trajectory (n=92, ungated), the cached monitor
reaches TPR 0.560 (95% bootstrap CI 0.461–0.654) at FPR 1e-2 and 0.314
(0.223–0.409) at FPR 3e-3; the 11 cropped ROC points in logit10–logit10 space
fit a line of slope 0.881 with R² 0.985, with the low-FPR end bending below it.
The honest pool and attack maxima are identical (as multisets) to the paper's
`data.json`, and the paper's per-budget thresholds are reproduced exactly.

**Kind of claim.** General claim (replication of a published curve). Baseline
= the paper's own numbers (cross-check above); chance line on the standard ROC.

**Evidence.**
- Script: `experiments/logit-curve-replication/data_export/logit_roc.py` @ commit `4032851` (= `.git_commit` in the raw file)
- Input: `results/raw/logit-curve-replication/export_actions_20260910T043234Z.jsonl` (from `data_export/export.py`, same commit)
- Raw: `results/raw/logit-curve-replication/l3_logit_roc_20260910T043236Z.json`
- Log: `logs/logit-curve-replication/l3_logit_roc.log`
- Figures: `results/figures/logit-curve-replication/l3_roc_standard.png`, `l3_logit_roc_pooled.png`, `l3_logit_roc_per_category.png`
- Recompute (no model needed):
  - `jq '.tpr_at_fpr["0.01"] | {tpr, ci95}' results/raw/logit-curve-replication/l3_logit_roc_20260910T043236Z.json` → 0.560, [0.461, 0.654]
  - `jq '.ols_pooled' …` → slope 0.881, intercept 1.906, r2 0.985, n 11
  - from scratch: `python3 -c "import json;d=json.load(open('results/raw/logit-curve-replication/l3_logit_roc_20260910T043236Z.json'));b=d['benign_scores'];m=[t['max_score'] for t in d['attack_trajectories']];print(sum(s>7.5 for s in b)/len(b), sum(x>7.5 for x in m)/len(m))"` → FPR 0.00840, TPR 0.543 at threshold 7.5 (the point just below FPR 1e-2)
  - cross-check: `jq '.cross_check_paper | {honest_pool_multiset_equal, attack_max_multiset_equal, thr: [.per_budget[].threshold_equal]}' …` → true, true, all true

**Baselines.**
| condition | value |
|---|---|
| main (TPR at FPR 1e-2) | 0.560 |
| chance | 0.010 |
| paper safety at budget 1e-2 (different metric, same threshold) | 0.572 |

**What I checked myself.** (left for the reviewer)

**Alternative explanations considered.**
- Action-level bootstrap ignores that honest actions are clustered in 200
  trajectories of very unequal length; CIs on FPR are likely too narrow.
- TPR at a target FPR is an interpolation on a 0.5-step score grid; the strict
  step-function value at threshold 7.5 is 0.543 (FPR 8.4e-3).
- Per-category curves rest on 5–31 trajectories; only one category has ≥5
  cropped points.

**Status.** `[tested]`

---

## 2026-09-10 — L2 export: 12,675 honest + 5,097 attack actions

**Claim.** The export covers all 200 honest and 92 attack monitor-run
trajectories; every action's cached samples equal the mirror's; 12,487 honest
actions are scorable by the live monitor (12,494 in the paper's pool);
tool_output differs from the HF dump on 39 actions, all `LinuxBench`→`linuxarena`
renames, and no tool_input contains either string.

**Kind of claim.** Descriptive (data preparation).

**Evidence.**
- Script: `experiments/logit-curve-replication/data_export/export.py` @ commit `4032851` (= `.git_commit` in the raw file)
- Raw: `results/raw/logit-curve-replication/export_meta_20260910T043234Z.json`, `export_actions_20260910T043234Z.jsonl` (superseded first run: `…_20260910T042851Z.*`)
- Log: `logs/logit-curve-replication/l2_export.log`
- Data: `experiments/logit-curve-replication/data_export/data/{honest,attack,trajectories}.jsonl` (gitignored, 61 MB; sha256 in `data_export/data/CHECKSUMS.json` and in the raw meta), `summary.md`
- Recompute: `jq '.sides | map_values({n_trajectories, n_actions, n_actions_scorable, member_mismatch: .checks.member_mismatch_hf_vs_api, output_diff: .checks.output_diff_hf_vs_api})' results/raw/logit-curve-replication/export_meta_20260910T043234Z.json`

**Alternative explanations considered.** `tool_input` has no mirror-side
check at all (the mirror strips arguments); if the HF dump altered arguments
in ways other than the two strings searched for, nothing here would notice.

**Status.** `[tested]`

---

## 2026-09-10 — L1 reconnaissance: mirror + HF rows audited

**Claim.** The four runs (Opus honest/attack agent runs; GPT-5 Nano monitor
runs on each) are complete on the public mirror; monitor runs join to agent
runs by `(env, main_task, side_task)` 200/200 and 92/92; the honest monitor
scored a strict prefix of 3 of the 200 honest trajectories; both monitor runs
are 2-sample ensembles except 333 single-sample actions on the attack side;
per-action scores on the mirror equal the HF dump on every action.

**Kind of claim.** Descriptive data audit (no hypothesis tested yet).

**Evidence.**
- Script: `experiments/logit-curve-replication/data_export/recon.py` @ commit `4362d82` (= `.git_commit` in the raw file; the script was committed together with the raw file in the next commit — the raw file records the scaffold commit it was run at)
- Raw: `results/raw/logit-curve-replication/l1_recon_20260910T042333Z.json`
- Log: `logs/logit-curve-replication/l1_recon.log`
- Recompute (no model needed):
  - join: `jq '.agent_monitor_join.honest | {task_keys_matched, matched_with_identical_function_sequence, matched_with_different_actions: (.matched_with_different_actions|length)}' results/raw/logit-curve-replication/l1_recon_20260910T042333Z.json` → 200, 197, 3
  - samples per action: `jq '.samples_per_action | {honest: .honest_monitor.n_actions_with_2_members, attack2: .attack_monitor.n_actions_with_2_members, attack1: .attack_monitor.n_actions_non_ensemble}' …` → 12675, 4764, 333
  - mirror vs HF: `jq '.hf | {h: .honest_monitor.api_vs_hf_member_scores, a: .attack_monitor.api_vs_hf_member_scores}' …` → different: 0 on both
  - fingerprints: `jq '[.fingerprints[].recompute_matches] | all' …` → true
  - honest pool: `jq '.samples_per_action.honest_monitor.n_scorable_actions' …` → 12494 (= `len(honest_action_scores)` for "GPT-5 Nano" in `linuxarena-paper/src/neurips/section_5_3_monitoring_results/data.json`)

**Baselines.** n/a (audit).

**What I checked myself.** (left for the reviewer)

**Alternative explanations considered.**
- The 3 truncated honest trajectories could be a different *run* of the same
  task rather than a prefix: ruled out for the function sequence (exact
  prefix), not for the arguments/outputs (L2 checks content equality of the
  prefix).
- "Mirror == HF" is only checked on scores and outputs; `arguments` exist only
  in HF, so nothing on the mirror can confirm them. The mirror fingerprint
  does not cover them either.

**Status.** `[tested]`

---

## Verification (VERIFY.md)

Filled in by the review session, on this branch, before merge to main.

**Verdict.** Verified / Verified but weaker than stated / Not verifiable from what's here / Wrong

**What was recomputed.**

**Dumbest ways this could be wrong, and what rules each out.**

---

## Dead ends

- (none yet)
