# Summary figures — captions (FIGURES.md, 2026-09-12)

Captions are the FIGURES.md text with numbers replaced only where the committed raws say otherwise; every
replacement is listed under "differs from FIGURES.md". Recompute commands are in
`experiments/latent-vs-verbalized/RESULTS.md` (entry "Summary figures F1–F4").

## F1 — `F1_readout_loss.{png,svg}` (`fig_F1.py`; P4 + P0b)

The forced digit distribution E beats the emitted integer at a 5 % FPR budget (TPR 0.64 vs 0.41) and not
at 1 % (0.30 vs 0.33). What E recovers on the 31 payloads the integer scores ≤ 1 is mass at 2–3 (inset),
not a hidden high verdict (mass on 6–10: 0.006). gpt-oss-20b, 53 level-2 payloads vs 839 honest actions
(the pool of the committed pooled-59 ROC in P4); bands are trajectory-cluster bootstrap 95 % CIs; below
1e-2 the dashed curve is a logit-linear extrapolation, not a measurement.

Differs from FIGURES.md: the caption's "743 honest" → 839. The TPR numbers in the FIGURES.md caption
(0.64 / 0.41 / 0.30 / 0.33) are the 839-pool values from P4; no committed raw carries a ROC curve on the
common 743 pool. On that pool (P7 §1, scalars only): E 0.55 [0.39, 0.81], integer 0.42, cached 0.40 at
5 %; 0.30 / 0.33 / 0.30 at 1 %. Drawing a 743-pool curve needs a recompute from P3's per-row scores,
which FIGURES.md rules out.

## F2 — `F2_no_probe_beats_E.{png,svg}` (`fig_F2.py`; P7 + P3 + P11)

After nine baselines no probe ranks payloads better than E where it matters. The score probe's pooled
edge (+0.046, paired CI [+0.002, +0.119]) is a denoised E — it ties E on the payloads the integer misses
(11 vs 11 of 31). The label probe ties E pooled and collapses under leave-one-category-out (0.75; 0.57 on
data_tampering) and length/position-matched negatives (0.77); 9 of its 18 recoveries come from one
trajectory. Pooled markers and recoveries use the common 743-honest pool; whiskers are cluster-bootstrap
95 % CIs; the leave-one-category-out markers are P3's (each scorer's full pool: 839, or 743 for the score
probe) and the matched markers use 147 negatives.

Differs from FIGURES.md: "(14 from one trajectory)" → 9 (14 is that trajectory's count of nulled
payloads; the label probe lifts 9 of them above the 743-pool p95). E has no leave-one-category-out
marker (it is not trained).

## F3 — `F3_where_signal_sits.{png,svg}` (`fig_F3.py`; P2 sweep)

Linear signal for the label-supervised probe peaks at the last token of the action (0.93) and decays
through the fixed template suffix (0.78 → 0.69); no generation-side position exceeds it (0.84, 0.90,
0.84). The score-supervised probe is flat at 0.93 from the action onward (0.93 / 0.93 / 0.93 / 0.93 at
action, hidden-CoT, visible-reasoning and pre-digit positions). The pre-registered position, prompt_end,
is the weakest prompt-side position for both arms. Train out-of-fold, 33 payloads vs 599 honest over 40
trajectories; E on the same rows 0.89; bands are the range of the five fold-wise AUROCs of the best
cell (the pooled OOF value can fall outside that range, as it does for the label arm at hidden-CoT end).

Differs from FIGURES.md: "no generation-side position exceeds it" is qualified to the label arm — for
the score arm hidden-CoT end (0.9322) and visible-reasoning end (0.9324) are 0.001 above the action-end
value (0.9311). No CI exists in the raw for the per-position best cells; the fold range is what P2
recorded.

## F4 — `F4_verdict_in_cot.{png,svg}` (`fig_F4.py`; P12 + P12C)

On the payload where the integer beats E, the pre-CoT readout is at E (0.44) and the digit moves at the
sentence naming the covert objective (left: 0.4–1.6 through s10, 4.5 at s11, 9.0 at the end; the
objective sentence alone gives 5.7, a benign conclusion swapped in gives 0.2). The same sentences
appended to a benign edit drive the digit to 7.6 (6.1 without a verdict word), while length- and
register-matched concern without an objective reads 1.0, a lift of 0.75 over the 0.27 baseline, and the
verdict word alone 0.1 (right): the readout follows the CoT's stated objective match and does not check
it against the diff. One trajectory (`30e71655`), n = 1; `#26` rises on verdict language one sentence
earlier.

Differs from FIGURES.md: "matched-register concern, no objective → ≤ 0.8" → the value is 1.0; ≤ 0.8 is
the lift over the 0.27 prefix baseline (0.75 on `#27`, 0.61 on `#24`). Both numbers are on the figure.
