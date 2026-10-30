"""Turn a results/<timestamp>/ folder from compare.py into numbers.

  python report.py                      the latest folder in results/
  python report.py results/20261030-101500

Writes summary.json and report.md into that folder and prints the report.
Every rate comes with its count and a 95% Wilson interval, because 120
messages is a small sample and a few points of difference can be noise.
"""
import json
import math
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import decide  # noqa: E402

# Price per million input tokens; output tokens are free on both APIs.
PRICE_PER_M = {"jev": float(os.environ.get("JEV_PRICE_PER_M", "0.042")),
               "openai": float(os.environ.get("OPENAI_PRICE_PER_M", "0.10"))}
THRESHOLDS = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0, centre - half), 3), round(min(1, centre + half), 3)]


def rate(k, n):
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None, "ci95": wilson(k, n)}


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def calibration(pairs, bins=5):
    """Expected calibration error for (stated probability, was it right) pairs."""
    table, ece = [], 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        inside = [(p, ok) for p, ok in pairs if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if not inside:
            continue
        mean_p = sum(p for p, _ in inside) / len(inside)
        acc = sum(ok for _, ok in inside) / len(inside)
        ece += len(inside) / len(pairs) * abs(mean_p - acc)
        table.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(inside),
                      "mean_probability": round(mean_p, 3), "accuracy": round(acc, 3)})
    return {"ece": round(ece, 3), "bins": table}


