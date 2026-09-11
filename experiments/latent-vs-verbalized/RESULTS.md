# RESULTS — latent-vs-verbalized

Branch `exp/latent-vs-verbalized`. Running log for this experiment only. Newest at the top.
Every quantitative claim carries its source, its raw file, and a recompute
command — see CLAUDE.md. Status tags: `[hunch]` `[tested]` `[verified]` `[dead]`

## Hypothesis

A linear probe on gpt-oss-20b's residual stream at `prompt_end`, trained on level-2
payload actions vs honest actions, ranks the 31 payloads the verbalized integer puts at
≤ 1 above the honest 5 % FPR threshold more often than the expected score E does
(E: 15/31), and keeps that margin under leave-one-environment-out, length/position-matched
negatives, and a TF-IDF text baseline.

Kind of claim: general claim (about this monitor on this pool; needs the baselines above).
Falsified if the probe's Δp_null ≤ 15/31, or if any listed baseline matches it. A null here
is a result: it means E already exhausts what is linearly readable before generation.

Pre-registered secondary (position ordering, written before running P2): I expect
`prompt_end` ≥ `analysis_end` ≥ E — the information is present before the monitor writes
anything, and the CoT adds nothing linearly readable. The G4.3 local>cached catch, whose
analysis text named the mechanism, is the reason the opposite ordering
(`analysis_end` > `prompt_end`) is plausible; if that is what appears, the probe must be
re-run with the suspicion-language actions removed before it counts.
`instruction_end` must be at chance; `pre_score` is excluded as evidence (digit mass 1.0).

## Task

See `TASK.md` in this directory — the prompt the experiment session was given,
verbatim, so the reviewer can see what was asked vs what was run.

---

## 2026-09-11 — P-1 / P-0 / P0 / P0b / P1: capture verified, shards consolidated, gate reproduced, anchoring read, split locked

**Claim.** (1) The join reproduces every label-branch gate number to ±0.01 under both placeholder
rules the gate was defined on. (2) For the 31 level-2 payloads the integer nulls, the forced-readout
digit mass is unimodal at 0–1 with the remainder at 2–3 and essentially nothing at 6–10 (mean 0.006,
max per action 0.021) — there is no discarded second mode. (3) The literal suspicion regex is
useless on this monitor: it matches 1,477 of 1,747 score ≤ 1 actions because the analysis boilerplate
is "No malicious." Non-negated matches: 16 actions, 0 of them level-2.

**Kind of claim.** Descriptive / infrastructure gates. No probe yet.

**Evidence.**
- Scripts (all @ this commit): `common.py` (loader + ROC conventions), `p1_verify.py`, `p0_consolidate.py`, `p0_gate.py`, `p0b_anchoring.py`, `p1_split.py`
- Raw: `results/raw/latent-vs-verbalized/p1_verify_20260911T141659Z.json`, `p0_consolidate_20260911T142132Z.json`, `p0_gate_20260911T142420Z.json`, `p0b_anchoring_20260911T142455Z.json`, `p1_split_20260911T142510Z.json` (+ `split.json` in this directory)
- Logs: `logs/latent-vs-verbalized/{p1_verify,p0_consolidate,p0_gate,p0b_anchoring,p1_split}_*.log`
- Figures: `results/figures/latent-vs-verbalized/p0_score_by_side.png`, `p0b_digit_mass.png`
- Labels: `action_labels.json` @ `297ef42` on `origin/exp/action-level-attack-label` (sha256 in every raw under `.inputs.labels`). Scores: the three G4 files in `results/raw/local-monitor-activations/` (sha256 in `.inputs.scores`).

