# CLAUDE.md

Mech interp research project. Read this before doing anything.

## The one thing

I am being evaluated on whether I catch your mistakes, not on whether you
produce results. A plausible-looking wrong result is worse than no result,
because it costs me hours to discover and it sinks the writeup if it survives.
Optimise for me being able to check you fast.

## Environment

- Repo: `/workspace/repo`. Everything persistent is under `/workspace`.
- Python: `/workspace/venv` (already on PATH). `uv pip install` to add packages.
- Weights cache: `$HF_HOME=/workspace/hf`. Never download to the container disk.
- Model internals: use **nnsight**, or raw PyTorch hooks. Both are fine.
- Reference docs are in `/workspace/context/`. Read them before guessing at an API.

## Kernel discipline

There is a persistent Jupyter kernel. The model is loaded once and stays in
memory. Cold-start scripts that reload weights every run waste minutes per
iteration and are not acceptable for exploratory work.

- Load models and datasets in **dedicated cells at the top**, nothing else in them.
- **Never restart the kernel without asking.** Reloading a 27B model is a
  multi-minute tax and I may have state in memory you don't know about.
- Every plot gets `plt.savefig("results/figures/<slug>/<name>.png", dpi=150)`
  as well as being displayed. A figure that only exists in a cell output is
  a figure I can't put in the writeup.
- Anything that runs longer than ~10 minutes goes to a background script with a
  logfile in `logs/<slug>/`, not a notebook cell. Checkpoint expensive
  artifacts (activations, datasets, trained SAEs) to `checkpoints/<slug>/`
  as you go, so a crashed kernel costs minutes and not the night.
- Before a long run, sanity check on a tiny slice (2 prompts, 1 layer) and show
  me the output. Do not launch the full sweep until that looks right.

### Route B — JupyterLab kernel via MCP (primary)

The `jupyter` MCP server (registered `--scope user`, so it's available in
every Claude Code session on this pod) gives you tools to create, edit, and
execute cells against a live kernel backing `experiments/lab.ipynb`. Check
`/mcp` shows `jupyter` connected before relying on it.

- The JupyterLab server for this workflow runs in tmux window `mi:jupyter`,
  on **port 8889** (not 8888 — that port is already held by the platform's
  own default Jupyter instance, which lacks the collaboration/MCP extensions
  and is unrelated to this project; it was left running untouched). Token is
  `JUPYTER_TOKEN` in `/workspace/.env`.
- Notebook: `experiments/lab.ipynb`, server-relative path (server root is
  `/workspace/repo`). A kernel is already attached to it — don't let the MCP
  server spin up a second one; connect to the existing session first.
- To watch from a browser: port-forward 8889 from your laptop
  (`ssh -N -L 8889:localhost:8889 ...`), then open
  `http://localhost:8889/lab?token=<JUPYTER_TOKEN>`.
