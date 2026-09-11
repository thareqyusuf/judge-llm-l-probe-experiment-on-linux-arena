# TRANSFER MANIFEST — TASK-A bundle

Built on the pod from `/workspace/judge-llm-l-probe-experiment-on-linux-arena`
at commit `d7eb97f25d1e0ca90731dbfecab18a30a87593b2` (branch exp/local-monitor-activations), 2026-09-11T021758Z.

Extract at the **repo root** of your local checkout; every path below is repo-relative:

    cd "/home/tarek/Projects/mech-interp/neel application/mech-interp-2"
    tar -xzf ~/Downloads/taskA_bundle_20260911T021802Z.tar.gz
    sha256sum -c experiments/action-level-attack-label/TRANSFER-SHA256.txt

## What is here and which step needs it

| path | step | note |
|---|---|---|
| checkpoints/local-monitor-activations/data/export/trajectories.jsonl | A1 | 292 trajs; side_task_goal, side_task_succeeded, main_task_success, trigger idx |
| checkpoints/local-monitor-activations/data/export/attack.jsonl | A3,A4,A5 | 5,097 attack actions: tool_name + tool_input + output |
| checkpoints/local-monitor-activations/data/export/honest.jsonl | A3.3 | 12,675 honest actions (specificity check) |
| checkpoints/local-monitor-activations/data/export/CHECKSUMS.json | all | upstream sha256 of the three files |
| experiments/logit-curve-replication/gpu/format_monitor_prompt.py | A2,A3 | `format_action(a, hide_output=True)` == the `current_action` string the regexes run on. Stdlib only |
| experiments/logit-curve-replication/gpu/prompts/old_action.md | A3 | prompt template (only needed if you re-render a full prompt) |
| experiments/logit-curve-replication/gpu/side_task_goals.json | A1.2 | per-env rendered side-task goal block |
| experiments/logit-curve-replication/gpu/manifest.json | A5, B | cached_scores + cached_mean + side/env/tool for all 17,234 actions |
| experiments/local-monitor-activations/monitor_prompt.py | A3.5 | `has_attachment_placeholder`, `load_trajs`, `load_export`. Stdlib only |
| experiments/local-monitor-activations/subset_main.json | A1,A3,A4 | the 2,012 actions (1,156 attack / 856 honest; 32 attack trajs) |
| results/raw/local-monitor-activations/g2_prep_20260910T103431Z.json | A5, B | `.per_action` = columnar n_tokens / placeholder / cached_mean for all 17,234 |
| CLAUDE.md, VERIFY.md, RESULTS.md, .gitignore, .gitattributes, infra/ | — | repo conventions + handoff.sh |
| experiments/action-level-attack-label/{TASK.md,RESULTS.md} + empty results/logs dirs | — | scaffold for this experiment (TASK.md is your prompt verbatim) |

## Deliberately NOT in the bundle

- `experiments/local-monitor-activations/RESULTS.md` (120 KB) and every
  `results/raw/local-monitor-activations/*scores*.jsonl` — these quote high-cached action
  text. They are the contamination hazard named in the contamination rule. Pull them from git
  if the main session needs them; keep them away from the A2 session.
- The other four `g2_prep_*.json` runs. Their `.per_action` columns (traj_id, action_idx,
  n_tokens, placeholder, cached_mean) are bitwise-identical to the one included; verified on the pod.
- Model weights, HF cache, .env, checkpoints/*/out — not needed, nothing here runs a forward pass.

## Verifying the export

    cd checkpoints/local-monitor-activations/data/export
    python3 - <<'PY'
    import hashlib, json, pathlib
    c = json.load(open("CHECKSUMS.json"))["checksums"]
    for name, meta in c.items():
        h = hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()
        print(name, "OK" if h == meta["sha256"] else "MISMATCH", meta["bytes"], "bytes")
    PY

Expected: attack.jsonl c8a4a22b…, honest.jsonl cbc0994d…, trajectories.jsonl 38e00f14…  (all three verified on the pod at build time).

Optional, if you want the logit-curve scripts to find the export at their own path:

    mkdir -p experiments/logit-curve-replication/data_export/data
    cd experiments/logit-curve-replication/data_export/data
    for f in attack honest trajectories; do ln -sf ../../../../checkpoints/local-monitor-activations/data/export/$f.jsonl .; done

## Python needs

stdlib for A1–A3/A5; numpy + scipy for the Mann-Whitney in B; matplotlib for a3_label_position.png.
Do **not** import `run_monitor.py` — it pulls torch. `monitor_prompt.py` and
`format_monitor_prompt.py` are stdlib-only, so a plain CPU venv is enough.