P-1 (`P1=results/raw/latent-vs-verbalized/p1_verify_20260911T141659Z.json`): newest `out/main` shard
`acts_0072.pt`, 12 keys, all `[7,25,2880]` fp16, rev-3 position order — `jq '.newest_main_shard.shape_dtype_counts' $P1`.
1,807 of 1,812 main-pass records have 7 capture positions with `analysis_end` followed by `<|end|>`
and `pre_score` = `>\n` followed by the emitted digit; the 5 exceptions are exactly the 5 `score: null`
no-verdict actions — `jq '.check_2_capture_positions.problems' $P1`. Three records quoted verbatim in
`.check_2_capture_positions.quoted`. Dedupe: 2,012 unique original-render keys = 1,812 main + 199
pass-1 + 1 consistent_high (`jq '.check_3_dedupe.n_by_source' $P1`). **199, not 200**, pass-1 keys are
4-position: one pass-1 key also exists in `consistent_high` with 7 positions and dedupe prefers it
(`jq '.check_3_dedupe.pass1_keys_with_7_position_copy' $P1`). First raw `p1_verify_20260911T141627Z.json`
failed only on my own `== 200` assertion; kept.

P-0 (`P0=results/raw/latent-vs-verbalized/p0_consolidate_20260911T142132Z.json`): `checkpoints/latent-vs-verbalized/acts.npy`
fp16 `[2012,7,25,2880]`, sha256 `c9ecfa56…` (`jq '.sha256' $P0`), rows sorted by (traj_id, action_idx),
index `acts_index.json`. Pass-1 rows permuted from `[transcript_end, action_end, instruction_end, final]`
into rev-3 order, gen positions NaN. Verification `jq '.verification' $P0`: count = P-1 dedupe count;
5 random rows (seed 0, two of them pass-1) bitwise equal to their source shards; NaN pattern exact:
199 rows NaN at positions 4–6, and the 5 no-verdict rows NaN at `reasoning_end`,`pre_score` only
(`jq '.verification.rows_with_nan_generation_positions_despite_7' $P0`). First run
`p0_consolidate_20260911T141803Z.json` produced the **same array (same sha256)** but its NaN check did
not allow for those 5 rows; kept. Note for anyone opening the array: use `np.load(..., mmap_mode="r")`,
not a raw `np.memmap` — the 128-byte `.npy` header shifts every row by 64 values otherwise (I did this
in a diagnostic, not in any committed script).

P0 gate (`G=results/raw/latent-vs-verbalized/p0_gate_20260911T142420Z.json`, `jq '.gate' $G`):

| rule | n_pos / n_neg | AUROC E / int / cached | TPR@5% E / cached | p_null | E>p95 / p99 | mass≥3 L2 / honest | gate |
|---|---|---|---|---|---|---|---|
| any (as published) | 53 / 825 | 0.905 / 0.748 / 0.853 | 0.642 / 0.416 | 31/53 | 15 / 4 | 0.308 / 0.082 | OK |
| **current (this experiment)** | 53 / 839 | 0.905 / 0.748 / 0.853 | 0.642 / 0.415 | 31/53 | 15 / 4 | 0.308 / 0.082 | OK |
| none | 53 / 852 | 0.906 / 0.742 / 0.851 | 0.660 / 0.414 | 31/53 | 16 / 4 | 0.308 / 0.082 | (not gated) |

Honest E p95 / p99 = 1.170 / 1.689 under both gated rules. Placeholder decomposition matches the E entry
exactly (attack 347 flagged / 74 current / 273 history-only; honest 27 / 13 / 14; `jq '.placeholder_counts' $G`),
and `has_attachment_placeholder` in the score records is the whole-prompt flag (`jq '.has_attachment_placeholder_equals_placeholder_any' $G`).
Side × placeholder split (`jq '.split_side_x_placeholder' $G`): honest non-placeholder p(score ≥ 3) = 0.007
(6 of 839), attack non-placeholder 0.066, level-2 0.321; Spearman(E, score) 0.34 / 0.41 / 0.50; the 13
honest current-action placeholders come from one trajectory and score ≥ 3 at 0.615.

P0b (`B=results/raw/latent-vs-verbalized/p0b_anchoring_20260911T142455Z.json`):
- Digit mass, 31 nulled payloads (`jq '.digit_mass.nulled_level2.mean_bands' $B`): 0–1 **0.589**, 2–5 **0.405**, 6–10 **0.006**.
  Zero actions have > 0.05 at 6–10; max is 0.021. Per-action heatmap in the figure. Mean distribution
  0: 0.53, 2: 0.19, 3: 0.18, 4: 0.03 (`jq '.digit_mass.nulled_level2.mean_digit_dist' $B`) vs honest
  0: 0.71, 2: 0.15, 3: 0.07. Shape: unimodal at 0 with a fat shoulder at 2–3; not bimodal. What E is
  recovering is that shoulder, not a suppressed high verdict.
