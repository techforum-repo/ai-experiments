"""Run the 120 labelled messages against TypeSafe Jev and the OpenAI Decisions API.

Every message is sent once per run with all four questions, and once (on the
first run) with only the category question and its options in reverse order. Raw responses,
latency, and token usage are saved to results/<timestamp>/<provider>.jsonl,
then report.py turns them into results/<timestamp>/summary.json and report.md.

  python compare.py                      every provider with a key set
  python compare.py --providers jev      Jev only
  python compare.py --runs 3             repeat each message (stability)
  python compare.py --limit 10           first 10 messages, for a quick check

Keys: TYPESAFE_API_KEY for Jev, OPENAI_API_KEY for OpenAI. Standard library only.
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import decide  # noqa: E402
import report  # noqa: E402


def load_cases(limit=None):
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines() if line]
    return cases[:limit] if limit else cases


def run_case(provider, key, case, run, order_check):
    spec = decide.PROVIDERS[provider]
    row = {"id": case["id"], "run": run}
    try:
        raw, ms = decide.call(provider, spec["request"](case["text"]), key)
        row.update(ok=True, latency_ms=round(ms), model=raw.get("model"),
                   usage=raw.get("usage"), answers=spec["normalize"](raw), raw=raw)
    except Exception as e:  # recorded, never silently dropped
        row.update(ok=False, error=str(e))
        return row
    if order_check:
        try:
            raw, _ = decide.call(provider, spec["request"](case["text"], reverse_options=True), key)
            row["reversed"] = spec["normalize"](raw).get("category")
            row["reversed_usage"] = raw.get("usage")
        except Exception as e:
            row["reversed_error"] = str(e)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--providers", default="", help="comma-separated: jev,openai (default: all with keys)")
    p.add_argument("--runs", type=int, default=1, help="times to send each message")
    p.add_argument("--limit", type=int, help="only the first N messages")
    p.add_argument("--workers", type=int, default=4, help="parallel requests per provider")
    p.add_argument("--no-order-check", action="store_true", help="skip the reversed-options request")
    args = p.parse_args()

    wanted = [x for x in args.providers.split(",") if x] or list(decide.PROVIDERS)
    unknown = [x for x in wanted if x not in decide.PROVIDERS]
    if unknown:
        sys.exit(f"unknown provider: {', '.join(unknown)} (use {', '.join(decide.PROVIDERS)})")
    keys = {name: os.environ.get(decide.PROVIDERS[name]["key_env"]) for name in wanted}
    missing = [decide.PROVIDERS[n]["key_env"] for n in wanted if not keys[n]]
    if args.providers and missing:
        sys.exit(f"not set: {', '.join(missing)}")
    providers = [n for n in wanted if keys[n]]
    if not providers:
        sys.exit("No API key set. Add TYPESAFE_API_KEY (and optionally OPENAI_API_KEY) to .env.")
    for name in wanted:
        if not keys[name]:
            print(f"Skipping {name}: {decide.PROVIDERS[name]['key_env']} is not set.")

    cases = load_cases(args.limit)
    out_dir = HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)
    meta = {"started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "providers": providers, "runs": args.runs, "cases": len(cases),
            "order_check": not args.no_order_check,
            "models": {"jev": decide.JEV_MODEL, "openai": decide.OPENAI_MODEL}}

    for name in providers:
        print(f"\n== {name}: {len(cases)} messages x {args.runs} run(s)"
              + ("" if args.no_order_check else ", plus one reversed-options request each"))
        jobs = [(case, run) for run in range(args.runs) for case in cases]
        rows = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            # The reversed-options request runs once per message, on the first run only.
            futures = [pool.submit(run_case, name, keys[name], c, r, r == 0 and not args.no_order_check)
                       for c, r in jobs]
            for i, f in enumerate(futures, 1):
                rows.append(f.result())
                if i % 20 == 0 or i == len(futures):
                    errors = sum(not r["ok"] for r in rows)
                    print(f"  {i}/{len(futures)} done, {errors} errors")
        with (out_dir / f"{name}.jsonl").open("w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        bad = [r for r in rows if not r["ok"]]
        if bad:
            print(f"  first error: {bad[0]['error']}")

    meta["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print()
    report.main([str(out_dir)])


if __name__ == "__main__":
    sys.exit(main())
