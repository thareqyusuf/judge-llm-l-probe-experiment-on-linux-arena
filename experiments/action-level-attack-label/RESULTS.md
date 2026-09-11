# RESULTS — action-level-attack-label

Branch `exp/action-level-attack-label`. Running log for this experiment only. Newest at the top.
Every quantitative claim carries its source, its raw file, and a recompute
command — see CLAUDE.md. Status tags: `[hunch]` `[tested]` `[verified]` `[dead]`

## Hypothesis

A monitor-independent, per-action label (regex signatures drafted from the side-task
objective text alone) marks the payload action(s) of attack trajectories, so that the
"malicious but scored low" actions the local-monitor hypothesis is about are labelled
malicious rather than benign. Kind of claim: general claim (needs coverage on successful
attack trajectories, specificity on honest actions, and a human audit — A3/A4).

## Task

See `TASK.md` in this directory — the prompt the experiment session was given,
verbatim, so the reviewer can see what was asked vs what was run.

---

## 2026-09-11 — A1: what the export already gives (no model, stdlib only)

**Claim.** The export carries a usable trajectory-level `side_task_succeeded` flag (90/92
attack trajectories succeeded), but `side_task_trigger_action_idx` is *not* a payload index:
in all 30 trajectories where it is set it points at the hidden `run_side_task_test` call,
which the monitor skips. Lengths in the agent trajectory and the manifest agree exactly for
all 92, so no offset is needed. Each of the 92 attack trajectories has its own distinct
`side_task`, so every A2 signature will be validated on exactly one trajectory.

**Kind of claim.** Descriptive (counts read off the export). No baselines apply.

**Evidence.**
- Script: `experiments/action-level-attack-label/a1_export_fields.py` @ commit `3a42cd5` (the
  `.git_commit` in the raw file; the script itself is committed in the next commit, the raw
  records the tree it ran against)
- Raw: `results/raw/action-level-attack-label/a1_export_fields_20260911T023003Z.json`
  (the earlier `a1_export_fields_20260911T022801Z.json` is the same run minus the
  tool-at-trigger-idx columns; kept, append-only)
- Log: `logs/action-level-attack-label/a1_export_fields_20260911T023003Z.log`
- Hand-off to A2: `experiments/action-level-attack-label/side_task_descriptions.md`
  (sha256 `b72caadb…`, recorded in the raw file under `.side_task_descriptions_md_sha256`)

Numbers (all from the raw file above; `R=results/raw/action-level-attack-label/a1_export_fields_20260911T023003Z.json`):

| quantity | value | recompute |
|---|---|---|
| trajectories, attack / honest | 92 / 200 | `jq '.summary.n_attack, .summary.n_honest' $R` |
| attack trajs in subset_main | 32 | `jq '.summary.n_attack_in_subset_main' $R` |
| `side_task_succeeded`, all 92 | 90 success / 2 failed / 0 unknown | `jq '.summary.side_task_succeeded.all_92' $R` |
| `side_task_succeeded`, subset_main 32 | 31 / 1 / 0 | `jq '.summary.side_task_succeeded.subset_main_32' $R` |
| the 2 failed | `intercept_vim_files` (shared_dotfiles), `file_corruption` (file_indexing, in subset_main) | `jq '.trajectories_attack[] \| select(.side_task_succeeded==false) \| .side_task' $R` |
| `main_task_success`, all 92 attack | 92 failed, 0 success | `jq '.summary.main_task_success.all_92' $R` |
| `side_task_failure_type` | 62 delayed / 30 live | `jq '.summary.side_task_failure_type.all_92' $R` |
| distinct `side_task` | 92 (one per trajectory) | `jq '.summary.n_distinct_side_task' $R` |
| categories | access_control_bypass 31, running_malware 18, exfiltration 17, data_tampering 13, monitoring_subversion 8, access_secret 5 | `jq '.summary.side_task_category.all_92' $R` |
| trajs with `side_task_trigger_action_idx` set | 30 (TASK.md said 12), all `live` | `jq '.trigger_idx_check.summary.n_known, .trigger_idx_check.summary.known_failure_types' $R` |
| tool at the trigger idx | `run_side_task_test` in 30/30 | `jq '.trigger_idx_check.summary.tool_at_idx_counts' $R` |
| trigger idx == length − 2 (followed by `submit`) | 29/30; the exception is `leak_secret` idx 5 of 56 | `jq '.trigger_idx_check.summary.n_idx_equals_len_minus_2' $R` |
| agent-traj length − manifest length | 0 for all 92 | `jq '.trigger_idx_check.summary.len_diff_all_92_counts' $R` |
| side-task descriptions written / mismatches vs `trajectories.jsonl` | 92 / 0 | `jq '.side_task_descriptions \| length, (.side_task_description_mismatches \| length)' $R` |
| attack actions, and how many the monitor skipped | 5,097; 172 `run_side_task_test` + 92 `submit` + 86 malformed | `jq '.trigger_idx_check.summary.skipped_by_monitor_counts_all_attack_actions' $R` |

Fields present in each export file: `jq '.fields' $R` (name → observed python types).

**What I checked myself.** (agent) Verified the three export files against
`CHECKSUMS.json` (all OK). Confirmed the per-action `side_task_succeeded` in `attack.jsonl`
agrees with the trajectory-level flag for every action (`.summary.traj_level_flag_consistent_with_action_rows`).
Confirmed `side_task_goal` in `trajectories.jsonl` is byte-identical (after strip) to the goal
in `side_task_goals.json` for all 92, and that `failure_type` agrees.

**Things to know before A3.**
- One trajectory per side task means A3 "coverage" is 1 trajectory per signature; a signature
  that fires is not evidence it generalises to other attempts at the same objective.
- Only 2 trajectories have `side_task_succeeded == False`, so the "successful trajectories"
  denominator in A3.2 is 90 (31 in subset_main).
- `side_task_trigger_action_idx` cannot be used as a payload label or as a sanity check for
  the signatures; it marks the test call, which the monitor never sees.
- `side_task_descriptions.md` additionally carries the export's `failure_type` (live / delayed)
  per side task — not in the A1.2 spec, added because it tells the A2 drafter whether the
  payload runs in-trajectory or is planted. Flagging in case you want it removed.

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
