# VERIFY.md

The standing prompt for the verification session. Paste the framing block
below into a **fresh** Claude Code session in the `verify` tmux window,
then add the specific claim.

Do not let this session read the experiment session's transcript, its summary
prose, or its explanation of why the result makes sense. It reads code and raw
outputs only. The point of the separation is that the checker has not been told
what to believe.

## Where this runs

On the **laptop**, from a fresh `git pull`, with no GPU and no model. The pod
pushes everything the review needs (see CLAUDE.md, "Handoff"). The checker
recomputes from `results/raw/*.json` with `jq`/`python` only. If a headline
number cannot be recomputed from the raw file without a forward pass, the
verdict is **Not verifiable from what's here**, and the missing field in the
raw file is the finding. Do not start a pod to fill the gap; send the gap
back to the experiment session.

Pre-flight, before the three questions:

- `git fetch && git checkout exp/<slug>` — the review happens on the
  experiment's branch, and the verdict is written into
  `experiments/<slug>/RESULTS.md` on that branch, under "Verification".
  Main is only touched at merge time.
- `git log --oneline main..HEAD` and `git log -1 --stat` — does the branch
  contain script, raw JSON, figure, log, and a `RESULTS.md` entry? Missing
  one is a finding.
- Read `experiments/<slug>/TASK.md` and compare it to what the script does.
  "Asked for 2 layers, ran 36" is a finding even when harmless.
- Does the raw file's `script`/`git_commit` field match the script you are
  reading? A script edited after the run is not the script that produced
  the number.
- Does the number in `RESULTS.md` appear verbatim in the raw file?

---

## The framing

> I have a research claim and the code and raw data behind it. I did not write
> this code and I have no stake in the claim being true — I need to know if it's
> wrong before I put it in a writeup that gets read carefully.
>
> Don't verify that the code does what it says. Verify that the number means
> what it's being taken to mean. Those are different, and the second one is
> where things go wrong.
>
> Work through it in this order:
> 1. Read the script and tell me what it actually computes, in your own words,
>    without reference to what it's supposed to compute.
> 2. Recompute the headline number from the raw output file independently.
> 3. Then: what is the dumbest way this result could be wrong?
>
> Claim: <paste the claim>
> Code: <path>
> Raw output: <path>

The third question does the work. "Is this correct?" invites agreement; "what's
the dumbest way this is wrong" invites a list.

---

## Standard failure modes, general

- **Data leakage.** Train/test split done after some transformation that saw
  both. Probe trained and evaluated on activations from the same prompts.
- **A trivial baseline matches it.** Majority class. Random direction. Random
  head. If nobody ran the baseline, the number means nothing yet.
- **The metric doesn't measure the thing.** Accuracy on a 95/5 split. Logit
  difference where probability was meant. Unnormalised patching scores.
- **Sample size too small to distinguish from noise**, and no seed variance
  reported.
- **Cherry-picking that migrated.** An example chosen to illustrate a
  phenomenon later being cited as evidence for a general claim.
- **The number in the writeup isn't the number in the output file.** Check.

## Standard failure modes, mech interp specific

These are the ones that bite in this field and that generic code review misses:

- **BOS token handling.** `prepend_bos` on or off changes results, sometimes a
  lot. Attention sinks at position 0 absorb enormous attention mass and can
  dominate any head-level analysis that doesn't account for them.
- **Token position off-by-one.** Is the patch landing on the token you think?
  Print the decoded token at the index being patched. Do it every time.
- **Clean/corrupted pairs not token-aligned.** If the two prompts tokenize to
  different lengths, position-wise patching is comparing unrelated positions.
- **Layer indexing convention.** `resid_pre[i]` vs `resid_post[i]`, and whether
  the library is 0- or 1-indexed. An off-by-one layer is a different claim.
- **No random-direction control.** A steering vector that changes behaviour
  should be compared against a random vector of the same norm. Many "steering
  works" results survive this poorly.
- **No random-head / random-layer control** for ablation and patching results.
- **Effect size vs the model's baseline drift.** Does the intervention do more
  than perturbing the model at all does?
- **SAE latent interpretation taken on trust.** Auto-interp labels are
  hypotheses. Were max-activating examples actually read, by a human?
- **Held-out distribution.** Does the circuit/probe/vector work on prompts that
  weren't used to find it? Circuits found and tested on the same distribution
  are close to unfalsifiable.
- **Quantisation.** If the model isn't at full precision, "int8 artifact" is a
  live alternative explanation for anything subtle.

## What to hand back

For each claim, one of:

- **Verified** — recomputed independently, matches, controls present.
- **Verified but weaker than stated** — the number is right, the claim isn't.
- **Not verifiable from what's here** — say what's missing.
- **Wrong** — with the specific reason.

Then write the verdict and what you checked into the "Verification" section
of `experiments/<slug>/RESULTS.md`, commit it on the branch
(`verify(<slug>): <verdict>`), and only then merge to main. Also put it in the
writeup. "I read 30 transcripts and
confirmed the probe's positives were real" is itself evidence of research
skill, and it's the kind of sentence that distinguishes work you did from work
an agent handed you.
