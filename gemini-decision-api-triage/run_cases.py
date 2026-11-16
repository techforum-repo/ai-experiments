"""Send the cases in cases.jsonl to the Gemini Decisions API and save the raw responses.

    python3 run_cases.py                         all groups, once
    python3 run_cases.py --runs 3                each case three times (stability, latency)
    python3 run_cases.py --groups formats        one group: formats, attachments, mixed, resolution
    python3 run_cases.py --only att-card         cases whose id contains this text
    python3 run_cases.py --out results/my-run    write into this folder (appends to responses.jsonl)

Needs GEMINI_API_KEY. Standard library only.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import decide

GROUPS = ["formats", "attachments", "mixed", "resolution"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--groups", default=",".join(GROUPS))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--only", help="run only cases whose id contains this text")
    ap.add_argument("--limit", type=int, help="first N cases after filtering")
    ap.add_argument("--out", help="results folder (default: results/<timestamp>)")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")

    groups = args.groups.split(",")
    cases = [c for c in decide.load_cases() if c["group"] in groups]
    if args.only:
        cases = [c for c in cases if args.only in c["id"]]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        sys.exit("No cases match.")

    out = Path(args.out or decide.HERE / "results" / dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"model": decide.MODEL, "endpoint": decide.URL, "price_per_m": decide.PRICE_PER_M,
                 "cases_started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "groups": groups, "runs": args.runs, "cases": len(cases)})
    meta_path.write_text(json.dumps(meta, indent=2))

    pacer = decide.Pacer()
    total = len(cases) * args.runs
    done = errors = 0
    with open(out / "responses.jsonl", "a") as f:
        for run in range(1, args.runs + 1):
            for case in cases:
                body = decide.build_request(case)
                est = decide.estimate_tokens(case, len(body["questions"]))
                r = decide.decide(body, key, pacer, est)
                record = {"case": case["id"], "group": case["group"], "run": run,
                          "questions": list(body["questions"]), **r}
                f.write(json.dumps(record) + "\n")
                f.flush()
                done += 1
                if r["status"] == "ok":
                    tokens = r["usage"].get("total_input_tokens", "?")
                    extra = ""
                    if "category" in r["answers"] and "enough" in r["answers"]:
                        extra = "  " + decide.route(r["answers"])[0]
                    print(f"[{done}/{total}] {case['id']:<34} {r['latency_ms']:>7.0f} ms  {tokens:>6} tok{extra}")
                else:
                    errors += 1
                    print(f"[{done}/{total}] {case['id']:<34} ERROR {r['http_status']}: "
                          f"{json.dumps(r.get('error'))[:200]}")

    meta = json.loads(meta_path.read_text())
    meta["cases_finished"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"\n{done} requests, {errors} errors. Raw responses: {out / 'responses.jsonl'}")
    print(out)


if __name__ == "__main__":
    main()
