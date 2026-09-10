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
