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
