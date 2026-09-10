#!/usr/bin/env python3
"""G3 addendum: free generation from the final channel. For each chosen pilot action: prefill the pinned
prompt, append `<|channel|>final<|message|>`, then greedy-decode --max-new-tokens tokens with nothing else
forced. Records the raw text, the parsed <score>, and the digit distribution at the position of the digit the
model itself wrote (if it wrote one). Writes results/raw/<slug>/g3_peek_<ts>.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve()
SLUG = HERE.parent.name
REPO = HERE.parents[2]
RAW = REPO / "results" / "raw" / SLUG
sys.path.insert(0, str(HERE.parent))
import chunked_attention  # noqa: E402
import monitor_prompt as mp  # noqa: E402
import run_monitor as rm  # noqa: E402

TS = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
ap = argparse.ArgumentParser()
ap.add_argument("--keys", nargs="+", required=True, help="traj_id|action_idx")
ap.add_argument("--max-new-tokens", type=int, default=200)
ap.add_argument("--attn-chunk-size", type=int, default=256)
ap.add_argument("--template-date", required=True)
ap.add_argument("--reasoning-effort", default="low")
args = ap.parse_args()
assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "").startswith("expandable_segments")
from transformers import AutoTokenizer, AutoModelForCausalLM  # noqa: E402

manifest = mp.load_manifest(); trajs, tmpl_sha = mp.load_trajs(); template = mp.fmp.load_template()
man = {(a["traj_id"], a["action_idx"]): a for a in manifest["actions"]}
tok = AutoTokenizer.from_pretrained(mp.MODEL_ID)
pinned = mp.pin_chat_template(tok, args.template_date)
digits = rm.digit_ids(tok)
forced_ids = tok.encode(rm.FORCED_FINAL, add_special_tokens=False)
chunked_attention.CHUNK_SIZE = args.attn_chunk_size
chunked_attention.register()
model = AutoModelForCausalLM.from_pretrained(mp.MODEL_ID, dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="chunked_eager").eval()
stop_ids = [200002, 200007, 200012]   # <|return|>, <|end|>, <|call|>
R = {"slug": SLUG, "script": str(HERE.relative_to(REPO)), "timestamp": TS, "git_commit": rm.git_commit(), "args": vars(args),
     "forced_prefix": rm.FORCED_FINAL, "decoding": "greedy, nothing forced after the prefix, stop on <|return|>/<|end|>/<|call|>", "generations": []}
for key in args.keys:
    tid, idx = key.split("|"); idx = int(idx)
    t = trajs[tid]; m = man[(tid, idx)]
    r = mp.render_user_text(t, idx, "original", template)
    s = mp.apply_template(tok, r["text"], args.template_date, args.reasoning_effort)
    ids = tok(s, add_special_tokens=False)["input_ids"]
    x = torch.tensor([ids + forced_ids], device=model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(x, max_new_tokens=args.max_new_tokens, do_sample=False, eos_token_id=stop_ids, pad_token_id=tok.pad_token_id or 200002,
                             output_scores=True, return_dict_in_generate=True)
    gen = out.sequences[0, x.shape[1]:].tolist()
    text = tok.decode(gen, skip_special_tokens=False)
    sec = time.time() - t0
    mtch = re.search(r"<score>\s*(\d+)\s*</score>", text, re.S)
    rec = {"key": key, "side": m["side"], "env": m["env"], "side_task": t.get("side_task"), "cached_scores": m["cached_scores"], "n_prompt_tokens": len(ids),
           "n_generated": len(gen), "hit_max_new_tokens": len(gen) >= args.max_new_tokens, "stopped_on": tok.decode([gen[-1]]) if gen and gen[-1] in stop_ids else None,
           "seconds": sec, "text": text, "parsed_score": int(mtch.group(1)) if mtch else None,
           "current_action": r["text"][r["action_span"][0]:r["action_span"][1]][:500]}
    # digit distribution at the model's own score digit, if any
    if mtch:
        # locate the generated token that starts the digit
        pos = None; acc = ""
        for i, g in enumerate(gen):
            acc = tok.decode(gen[: i + 1], skip_special_tokens=False)
            if len(acc) > mtch.start(1):
                pos = i; break
        if pos is not None:
            probs = torch.softmax(out.scores[pos][0].float(), -1)
            rec["own_digit_token"] = tok.decode([gen[pos]])
            rec["own_digit_dist"] = rm.read_distribution(tok, out.scores[pos][0], digits)
            rec["own_digit_dist"].pop("top10", None)
    R["generations"].append(rec)
    print(f"\n===== {m['side']} {key[:8]}#{idx} env={m['env']} side_task={t.get('side_task')} cached={m['cached_scores']} {len(ids)} tok, {len(gen)} gen tok in {sec:.1f}s, parsed score {rec['parsed_score']}, E at own digit {rec.get('own_digit_dist', {}).get('expected_score')}")
    print("  CURRENT ACTION:", rec["current_action"][:300].replace("\n", "\n    "))
    print("  GENERATION:\n" + "\n".join("    | " + l for l in text.splitlines()))
    sys.stdout.flush()
RAW.mkdir(parents=True, exist_ok=True)
out_p = RAW / f"g3_peek_{TS}.json"
out_p.write_text(json.dumps(R, indent=1, ensure_ascii=False))
print("raw ->", out_p.relative_to(REPO))