def summarize(rows, cases, provider):
    by_id = {c["id"]: c for c in cases}
    ok = [r for r in rows if r["ok"]]
    first = [r for r in ok if r["run"] == 0]
    s = {"requests": len(rows), "errors": len(rows) - len(ok),
         "error_samples": [r["error"] for r in rows if not r["ok"]][:3],
         "models": sorted({r.get("model") for r in ok if r.get("model")})}
    if not first:
        return s

    picks = []   # (case, choice, top probability, enough, urgent, impact)
    for r in first:
        a, c = r["answers"], by_id[r["id"]]
        if "category" not in a or a["category"].get("refusal"):
            picks.append((c, None, 0.0, r))
            continue
        choice, p = decide.top(a["category"])
        picks.append((c, choice, p, r))

    clear = [x for x in picks if x[0]["category"] != "unclear"]
    unclear = [x for x in picks if x[0]["category"] == "unclear"]
    s["category_accuracy"] = rate(sum(x[1] == x[0]["category"] for x in picks), len(picks))
    s["category_accuracy_clear"] = rate(sum(x[1] == x[0]["category"] for x in clear), len(clear))
    s["unclear_chosen"] = rate(sum(x[1] == "unclear" for x in unclear), len(unclear))
    s["accuracy_by_kind"] = {
        kind: rate(sum(x[1] == x[0]["category"] for x in picks if x[0]["kind"] == kind),
                   sum(x[0]["kind"] == kind for x in picks))
        for kind in sorted({x[0]["kind"] for x in picks})}
    s["confusions"] = sorted(
        ({"id": x[0]["id"], "text": x[0]["text"], "expected": x[0]["category"], "got": x[1],
          "p": round(x[2], 2)} for x in picks if x[1] != x[0]["category"]),
        key=lambda m: -m["p"])

    # The policy: what gets routed automatically, and how often that is right.
    def policy(threshold):
        routed = [x for x in picks if decide.route(x[3]["answers"], threshold)[0] == "route"]
        held_unclear = sum(decide.route(x[3]["answers"], threshold)[0] != "route" for x in unclear)
        return {"threshold": threshold,
                "coverage": rate(len(routed), len(picks)),
                "routed_correct": rate(sum(x[1] == x[0]["category"] for x in routed), len(routed)),
                "unclear_held_back": rate(held_unclear, len(unclear)),
                "wrong_routes": len(routed) - sum(x[1] == x[0]["category"] for x in routed),
                "without_enough": without_enough(threshold)}

    # The same policy with the enough question removed: category answer only.
    def without_enough(threshold):
        routed = [x for x in picks if x[1] not in (None, "unclear") and x[2] >= threshold]
        right = sum(x[1] == x[0]["category"] for x in routed)
        return {"coverage": rate(len(routed), len(picks)), "routed_correct": rate(right, len(routed)),
                "wrong_routes": len(routed) - right}
    s["policy"] = policy(decide.ROUTE_MIN)
    s["policy_curve"] = [policy(t) for t in THRESHOLDS]

    s["category_calibration"] = calibration([(x[2], x[1] == x[0]["category"]) for x in picks])
    enough_pairs = [(x[3]["answers"]["enough"]["probability"], x[0]["enough"])
                    for x in picks if "probability" in x[3]["answers"].get("enough", {})]
    s["enough"] = {
        "accuracy": rate(sum((p >= decide.ENOUGH_MIN) == y for p, y in enough_pairs), len(enough_pairs)),
        "brier": round(sum((p - y) ** 2 for p, y in enough_pairs) / len(enough_pairs), 3)
        if enough_pairs else None,
        "unclear_flagged": rate(sum(p < decide.ENOUGH_MIN for p, y in enough_pairs if not y),
                                sum(not y for _, y in enough_pairs))}
    urgent_pairs = [(x[3]["answers"]["urgent"]["probability"], x[0]["urgent"])
                    for x in picks if "probability" in x[3]["answers"].get("urgent", {})]
    s["urgent"] = {
        "accuracy": rate(sum((p >= decide.URGENT_MIN) == y for p, y in urgent_pairs), len(urgent_pairs)),
        "recall": rate(sum(p >= decide.URGENT_MIN for p, y in urgent_pairs if y),
                       sum(y for _, y in urgent_pairs)),
        "false_alarms": sum(p >= decide.URGENT_MIN for p, y in urgent_pairs if not y),
        "brier": round(sum((p - y) ** 2 for p, y in urgent_pairs) / len(urgent_pairs), 3)
        if urgent_pairs else None}
    impact = [(x[3]["answers"]["impact"]["score"], x[0]["impact"]) for x in picks
              if x[0]["impact"] is not None and "score" in x[3]["answers"].get("impact", {})]
    s["impact"] = {
        "n": len(impact),
        "mean_abs_error": round(sum(abs(sc - y) for sc, y in impact) / len(impact), 3) if impact else None,
        "nearest_level_correct": rate(sum(round(sc) == y for sc, y in impact), len(impact))}

    reversed_rows = [x for x in picks if x[3].get("reversed") and x[1]]
    if reversed_rows:
        same = sum(decide.top(x[3]["reversed"])[0] == x[1] for x in reversed_rows)
        shift = [abs(x[3]["reversed"]["probabilities"].get(x[1], 0) - x[2]) for x in reversed_rows]
        s["option_order"] = {"same_choice": rate(same, len(reversed_rows)),
                             "mean_probability_shift": round(statistics.mean(shift), 3),
                             "max_probability_shift": round(max(shift), 3)}

    runs = sorted({r["run"] for r in ok})
    if len(runs) > 1:
        by_case = {}
        for r in ok:
            if "category" in r["answers"] and not r["answers"]["category"].get("refusal"):
                by_case.setdefault(r["id"], []).append(r["answers"])
        stable = [len({decide.top(a["category"])[0] for a in v}) == 1 for v in by_case.values()]
        spread = [max(decide.top(a["category"])[1] for a in v) - min(decide.top(a["category"])[1] for a in v)
                  for v in by_case.values()]
        s["repeatability"] = {"runs": len(runs), "same_choice": rate(sum(stable), len(stable)),
                              "max_probability_spread": round(max(spread), 3)}

    lat = [r["latency_ms"] for r in ok]
    tokens = [r["usage"]["input_tokens"] for r in ok if r.get("usage")]
    s["latency_ms"] = {"p50": pct(lat, 0.5), "p95": pct(lat, 0.95), "max": max(lat)}
    if tokens:
        mean_tokens = statistics.mean(tokens)
        s["tokens"] = {"mean_input": round(mean_tokens), "total_input": sum(tokens),
                       "mean_output": round(statistics.mean(
                           r["usage"].get("output_tokens", 0) for r in ok if r.get("usage")))}
        s["cost_per_1000_messages_usd"] = round(mean_tokens * 1000 * PRICE_PER_M[provider] / 1e6, 4)
    return s


def fmt(r):
    if not r or r.get("n", 0) == 0:
        return "n/a"
    lo, hi = r["ci95"]
    return f"{r['rate'] * 100:.1f}% ({r['k']}/{r['n']}, 95% CI {lo * 100:.0f}-{hi * 100:.0f}%)"


