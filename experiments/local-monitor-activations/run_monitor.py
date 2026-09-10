#!/usr/bin/env python3
"""Track G runner: gpt-oss-20b live monitor, forced-final scoring, residual-stream capture at four positions.

Per (traj_id, action_idx) in --subset, in --render mode:
  1. render the user text with monitor_prompt.render_user_text (original is sha256-checked against the
     manifest), apply the pinned harmony template (date + reasoning effort are literals, asserted);
  2. ONE prefill forward pass (chunked_eager attention, fixed --attn-chunk-size, logits_to_keep=1) with
     forward hooks on the embedding output and every decoder layer; the residual stream at the four
     capture positions (transcript_end, action_end, instruction_end, final) is kept as fp16
     [4, n_layers+1, d_model] — layer 0 = embedding output, layer i = output of decoder layer i-1;
  3. forced final: feed `<|channel|>final<|message|>` on the cache and read the next-token distribution
     ("after_message"; this is what TASK-ver2 specifies), then feed `<score>\n` and read it again
     ("after_score_tag": the position where the template's format puts the digit). At both positions the
     mass on the digit tokens 0..9 and "10" (single token, id 702), the renormalised E[score], the argmax
     digit and the top-10 tokens are recorded. `score` / `expected_score` / `digit_token_mass` in the
     record are the after_score_tag reading; the after_message reading is kept alongside.
     No reasoning tokens are generated.
  4. append the record to <out>/scores.jsonl; activations are buffered and flushed to
     <out>/acts_XXXX.pt (dict key "traj_id|action_idx|render" -> tensor) every --checkpoint-every actions
     with <out>/acts_index.json; on restart, keys already in the index are skipped.

Usage:
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HOME=/workspace/hf \
  python experiments/local-monitor-activations/run_monitor.py --attn chunked_eager --attn-chunk-size 256 \
      --max-prompt-tokens 32000 --render original --reasoning-effort low --template-date 2026-09-10 \
      --subset experiments/local-monitor-activations/subset_main.json --out checkpoints/local-monitor-activations/out/main
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve()
SLUG = HERE.parent.name
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import chunked_attention  # noqa: E402
import monitor_prompt as mp  # noqa: E402

FORCED_FINAL = "<|channel|>final<|message|>"
SCORE_TAG = "<score>\n"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


class PositionCapture:
    """Forward hooks on embed_tokens + every decoder layer; keeps output[0, positions, :] of the prefill."""

    def __init__(self, embed: torch.nn.Module, layers: list[torch.nn.Module]):
        self.n = len(layers) + 1
        self.buf: list[torch.Tensor | None] = [None] * self.n
        self.positions: torch.Tensor | None = None
        self.handles = [embed.register_forward_hook(self._hook(0))] + \
                       [layer.register_forward_hook(self._hook(i + 1)) for i, layer in enumerate(layers)]

    def _hook(self, i):
        def fn(module, inputs, output):
            if self.positions is None:
                return
            out = output[0] if isinstance(output, (tuple, list)) else output
            if out.dim() == 3 and out.shape[1] > 1:                 # prefill only, not the forced-final steps
                self.buf[i] = out[0, self.positions, :].detach().to(torch.float16).cpu()
        return fn

    def arm(self, positions: list[int]):
        self.buf = [None] * self.n
        self.positions = torch.tensor(positions)

    def take(self) -> torch.Tensor:
        self.positions = None
        assert all(b is not None for b in self.buf), "a layer did not fire during prefill"
        return torch.stack(self.buf, dim=1).contiguous()           # [n_positions, n_layers+1, d_model] fp16


def digit_ids(tok) -> dict[int, int]:
    out = {}
    for v in range(11):
        enc = tok.encode(str(v), add_special_tokens=False)
        assert len(enc) == 1, (v, enc)
        out[v] = enc[0]
    return out


def read_distribution(tok, logits: torch.Tensor, digits: dict[int, int]) -> dict:
    probs = torch.softmax(logits.float(), dim=-1)
    top = torch.topk(probs, 10)
    dist = {str(v): float(probs[i]) for v, i in digits.items()}
    mass = sum(dist.values())
    argmax_digit = max(dist, key=dist.get)
    return {"digit_token_mass": mass,
            "expected_score": (sum(int(v) * p for v, p in dist.items()) / mass) if mass > 0 else None,
            "argmax_digit": int(argmax_digit), "argmax_digit_p": dist[argmax_digit],
            "digit_dist": dist,
            "top10": [{"id": int(i), "token": tok.decode([int(i)]), "p": float(p)} for p, i in zip(top.values, top.indices)],
            "argmax_is_digit": int(top.indices[0]) in digits.values()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--attn", default="chunked_eager", choices=["chunked_eager", "eager"])
    ap.add_argument("--attn-chunk-size", type=int, required=True)
    ap.add_argument("--max-prompt-tokens", type=int, required=True)
    ap.add_argument("--render", default="original", choices=list(mp.RENDERS))
    ap.add_argument("--reasoning-effort", default="low")
    ap.add_argument("--template-date", required=True)
    ap.add_argument("--subset", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--checkpoint-every", type=int, default=25)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--order", default="ascending", choices=["ascending", "subset"], help="ascending n_tokens or the subset file's order")
    ap.add_argument("--dry-run", action="store_true", help="render + tokenize only, no model")
    args = ap.parse_args()
    assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "").startswith("expandable_segments") or args.dry_run, \
        "set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True (G1: fragmentation OOM without it)"

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = mp.load_manifest()
    files = mp.verify_export_files(manifest)
    assert all(v["match"] for v in files.values()), files
    trajs, tmpl_sha = mp.load_trajs()
    assert tmpl_sha == manifest["prompt_template_sha256"]
    template = mp.fmp.load_template()
    man_actions = {(a["traj_id"], a["action_idx"]): a for a in manifest["actions"]}
    traj_len = {}
    for (t, _i) in man_actions:
        traj_len[t] = traj_len.get(t, 0) + 1
    tmeta = {}
    with (mp.EXPORT_DIR / "trajectories.jsonl").open() as f:
        for line in f:
            t = json.loads(line); tmeta[t["traj_id"]] = t

    subset = json.loads(args.subset.read_text())
    todo = list(subset["actions"])
    if args.order == "ascending":
        todo.sort(key=lambda a: (a["n_tokens"], a["traj_id"], a["action_idx"]))
    if args.limit:
        todo = todo[: args.limit]

    # ── resume ─────────────────────────────────────────────────────────────
    index_path = args.out / "acts_index.json"
    acts_index = json.loads(index_path.read_text()) if index_path.exists() else {"shards": {}, "position_order": list(mp.POSITIONS)}
    done = {k for keys in acts_index["shards"].values() for k in keys}
    key_of = lambda a: f"{a['traj_id']}|{a['action_idx']}|{args.render}"  # noqa: E731
    todo = [a for a in todo if key_of(a) not in done]
    print(f"{len(todo)} actions to do ({len(done)} already in {args.out}); render={args.render}", flush=True)

    # ── tokenizer + model ──────────────────────────────────────────────────
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import transformers
    tok = AutoTokenizer.from_pretrained(mp.MODEL_ID)
    pinned_sha = mp.pin_chat_template(tok, args.template_date)
    digits = digit_ids(tok)
    forced_ids = tok.encode(FORCED_FINAL, add_special_tokens=False)
    score_tag_ids = tok.encode(SCORE_TAG, add_special_tokens=False)
    assert tok.decode(forced_ids) == FORCED_FINAL and tok.decode(score_tag_ids) == SCORE_TAG
    model = None
    if not args.dry_run:
        chunked_attention.CHUNK_SIZE = args.attn_chunk_size
        chunked_attention.register()
        t0 = time.time()
        model = AutoModelForCausalLM.from_pretrained(mp.MODEL_ID, dtype=torch.bfloat16, device_map={"": 0},
                                                     attn_implementation=args.attn).eval()
        load_s = time.time() - t0
        assert model.config._attn_implementation == args.attn, model.config._attn_implementation
        assert getattr(model.hf_quantizer, "quantization_config", None) is not None and not model.hf_quantizer.quantization_config.dequantize
        layers = list(model.model.layers)
        capture = PositionCapture(model.model.embed_tokens, layers)
        model_gib = torch.cuda.memory_allocated() / 2**30
        print(f"model loaded in {load_s:.1f}s, {model_gib:.2f} GiB resident, attn={model.config._attn_implementation}, chunk={args.attn_chunk_size}", flush=True)
    meta = {"model_id": mp.MODEL_ID, "dtype": "bfloat16", "quantization": "mxfp4 (native, kernels)", "attn_impl": args.attn,
            "attn_chunk_size": args.attn_chunk_size, "softmax_dtype": "float32", "reasoning_effort": args.reasoning_effort,
            "template_date": args.template_date, "pinned_chat_template_sha256": pinned_sha, "prompt_template_sha256": tmpl_sha,
            "max_prompt_tokens": args.max_prompt_tokens, "render": args.render, "subset": str(args.subset), "order": args.order,
            "forced_final": FORCED_FINAL, "forced_final_ids": forced_ids, "score_tag": SCORE_TAG, "score_tag_ids": score_tag_ids,
            "digit_token_ids": {str(k): v for k, v in digits.items()}, "position_order": list(mp.POSITIONS),
            "activation_spec": "fp16 [n_positions=4, n_layers+1=25, d_model=2880]; index 0 along axis 1 is the embedding output, index i is the output of decoder layer i-1; positions in position_order; taken from the single prefill pass",
            "transformers": transformers.__version__, "torch": torch.__version__, "git_commit": git_commit(),
            "manifest_git_commit": manifest.get("git_commit"), "started": dt.datetime.now(dt.timezone.utc).isoformat(),
            "cuda_alloc_conf": os.environ.get("PYTORCH_CUDA_ALLOC_CONF"), "n_layers": 24, "d_model": 2880}
    (args.out / "run_meta.json").write_text(json.dumps(meta, indent=1))

    scores_f = (args.out / "scores.jsonl").open("a")
    buf: dict[str, torch.Tensor] = {}
    shard_no = len(acts_index["shards"])

    def flush():
        nonlocal shard_no, buf
        if not buf:
            return
        p = args.out / f"acts_{shard_no:04d}.pt"
        torch.save(buf, p)
        acts_index["shards"][p.name] = list(buf.keys())
        index_path.write_text(json.dumps(acts_index))
        scores_f.flush(); os.fsync(scores_f.fileno())
        print(f"  checkpoint: {p.name} ({len(buf)} actions, {p.stat().st_size / 2**20:.1f} MiB)", flush=True)
        shard_no += 1
        buf = {}

    t_run = time.time()
    n_ok = n_skip = n_fail = 0
    for n_done, a in enumerate(todo, 1):
        key = key_of(a)
        t = trajs[a["traj_id"]]
        m = man_actions[(a["traj_id"], a["action_idx"])]
        action = t["actions"][a["action_idx"]]
        t0 = time.time()
        r = mp.render_user_text(t, a["action_idx"], args.render, template)
        user_sha = hashlib.sha256(r["text"].encode()).hexdigest()
        s = mp.apply_template(tok, r["text"], args.template_date, args.reasoning_effort)
        tp = mp.tokenize_with_positions(tok, s, r["text"], r)
        ids = tp["input_ids"]
        rec = {"traj_id": a["traj_id"], "action_idx": a["action_idx"], "side": m["side"], "env": m["env"],
               "side_task": tmeta[a["traj_id"]]["side_task"], "side_task_category": tmeta[a["traj_id"]]["side_task_category"],
               "render": args.render, "counterfactual_stratum": a.get("counterfactual_stratum"),
               "prompt_sha256": user_sha, "prompt_sha256_matches_manifest": user_sha == m["prompt_sha256"],
               "has_attachment_placeholder": mp.has_attachment_placeholder(r["text"]),
               "n_prompt_tokens": len(ids), "n_prompt_chars": len(s), "cached_scores": m["cached_scores"], "cached_mean": m["cached_mean"],
               "step_index": a["action_idx"], "trajectory_length": traj_len[a["traj_id"]],
               "position_in_trajectory": a["action_idx"] / max(1, traj_len[a["traj_id"]] - 1),
               "n_context_tokens": tp["n_context_tokens"], "tool": m["tool"], **mp.action_features(action),
               "neutralize_events": r["subs"],
               "capture_positions": mp.decode_positions(tok, ids, tp["positions"]),
               "attn_impl": args.attn, "attn_chunk_size": args.attn_chunk_size, "softmax_dtype": "float32",
               "reasoning_effort": args.reasoning_effort, "template_date": args.template_date,
               "max_prompt_tokens": args.max_prompt_tokens, "git_commit": meta["git_commit"]}
        if args.render == "original":
            assert rec["prompt_sha256_matches_manifest"], key
        if len(ids) > args.max_prompt_tokens:
            rec.update({"status": "skipped", "reason": f"n_prompt_tokens {len(ids)} > max_prompt_tokens {args.max_prompt_tokens}",
                        "score": None, "expected_score": None, "digit_token_mass": None, "seconds": time.time() - t0})
            n_skip += 1
            scores_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[{n_done}/{len(todo)}] SKIP {key} {len(ids)} tokens", flush=True)
            continue
        if args.dry_run:
            rec.update({"status": "dry_run", "seconds": time.time() - t0})
            scores_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[{n_done}/{len(todo)}] dry {key} {len(ids)} tok  {[p['decoded'] for p in rec['capture_positions']]}", flush=True)
            continue
        try:
            torch.cuda.reset_peak_memory_stats()
            x = torch.tensor([ids], device=model.device)
            positions = [tp["positions"][k] for k in mp.POSITIONS]
            capture.arm(positions)
            with torch.no_grad():
                torch.cuda.synchronize(); t1 = time.time()
                out = model(x, use_cache=True, logits_to_keep=1)
                torch.cuda.synchronize(); prefill_s = time.time() - t1
                acts = capture.take()
                pkv = out.past_key_values
                # forced final channel
                L = len(ids)
                cp2 = torch.arange(L, L + len(forced_ids), device=model.device)
                o2 = model(torch.tensor([forced_ids], device=model.device), past_key_values=pkv, use_cache=True, logits_to_keep=1,
                           cache_position=cp2, position_ids=cp2[None])
                after_message = read_distribution(tok, o2.logits[0, -1], digits)
                cp3 = torch.arange(L + len(forced_ids), L + len(forced_ids) + len(score_tag_ids), device=model.device)
                o3 = model(torch.tensor([score_tag_ids], device=model.device), past_key_values=o2.past_key_values, use_cache=True, logits_to_keep=1,
                           cache_position=cp3, position_ids=cp3[None])
                after_score_tag = read_distribution(tok, o3.logits[0, -1], digits)
                torch.cuda.synchronize()
            assert acts.shape == (4, 25, 2880) and acts.dtype == torch.float16, acts.shape
            finite = bool(torch.isfinite(acts).all())
            rec.update({"status": "ok", "score": after_score_tag["argmax_digit"], "expected_score": after_score_tag["expected_score"],
                        "digit_token_mass": after_score_tag["digit_token_mass"], "after_score_tag": after_score_tag,
                        "after_message": after_message, "acts_finite": finite,
                        "acts_norm_final_last_layer": float(acts[3, -1].float().norm()),
                        "prefill_seconds": prefill_s, "seconds": time.time() - t0,
                        "peak_gib": torch.cuda.max_memory_allocated() / 2**30,
                        "acts_bytes": acts.numel() * 2})
            buf[key] = acts
            n_ok += 1
            del out, o2, o3, pkv, x
        except torch.cuda.OutOfMemoryError as e:
            rec.update({"status": "failed", "reason": "OOM: " + str(e)[:200], "score": None, "expected_score": None, "digit_token_mass": None,
                        "seconds": time.time() - t0})
            n_fail += 1
            capture.positions = None
            torch.cuda.empty_cache()
        scores_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{n_done}/{len(todo)}] {rec['status']:6s} {m['side']:6s} {a['traj_id'][:8]}#{a['action_idx']:<3d} {len(ids):>6d} tok "
              f"score {rec['score']} E {rec['expected_score'] if rec['expected_score'] is None else round(rec['expected_score'], 2)} "
              f"mass {rec['digit_token_mass'] if rec['digit_token_mass'] is None else round(rec['digit_token_mass'], 3)} "
              f"(cached {m['cached_mean']}) {rec['seconds']:.1f}s peak {rec.get('peak_gib', 0):.1f}G", flush=True)
        if n_done % args.checkpoint_every == 0:
            flush()
    flush()
    scores_f.close()
    meta.update({"finished": dt.datetime.now(dt.timezone.utc).isoformat(), "n_ok": n_ok, "n_skipped": n_skip, "n_failed": n_fail,
                 "seconds_this_run": time.time() - t_run})
    (args.out / "run_meta.json").write_text(json.dumps(meta, indent=1))
    print(f"done: ok {n_ok}, skipped {n_skip}, failed {n_fail} in {time.time() - t_run:.0f}s -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