- `.gitattributes` runs notebooks through `nbstripout` on commit, so
  `experiments/lab.ipynb` diffs cleanly (outputs are stripped, code isn't).

### Route A — IPython in tmux (fallback, not currently running)

If the Jupyter MCP connection misbehaves (stuck kernel, MCP server won't
reconnect, etc.), fall back to this — Neel's doc calls it "crude but
unbreakable." Nothing is set up for it yet; to switch, tell me and I will:

1. Open a new tmux window in session `mi`, name it `kernel`, run `ipython`.
2. Load the model there once, same discipline as above — don't reload it.
3. Drive it as: `tmux send-keys -t mi:kernel '<code>' Enter` to run code,
   `tmux capture-pane -p -t mi:kernel -S -100` to read output.
4. Save plots to disk as PNG — you can't see the terminal's rendering.

No MCP, no tokens, no port-forwarding — the trade is reading terminal
scrollback instead of rendered cells.

## The filesystem contract

Everything is namespaced by experiment slug, so experiment branches never
touch the same files and merge cleanly.

```
experiments/<slug>/TASK.md       the prompt this experiment was given, verbatim   (committed)
experiments/<slug>/RESULTS.md    this experiment's claims, each one traceable     (committed)
experiments/<slug>/*.py          its scripts                                      (committed)
results/raw/<slug>/              every raw output, append-only, NEVER overwritten (committed)
results/figures/<slug>/          plots as PNG                                     (committed)
logs/<slug>/                     stdout from runs                                 (committed)
checkpoints/<slug>/              expensive intermediates                          (gitignored)
RESULTS.md                       index: one row per experiment, edited on main    (committed)
experiments/lab.ipynb            shared scratch kernel notebook, outputs stripped (committed)
```

Raw outputs are append-only. If a run supersedes an earlier one, write a new
file with a new timestamp — don't overwrite. I need to be able to compare.

Raw outputs are also **small**: JSON/CSV of the numbers, never tensors. Keep a
single raw file under ~10 MB. Anything bigger is a checkpoint, not a raw
output; write a raw file next to it that holds the numbers derived from it.

Scripts find their namespace from their own location:
`SLUG = Path(__file__).resolve().parent.name`. Never hardcode a slug.

## Branches: one experiment, one branch

- `main` holds infra, docs, templates, and the `RESULTS.md` index. No raw
  results are ever committed directly to main.
- Each experiment lives on `exp/<slug>` (lowercase, hyphens; name the
  question, not the method: `induction-heads`, `ioi-name-mover`). Start one
  with `bash infra/new-experiment.sh <slug>` from a clean main. It scaffolds
  the namespace above, commits, and pushes.
- Commit messages on the branch are `exp(<slug>): <what ran>`.
  `infra/handoff.sh` writes them for you.
- A follow-up that changes the *question* is a new experiment and a new
  branch. A follow-up that changes seed, size, or a bug fix stays on the
  branch as another run.
- Infra or doc changes discovered mid-experiment go on main (or a short
  `infra/<thing>` branch), then `git merge main` into the experiment branch.
  Never smuggle them into an `exp(...)` commit; handoff.sh will warn.
- Branches are merged into main with `git merge --no-ff exp/<slug>` **after
  the laptop-side review has written its verdict** into the experiment's
  `RESULTS.md`. Dead experiments get merged too — a negative result is a
  result. The merge commit updates the row in the root `RESULTS.md` index.
- Branches are never deleted after merge, and never force-pushed.

## Handoff: pod → GitHub → laptop

The pod is rented and gets terminated. The laptop has no GPU. The review
(`VERIFY.md`) happens on the laptop, from the git checkout alone, without
the model. That drives three rules:

1. **Every run ends with a commit and a push.** Script, raw JSON, figure,
   log, and the entry in `experiments/<slug>/RESULTS.md` go in together.
   Run `bash infra/handoff.sh "<what ran>"` — it refuses if you are on main,
   if no raw file changed, if RESULTS.md was not touched, or if a staged
   file is over 10 MB. An unpushed result is a result that dies with the pod.
2. **The raw file must let someone recompute the headline number without
   the model.** That means it carries the *inputs* to the number, not just
   the number: the exact `input_ids`, the per-token losses (not just their
   means), the full score arrays for main *and* control conditions, which
   heads were ablated, seeds, model id, dtype, attention implementation,
   the git commit of the script. If the recompute command in `RESULTS.md`
   would need a forward pass, the raw file is incomplete.
3. **Decoded tokens go in the raw file too.** Boundary tokens, patched
   positions, top-k tokens — whatever a reviewer would want to eyeball goes
   in as strings, so it can be read off the JSON on a machine with no
   tokenizer.

## The citation rule

**Every quantitative claim in `RESULTS.md` must carry:**

1. the script or notebook cell that produced it,
2. the path to the raw output file it came from,
3. a one-line command that recomputes the headline number from that raw file.

Not "the probe reaches 87% accuracy." Instead:

> Probe reaches 87.3% accuracy on held-out set.
> `experiments/probe_layer12.py` → `results/raw/probe_l12_20260902T1430.json`
> Recompute: `jq '.held_out_acc' results/raw/probe_l12_20260902T1430.json`

If a claim can't carry those three things, it isn't a result yet, it's a hunch.
Mark it as one.

## Experimental standards

**Know which kind of claim you're making.** An existence proof ("this
phenomenon occurs") permits cherry-picking a striking example. A general claim
("this method works", "heads X and Y implement Z") does not, and needs
baselines. State which one you're going for before running anything.

**Baselines are not optional for general claims.** At minimum: the trivial
baseline (majority class, random direction, random head), and the ablation of
your intervention. If you didn't run a baseline, the number is uninterpretable
and should be labelled as such.

**Report failures.** Experiments that didn't work, runs that OOM'd, hypotheses
that died — these go in `RESULTS.md` too. A negative result I know about is
worth more than one I rediscover in the writeup.

## How to report to me

- Say what you actually ran and what actually came out. No "successfully
  implemented" — describe the behaviour and let me judge.
- When a result looks good, say so **and** name the two most likely ways it's
  an artifact. You are better placed than me to know what shortcuts the code took.
- Flag uncertainty explicitly. "I think this is right but I didn't verify X"
  is useful. Confident phrasing over unverified work is not.
- If you had to guess at an API, a hyperparameter, or what I meant, say where.

## Not your call

These are mine. Ask, don't decide:

- **What hypothesis we're testing** and whether the evidence supports it.
- **Experimental design** — which controls, which baselines, which comparison.
  You are good at running experiments and bad at noticing that the experiment
  doesn't test the hypothesis.
- **Changing the metric mid-project.** If the current metric looks bad, tell me
  it looks bad. Do not switch to one that looks better.
- **Declaring an experiment worked.** Report the numbers. I decide.

## Never

- Delete or overwrite anything in `results/raw/`.
- Commit results to `main`, or leave a finished run uncommitted or unpushed.
- Force-push or delete an `exp/*` branch.
- Restart the kernel unprompted.
- Put secrets in the repo (they live in `/workspace/.env`).
- Write claims into `RESULTS.md` that your own outputs don't support.
