"""How do latency, tokens, cost and answers change as one request asks more questions?

Every request carries the same shared input: the all-formats case (text, an image, an
audio voicemail, a PDF invoice and a screen recording). Only the number of questions changes:

    1     category
    10    the 7 triage questions + 3 yes/no fact checks
    100   the 7 triage questions + 93 fact checks
    1000  the 7 triage questions + 993 fact checks

The fact checks (scale_questions.json) ask whether a value appears in the input, e.g.
"Is order number 55102 mentioned anywhere in the input?". 11 are true; the rest are false,
and some of those are near misses (55102 for 55120, the street number instead of the
house number on the delivery photo). That gives every size a ground truth.

    python3 scale.py                    sizes 1, 10, 100, 1000, once each
    python3 scale.py --runs 3           three times each, in shuffled order
    python3 scale.py --sizes 1,50,500   other sizes (max 1000)
    python3 scale.py --out results/X    write into an existing results folder

Needs GEMINI_API_KEY. Standard library only.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
from pathlib import Path

import decide

TRIAGE = ["category", "urgent", "impact", "enough", "sensitive", "conflict", "wrong_address"]


def questions_for(size, facts):
    """Question map for one request size, plus the fact ground truth used in it."""
    if size <= len(TRIAGE):  # 1 = category only; up to 7 = the first triage questions, no facts
        return {k: decide.QUESTIONS[k] for k in TRIAGE[:size]}, {}
    qs = {k: decide.QUESTIONS[k] for k in TRIAGE}
    n = size - len(qs)
    trues = [f for f in facts if f["label"]]
    falses = [f for f in facts if not f["label"]]
    hard = [f for f in falses if f["hard"]]
    easy = [f for f in falses if not f["hard"]]
    n_true = min(len(trues), max(1, round(n * 0.3)) if n < 40 else len(trues))
    n_hard = min(len(hard), max(1, round(n * 0.3)) if n < 150 else len(hard))
    chosen = trues[:n_true] + hard[:n_hard]
    chosen += easy[:max(0, n - len(chosen))]
    chosen = chosen[:n]
    truth = {}
    for i, f in enumerate(chosen, 1):
        key = f"fact_{i:03d}"
        qs[key] = {"type": "noul", "instructions": f["instructions"]}
        truth[key] = {"label": f["label"], "hard": f["hard"], "kind": f["kind"], "value": f["value"]}
    return qs, truth


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default="1,10,100,1000")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out", help="results folder (default: results/<timestamp>)")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    sizes = [int(s) for s in args.sizes.split(",")]
    if any(s < 1 or s > 1000 for s in sizes):
        sys.exit("Sizes must be between 1 and 1000.")

    spec = json.loads((decide.HERE / "scale_questions.json").read_text())
    case = next(c for c in decide.load_cases() if c["id"] == spec["case"])

    out = Path(args.out or decide.HERE / "results" / dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"model": decide.MODEL, "endpoint": decide.URL, "price_per_m": decide.PRICE_PER_M,
                 "scale_started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "scale_case": case["id"], "scale_sizes": sizes, "scale_runs": args.runs})
    meta_path.write_text(json.dumps(meta, indent=2))

    pacer = decide.Pacer()
    order = [(run, s) for run in range(1, args.runs + 1) for s in sizes]
    rnd = random.Random(1)
    if args.runs > 1:  # so a warm-up effect doesn't always land on the same size
        rnd.shuffle(order)
    with open(out / "scale.jsonl", "a") as f:
        for i, (run, size) in enumerate(order, 1):
            qs, truth = questions_for(size, spec["facts"])
            body = decide.build_request(case)
            body["questions"] = qs
            est = decide.estimate_tokens(case, len(qs))
            r = decide.decide(body, key, pacer, est)
            f.write(json.dumps({"case": case["id"], "size": size, "run": run, "n_questions": len(qs),
                                "truth": truth, **r}) + "\n")
            f.flush()
            if r["status"] == "ok":
                print(f"[{i}/{len(order)}] {size:>5} questions  {r['latency_ms']:>7.0f} ms  "
                      f"{r['usage'].get('total_input_tokens', '?'):>6} tok")
            else:
                print(f"[{i}/{len(order)}] {size:>5} questions  ERROR {r['http_status']}: "
                      f"{json.dumps(r.get('error'))[:200]}")

    meta = json.loads(meta_path.read_text())
    meta["scale_finished"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(out)


if __name__ == "__main__":
    main()
