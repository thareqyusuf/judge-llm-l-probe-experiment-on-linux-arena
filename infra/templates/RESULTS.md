# RESULTS — <slug>

Branch `exp/<slug>`. Running log for this experiment only. Newest at the top.
Every quantitative claim carries its source, its raw file, and a recompute
command — see CLAUDE.md. Status tags: `[hunch]` `[tested]` `[verified]` `[dead]`

## Hypothesis

<one sentence, falsifiable>. Kind of claim: existence proof / general claim.

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

## Verification (laptop side, VERIFY.md)

Filled in by the review session, on this branch, before merge to main.

**Verdict.** Verified / Verified but weaker than stated / Not verifiable from what's here / Wrong

**What was recomputed.**

**Dumbest ways this could be wrong, and what rules each out.**

---

## Dead ends

- <what you tried> → <what happened> → <why you stopped>
