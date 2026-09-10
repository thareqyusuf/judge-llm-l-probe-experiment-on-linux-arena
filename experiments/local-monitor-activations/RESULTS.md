# RESULTS — local-monitor-activations

Branch `exp/local-monitor-activations`. Running log for this experiment only. Newest at the top.
Every quantitative claim carries its source, its raw file, and a recompute
command — see CLAUDE.md. Status tags: `[hunch]` `[tested]` `[verified]` `[dead]`

## Hypothesis

None is tested on this branch. Track G produces local gpt-oss-20b live-monitor scores and
residual-stream activations for the 17,234-action manifest from track L; every entry here is an
engineering-verification / descriptive claim (kind: general, about this pod and this pipeline;
no research hypothesis, no baselines beyond the checks named per entry).

## Task

See `TASK.md` in this directory — the prompt the experiment session was given,
verbatim, so the reviewer can see what was asked vs what was run.

---

## 2026-09-10 — G1: environment and hardware verification (+ attention backend)

**Claim.** The pod satisfies every G1 requirement (Blackwell sm_120, CUDA ≥ 12.8, pinned
packages, mirror fingerprints, gpt-oss-20b in native MXFP4 at 12.8 GiB), **but** two things
block G2 onward: the three L2 export files the runner reads are not on the pod, and neither of
transformers' shipped attention paths can run the long prompts (eager is O(L²) memory,
flex_attention fails at decode). A chunked eager attention written here runs a 131k-token prefill
within VRAM and is, at the function level, the same arithmetic as eager except that it keeps the sink softmax in fp32
(eager's is bf16 because gpt-oss's sinks load as bf16); that one difference accounts for the model-level logit gap.

**Kind of claim.** Engineering verification (descriptive). Controls: eager attention as the
numerical reference; eager-vs-eager repeat as the noise floor.