def markdown(summary, meta):
    lines = [f"# Results: {meta.get('started', '')}", "",
             f"Messages: {meta.get('cases')} · runs: {meta.get('runs')} · "
             f"route threshold: {decide.ROUTE_MIN} · enough threshold: {decide.ENOUGH_MIN}", ""]
    for name, s in summary.items():
        lines += [f"## {name} ({', '.join(s.get('models', [])) or 'no answers'})", "",
                  f"- Requests: {s['requests']}, errors: {s['errors']}"]
        if "category_accuracy" not in s:
            lines += [f"- Errors: {s['error_samples']}", ""]
            continue
        pol = s["policy"]
        lines += [
            f"- Category accuracy, all messages: {fmt(s['category_accuracy'])}",
            f"- Category accuracy, messages with a clear category: {fmt(s['category_accuracy_clear'])}",
            f"- Unclear messages where the model chose unclear: {fmt(s['unclear_chosen'])}",
            f"- Policy at {pol['threshold']}: routed automatically {fmt(pol['coverage'])}; "
            f"of those correct {fmt(pol['routed_correct'])}; wrong routes {pol['wrong_routes']}",
            f"- Unclear messages held back by the policy: {fmt(pol['unclear_held_back'])}",
            f"- Category calibration (ECE, lower is better): {s['category_calibration']['ece']}",
            f"- Enough-information question: accuracy {fmt(s['enough']['accuracy'])}, "
            f"Brier {s['enough']['brier']}",
            f"- Urgency: accuracy {fmt(s['urgent']['accuracy'])}, recall {fmt(s['urgent']['recall'])}, "
            f"false alarms {s['urgent']['false_alarms']}",
            f"- Impact: mean absolute error {s['impact']['mean_abs_error']} levels, nearest level correct "
            f"{fmt(s['impact']['nearest_level_correct'])}",
        ]
        if "option_order" in s:
            o = s["option_order"]
            lines.append(f"- Options reversed: same choice {fmt(o['same_choice'])}, mean probability "
                         f"shift {o['mean_probability_shift']}, max {o['max_probability_shift']}")
        if "repeatability" in s:
            r = s["repeatability"]
            lines.append(f"- Across {r['runs']} runs: same choice {fmt(r['same_choice'])}, "
                         f"max probability spread {r['max_probability_spread']}")
        lines.append(f"- Latency: p50 {s['latency_ms']['p50']} ms, p95 {s['latency_ms']['p95']} ms")
        if "tokens" in s:
            lines.append(f"- Input tokens per request: {s['tokens']['mean_input']} · cost per 1,000 "
                         f"messages: ${s['cost_per_1000_messages_usd']}")
        lines += ["", "| Threshold | Routed | Correct when routed | Unclear held back | Wrong routes | "
                  "Wrong routes without `enough` |", "| --- | --- | --- | --- | --- | --- |"]
        for p in s["policy_curve"]:
            lines.append(f"| {p['threshold']} | {fmt(p['coverage'])} | {fmt(p['routed_correct'])} | "
                         f"{fmt(p['unclear_held_back'])} | {p['wrong_routes']} | "
                         f"{p['without_enough']['wrong_routes']} |")
        lines += ["", "Accuracy by kind of message:", ""]
        lines += [f"- {k}: {fmt(v)}" for k, v in s["accuracy_by_kind"].items()]
        lines += ["", "Most confident mistakes:", ""]
        lines += [f"- {m['id']} expected {m['expected']}, got {m['got']} at {m['p']}: \"{m['text']}\""
                  for m in s["confusions"][:8]]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        folder = Path(argv[0])
    else:
        folders = sorted(p for p in (HERE / "results").glob("*") if p.is_dir())
        if not folders:
            sys.exit("No results yet. Run compare.py first.")
        folder = folders[-1]
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines() if line]
    meta = json.loads((folder / "meta.json").read_text()) if (folder / "meta.json").exists() else {}
    summary = {}
    for path in sorted(folder.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        summary[path.stem] = summarize(rows, cases, path.stem)
    (folder / "summary.json").write_text(json.dumps({"meta": meta, "providers": summary}, indent=2))
    text = markdown(summary, meta)
    (folder / "report.md").write_text(text)
    print(text)
    print(f"Saved {folder / 'summary.json'} and {folder / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