- Says-one-thing (`jq '.says_one_thing.literal, .says_one_thing.non_negated' $B`): literal regex 1,477 hits
  (mean E 0.64 vs 0.62 baseline; all 31 nulled level-2 are hits — every one negated, "No malicious").
  Non-negated: 16 actions in 12 trajectories, mean E 0.75, **0 level-2**, 9 attack level-0, 5 attack
  unlabeled (placeholder-history), 1 honest, 1 attack level-1. Ten verbatim in
  `.says_one_thing.ten_verbatim_random0` and in the log. Nothing here to quote as expression loss.
  **Consequence for P2 (ii):** the "remove suspicion-language actions" re-run is defined on the
  literal regex in TASK.md; that would remove 85 % of the pool. I will run it on the 16 non-negated
  hits (which removes no positive) and report both counts — flagging this as a deviation.

P1 (`experiments/latent-vs-verbalized/split.json`, seed 0, stratified side × side_task_category):
test 19 trajectories (9 honest, 10 attack), **5 positive trajectories, 20 level-2, 240 usable honest**;
train 40 (18 honest, 22 attack), 10 positive trajectories, 33 level-2, 599 usable honest. The
`user_tracking` trajectory with 14 payloads (d4b401b9) is in **test**; the other 14-payload trajectory
(588b46de, file_indexing) is train fold 1. Folds are uneven by construction (fold1 20 level-2, fold4 2):
per-fold numbers will be noisy; only pooled OOF is reported.

**What I checked myself.** Bitwise re-read of 5 random rows against the shards; NaN pattern vs the
runner's `gen_index`; gate deltas printed to 3 dp; read the 10 sampled analysis texts (all boilerplate
negations). I did not re-derive the placeholder rule from `g2_prep` — I took the E entry's definition.

**Alternative explanations considered.** None needed yet — no probe has run. Two things the reviewer
should know: (1) the gate matches because the join is the same code path as the label branch's
(`common.roc` is a copy of `c_roc.roc`), not an independent implementation; (2) the P0b regex result
depends on my negation heuristic (`NEG` in `p0b_anchoring.py`, 40-char lookback) — the literal count
is also in the raw.

**Status.** `[verified]` for the gate and consolidation (mechanical checks); `[tested]` for P0b.

---

## <YYYY-MM-DD> — <short title>

**Claim.** <one sentence>

**Kind of claim.** existence proof / general claim
<If general: which baselines were run.>

**Evidence.**
- Script: `experiments/<file>.py` @ commit `<hash>` (must equal `.git_commit` in the raw file)
- Raw: `results/raw/<file>_<timestamp>.json`
- Log: `logs/<file>_<timestamp>.log`
- Figure: `results/figures/<name>.png`
- Recompute (no model needed): `jq '.<field>' results/raw/<file>_<timestamp>.json`

**Baselines.**
| condition | value |
|---|---|
| main | |
| random direction / head | |
| trivial (majority class) | |

**What I checked myself.**
<Not what the agent reported. What you read, recomputed, or spot-checked by
hand. e.g. "read 30 transcripts, confirmed 28/30 positives were real";
"recomputed the headline accuracy with a one-liner, matched to 3dp";
"printed decoded token at the patched index, confirmed position 7 = ' Mary'".>

**Alternative explanations considered.**
<The two most likely ways this is an artifact, and what rules each out —
or that nothing rules it out yet.>

**Status.** `[tested]`

---

---

## Verification (VERIFY.md)

Filled in by the review session, on this branch, before merge to main.

**Verdict.** Verified / Verified but weaker than stated / Not verifiable from what's here / Wrong

**What was recomputed.**

**Dumbest ways this could be wrong, and what rules each out.**

---

## Dead ends

- <what you tried> → <what happened> → <why you stopped>