**Evidence.**
- Script: `experiments/local-monitor-activations/g1_env.py` @ commit recorded in `.git_commit` of the raw file
  (the script was run before this commit; the raw file's `git_commit` is the parent commit `ce1babc`).
- Raw: `results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`
- Log: `logs/local-monitor-activations/g1_env_20260910T070739Z.log`
- Attention probe: `experiments/local-monitor-activations/g1_attn_probe.py` + `chunked_attention.py`
  → `results/raw/local-monitor-activations/g1_attn_probe_20260910T071901Z.json`,
  log `logs/local-monitor-activations/g1_attn_probe_20260910T071746Z.log`
- Noise-floor probe: `experiments/local-monitor-activations/g1_attn_probe2.py`
  → `results/raw/local-monitor-activations/g1_attn_probe2_20260910T074025Z.json`,
  log `logs/local-monitor-activations/g1_attn_probe2_20260910T073915Z.log`
- Unit test: `experiments/local-monitor-activations/g1_attn_unit.py` → `results/raw/local-monitor-activations/g1_attn_unit_20260910T075628Z.json`
  (an earlier run with fp32 sinks only, `g1_attn_unit_20260910T075342Z.json`, is superseded, kept per append-only rule); logs `logs/local-monitor-activations/g1_attn_unit_*.log`
- Model-download log (fetched the whole repo incl. `original/` and `metal/`, 39 GB instead of 13 GB — harmless
  on this volume, wasteful): `logs/local-monitor-activations/g1_hf_download.log`
- Figures: none (G1 has no plot).

### G1.1 hardware — pass
NVIDIA GeForce RTX 5090, driver 580.159.03, 32,607 MiB (31.36 GiB usable per torch), compute
capability **(12, 0)**, torch **2.14.0+cu130**, CUDA **13.0** (≥ 12.8), cuDNN 91500, 64 CPUs.
Recompute: `jq '{hw: .hardware, checks: .checks}' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`

### G1.2 storage — pass
`HF_HOME=/workspace/hf` on the persistent volume (network FS, 578 TiB free). Mirror payloads cached
under `checkpoints/local-monitor-activations/data/api/` (gitignored, regenerable).
Recompute: `jq '.storage' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`

### G1.3 packages — pass, with one addition
All six pins in `experiments/logit-curve-replication/gpu/requirements.txt` match what is installed:
torch 2.14.0, transformers 5.17.0, tokenizers 0.23.2, accelerate 1.15.0, safetensors 0.8.0, numpy 2.5.3.
Also present: triton 3.8.0, huggingface_hub 1.30.0, nnsight 0.7.0; **flash_attn absent**.
**I installed `kernels==0.16.1`** (`uv pip install "kernels>=0.16,<0.17"`): transformers 5.17's
`Mxfp4HfQuantizer` silently sets `dequantize=True` (→ bf16, ~40 GB, OOM here) when `kernels` is
missing; `requirements.txt` does not list it (its comment only mentions the A100 dequantised path).
That is a track-L infra fix, not made on this branch.
Recompute: `jq '.packages' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`

### G1.4 mirror payloads — pass (one explained mismatch); **export files missing → blocker**
Fetched exactly four payloads: `lean` and `monitor-data` for the two *monitor* run ids.

| payload | bytes | sha256[:12] | trajs | actions | server fp == manifest | recompute == manifest |
|---|---|---|---|---|---|---|
| lean honest `f25f1eaf…` | 1,915,687 | `c9c4b3fb2661` | 200 | 12,675 | yes | yes |
| monitor-data honest | 25,386,404 | `8011dcff3eaa` | 200 | 12,675 | (no fp field) | **no** — explained below |
| lean attack `30d53f5a…` | 776,284 | `c5b75c3a9a8c` | 92 | 5,097 | yes | yes |
| monitor-data attack | 10,306,406 | `e9e555c2a7db` | 92 | 5,097 | (no fp field) | yes |

The honest `monitor-data` recompute differs only because that payload has no `main_task_success`
field (keys: `actions, run_id, side_task_success, traj_monitor_response, trajectory_id`), so the
fingerprint's `mt` term is 0 instead of lean's 132; ids, action counts (12,675) and the sus-score sum
(16629) agree. Substituting `mt=132` reproduces `190c8878…` exactly (attack has `mt=0` on both, so it
matched anyway). Check (needs the cached payloads, CPU only):
`python - <<'EOF'` … see the one-liner in the session log; equivalently rerun `g1_env.py`'s
`recompute_fingerprint` on the honest monitor-data trajectories with `mt` overridden to 132.
The manifest's *agent* fingerprints were not re-checked (would need two more payloads; TASK said fetch nothing else).
Recompute: `jq '.mirror.payloads | map_values({bytes, n_trajectories, n_actions, server_matches_manifest, recompute_matches_manifest})' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`

**Blocker.** `run_monitor.py` reads `honest.jsonl` / `attack.jsonl` / `trajectories.jsonl` (61 MB,
sha256 in the manifest). They are built by `data_export/export.py` from the mirror **plus the 16 GB
HF dump** (tool arguments and task descriptions are not on the mirror — L1) and are gitignored. They
are not on the pod. Nothing after G1, including G2's token counts, can run until they are copied to
`checkpoints/local-monitor-activations/data/export/` (the script checks their sha256 against the manifest).
Recompute: `jq '.data_files.files | map_values(.present)' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json` → all `false`.

### G1.5 gpt-oss-20b — loads in native MXFP4
Snapshot `6cee5e81…`, 3 safetensors shards, 12.82 GiB on disk. Load 34.6 s with
`dtype=bfloat16, device_map={"":0}, attn_implementation="eager"`.

| what | value |
|---|---|
| `torch.cuda.memory_allocated` after load | **12.83 GiB** |
| `model.get_memory_footprint()` | 3.37 GiB — **misleading**: only counts registered params (1.80 B: bf16 attention/router/embeddings + fp32 biases); the FP4 expert tensors are triton wrapper objects, not `nn.Parameter`s |
| `hf_quantizer` | `Mxfp4HfQuantizer`, `quantization_config.dequantize == False` |
| experts module (layers 0, 12, 23) | `Mxfp4GptOssExperts`; `gate_up_proj` [32, 2880, 5760] and `down_proj` [32, 2880, 2880] dtype `FloatType(e2m1)` (FP4); `*_precision_config.weight_scale` uint8 [32, 90, ·]; biases fp32 |
| bf16 would be | ~40 GB → would OOM on 31 GiB, so a successful load is itself weak evidence, as TASK said |

Greedy generation on a 79-token chat prompt ("capital of France?"): next-token p(`<|channel|>`) = 1.00;
output `<|channel|>analysis<|message|>…<|end|><|start|>assistant<|channel|>final<|message|>Paris<|return|>`
(64-token budget, 5.4 s). So harmony `analysis` → `final` parsing in `run_monitor.visible_answer` applies.
Recompute: `jq '.model.load | {seconds, cuda_memory_allocated_gib, get_memory_footprint_gib, hf_quantizer_class, quantizer_dequantize_flag}' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`;
`jq '.model.load.experts.layer_12.tensors | map_values({dtype, shape})' …`; `jq '.model.tests.eager' …`.

Tokenizer facts recorded for later steps (not G3 itself):
- `"10"` **is a single token** (id 702); digits 0–9 are ids 15–24; `" 10"` is two tokens. So
  `expected_score` can cover 0–10 exactly with the runner's existing `digit_token_ids` (TASK constraint 5 is moot for gpt-oss).
- The chat template ends `…<|end|><|start|>assistant` — last token `assistant` (id 173781) — and injects **no** empty
  reasoning block; the model itself emits `<|channel|>analysis`. Capture position candidate for G3.
- The template prepends a system message containing `Current date: 2026-09-10` and `Reasoning: medium`.
  **The templated prompt therefore changes with the calendar day**; the runner does not pin it. Flag for G3/G4.
Recompute: `jq '.model.tokenizer | {digit_tokens, chat_template_preview}' results/raw/local-monitor-activations/g1_env_20260910T070739Z.json`

### G1.6 attention backend (added — it gates G2's KV/memory decision)
`GptOssPreTrainedModel._supports_sdpa = False`, `_supports_flash_attn = True` (no flash_attn installed;
FA2 has no sink support, FA3 is Hopper-only), `_supports_flex_attn = True`.
- **eager**: materialises `[64, L, L]` scores per layer → 80 GB at L = 25k (median prompt). Unusable beyond a few k tokens.
- **flex_attention**: default compile raises an inductor error on this torch/GPU at q_len = 79 (decode tile sizes
  `BLOCK_M=1024` not dividing sparse block 128); forward works with `kernel_options={'fwd_BLOCK_M':32,'fwd_BLOCK_N':64}`
  (or `BLOCK_M/N=64`) but `generate()` rejects the `kernel_options` kwarg, so no decode path. Dead end as shipped.
- **chunked_eager** (`chunked_attention.py`, registered via `AttentionInterface`): eager's exact formula
  (bf16 QKᵀ, additive causal/sliding mask, sink column appended before softmax in fp32, dropped after) over query
  chunks; sliding layers only see their 128-key band. Greedy generation on the 79-token prompt is identical to eager.
  Synthetic random-token prefill, batch 1, `logits_to_keep=1`, model resident (12.83 GiB):

| prompt tokens | seconds | peak GiB (incl. model) |
|---|---|---|
| 4,096 | 1.7 | 16.68 |
| 16,384 | 8.5 | 17.63 (18.38 with 16 decode steps) |
| 32,768 | 27.6 | 18.90 |
| 65,536 | 108.4 | 21.43 |
| 98,304 | 270.9 | 24.24 |
| 131,072 | **OOM** | 22.02 GiB allocated + 6.24 GiB reserved-but-unallocated (fragmentation) when a 3.52 GiB block was requested; retried with `expandable_segments` in probe 2: **fits with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`: 512.9 s, peak 28.04 GiB, reserved 28.83 GiB** (`jq '.prefill_expandable_segments' results/raw/local-monitor-activations/g1_attn_probe2_20260910T074025Z.json`) |

Time is quadratic in length (full-attention layers); a 65k prompt is ~2 min of prefill alone.
Recompute: `jq '.chunked_eager.prefill' results/raw/local-monitor-activations/g1_attn_probe_20260910T071901Z.json`;
flex: `jq '.flex | map_values(keys)' …` (the error strings are in the file).

**Numerics vs eager** (all logits, all positions; noise floor = eager run twice; `g1_attn_probe2`):
| prompt | run vs eager_1 | max abs Δlogit | mean | p99 | last-pos max | argmax agreement | positions with max Δ>1 |
|---|---|---|---|---|---|---|---|
| chat79 | eager_2 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0/79 |
| chat79 | chunked_single_1 | 4.9375 | 0.16694 | 1.2031 | 0.9375 | 0.9747 | 26/79 |
| chat79 | chunked_single_2 | 4.9375 | 0.16694 | 1.2031 | 0.9375 | 0.9747 | 26/79 |
| chat79 | chunked_multi | 4.9375 | 0.16694 | 1.2031 | 0.9375 | 0.9747 | 26/79 |
| chat79 | flex_fwd32_64 | 8.4648 | 0.25863 | 1.9688 | 3.25 | 0.9241 | 38/79 |
| chat79 | chunked_multi vs chunked_single_1 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0/79 |
| rand2048 | eager_2 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0/2048 |
| rand2048 | chunked_single_1 | 1.4824 | 0.01472 | 0.1094 | 0.0547 | 0.9927 | 2/2048 |
| rand2048 | chunked_single_2 | 1.4824 | 0.01472 | 0.1094 | 0.0547 | 0.9927 | 2/2048 |
| rand2048 | chunked_multi | 1.4688 | 0.01459 | 0.1094 | 0.0469 | 0.9951 | 1/2048 |
| rand2048 | flex_fwd32_64 | 1.4062 | 0.01597 | 0.1094 | 0.0625 | 0.9912 | 1/2048 |
| rand2048 | chunked_multi vs chunked_single_1 | 1.4902 | 0.01256 | 0.1017 | 0.0625 | 0.9946 | 2/2048 |

Eager is bit-deterministic run to run (Δ = 0), so the noise floor is zero: these differences are real and need a cause. The function-level test (`g1_attn_unit.py`, random q/k/v in gpt-oss shapes, prefill 79/2048/4096 with and without the 128-token window, decode q=1, chunk sizes down to 16 tokens, each against an fp64 evaluation of the same formula) finds it:
- with **fp32 sinks**, `chunked_eager` is **bitwise equal** to transformers' `eager_attention_forward` whenever there is one chunk (79 tokens, both decode cases) and within **1 bf16 ulp (0.00195) on < 2e-6 of elements** when there are 128–256 chunks — the sliding-window band slicing and the mask are the same math;
- with **bf16 sinks — which is what the loaded model has** (`self_attn.sinks` is BF16 in the checkpoint; the 6.6 M fp32 params in `parameter_numel_by_dtype` are exactly the expert biases) — eager concatenates bf16 scores with bf16 sinks and runs `softmax` in **bf16**, while `chunked_eager` (and flex, via fp32 LSE) run it in fp32. Then chunked-vs-eager is up to 0.0156 per element, and chunked's mean error against fp64 is consistently the smaller of the two (e.g. 0.000637 vs 0.000700 at 79 tokens; every bf16 row).

So the model-level Δ above is eager's bf16 softmax, not a chunking or masking bug, and on natural text (chat79: mean |Δlogit| 0.17, 26/79 positions with max Δ > 1, 2 argmax flips) it is larger than on random tokens because the logits are peakier and a few MoE top-4 routings flip. The 79-token row `chunked_multi vs chunked_single` is 0 only because 79 tokens is one chunk either way; the 2048-token rows exercise the multi-chunk path. Whether Δ of this size moves a monitor *score* is a G4 question (compare scores, not logits).

| unit case (bf16 sinks) | eager vs fp64 mean | chunked vs fp64 mean | chunked vs eager max |
|---|---|---|---|
| prefill 79 | 0.000700 | 0.000637 | 0.0156 |
| prefill 2048, 128 chunks | 0.000245 | 0.000213 | 0.0156 |
| prefill 4096 sw128, 256 chunks | 0.000469 | 0.000418 | 0.0156 |
| decode q=1, k=300 | 0.000325 | 0.000290 | 0.0020 |

Recompute: `jq '.cases | map_values({sinks_dtype, e: .eager_vs_ref64.mean_abs, c: .chunked_vs_ref64.mean_abs, ce: .chunked_vs_eager.max_abs, bit: .chunked_eager_bitwise_equal})' results/raw/local-monitor-activations/g1_attn_unit_20260910T075628Z.json`
Recompute: `jq '.results' results/raw/local-monitor-activations/g1_attn_probe2_20260910T074025Z.json`

**Not done at G1 (needs your call, see "Open questions").** The runner (`run_monitor.py`) lives under
`experiments/logit-curve-replication/gpu/`, outside this branch's namespace, so the attention patch has not
been wired into it.

**What I checked myself.**
- Read the expert tensor dtypes off the loaded module (not the config) for three layers; read `dequantize` off the quantizer object.
- Recomputed the lean fingerprints from the payloads with the formula ported in `recon.py`, and reproduced the honest
  monitor-data mismatch by hand with `mt` overridden.
- Read the 8 last template tokens as decoded strings; confirmed the last one is `assistant`, not a reasoning marker.
- Confirmed `flex_attention` fails in `generate` in three configurations before writing the chunked path.
- Traced the chunked-vs-eager logit gap to eager's bf16 softmax by reading the sink dtype off the safetensors header and reproducing the gap at the function level with bf16 vs fp32 sinks.

**Alternative explanations considered.**
1. *MXFP4 not actually used (silent bf16 fallback).* Ruled out by three independent readings: quantizer
   `dequantize=False`, FP4-typed expert tensors on the module, 12.83 GiB resident (bf16 would be ~40 GB and
   cannot fit). Not ruled out: that the sm_120 triton MXFP4 kernels are numerically faithful — one sensible
   generation is not a test of that; G4's score sanity check against the cached monitor is the first real one.
2. *Mirror payloads differ from what the laptop used.* The fingerprint covers trajectory ids, action counts,
   success counts and the sus-score sum — not tool-output bytes. The L1 raw file has no payload sha256s, so
   byte identity with the laptop's copies cannot be checked from git; the reviewer can compare
   `sha256sum checkpoints/logit-curve-replication/api/*.json` on the laptop with `.mirror.payloads[].sha256`.
3. *chunked_eager is wrong rather than merely different.* Ruled out at the function level: bitwise equal to eager with fp32
   sinks, 1-ulp with many chunks, closer to fp64 than eager with the model's bf16 sinks. What remains open is a *choice*:
   eager-as-shipped softmaxes in bf16, chunked in fp32 — see open question 3b.
4. *The 1,626 placeholder prompts, the 17,234 vs 12,494 pool gap, the capture position, truncation.* Not
   touched at G1; all carried forward unchanged. The payloads hold 12,675 + 5,097 = 17,772 actions, of which
   the manifest lists 17,234 as scorable.

**Status.** `[tested]` for every environment fact; G2+ `blocked` on the export files.

### Open questions for you (not my call)
1. **Export files.** Copy `data_export/data/{honest,attack,trajectories}.jsonl` from the laptop to
   `checkpoints/local-monitor-activations/data/export/` (61 MB; `scp`/`runpodctl`)? Or ship the 16 GB HF dump and
   re-run `recon.py` + `export.py` here? G2 cannot start before this.
2. **Attention backend.** I propose running G2–G5 with `chunked_eager`. It needs a runner that registers it:
   either a thin `experiments/local-monitor-activations/run_monitor.py` that imports track L's modules and adds
   `--attn chunked_eager`, or a change to track L's file on its own branch. Which?
3a. **Template date.** Pin `Current date` in the harmony system prompt (e.g. to the run's start date) so the 17,234
   prompts are byte-stable across days, or leave it and record it per action?
3b. **Softmax precision.** `chunked_eager` keeps the sink/softmax arithmetic in fp32 (as flex and the vLLM/FlashAttention
   kernels do); transformers' eager runs it in bf16 because the sinks load as bf16. I kept fp32 (closer to exact). Say if you want
   it to mimic eager bit-for-bit instead — it is a one-line cast.
4. **`kernels` in `gpu/requirements.txt`** — infra fix for track L / main.
5. **Jupyter MCP** returns `401 Password login failed` (the server on 8889 accepts the token via curl, so the MCP
   server's auth config is what is off). G1 did not need the kernel; G3 exploration would. Fall back to Route A?
6. Throughput hunch only, not a result: prefill alone is ~17 s at 25k tokens and ~2 min at 65k, before any
   reasoning tokens; the full 17,234-action set looks like days, not hours, on one 5090. G4 measures it.

---

## Verification (VERIFY.md)

Filled in by the review session, on this branch, before merge to main.

**Verdict.** Verified / Verified but weaker than stated / Not verifiable from what's here / Wrong

**What was recomputed.**

**Dumbest ways this could be wrong, and what rules each out.**

---

## Dead ends

- `flex_attention` for gpt-oss on torch 2.14.0+cu130 / sm_120 → inductor `LoweringException` at decode
  (q_len < 128) with default kernel options; works for forward with explicit `kernel_options`, but
  `generate()` refuses that kwarg → not usable for G4/G5 without patching transformers.
- `hf download openai/gpt-oss-20b` without `--include` pulled `original/` and `metal/` too (39 GB, not 13 GB).
