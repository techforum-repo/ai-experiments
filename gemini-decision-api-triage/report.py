"""Turn a results folder into summary.json and report.md.

    python3 report.py results/<timestamp>
    python3 report.py published-results/<date>

Reads responses.jsonl (run_cases.py) and scale.jsonl (scale.py), whichever exist.
Standard library only.
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import decide

FORMAT_LABELS = {"text": "Text", "image": "Image (photo of a letter)", "audio": "Audio (voicemail)",
                 "pdf": "PDF (text layer)", "pdf_scanned": "PDF (scanned, image only)",
                 "video": "Video (spoken message)"}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def pct(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "–"


def p50(xs):
    return round(statistics.median(xs)) if xs else None


def p95(xs):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(0.95 * len(xs)))])


def modality_tokens(usage):
    return {m["modality"]: m.get("tokens", 0) for m in usage.get("input_tokens_by_modality", [])}


def judge(qkey, answer, label):
    """(correct or None, shown value, probability of the shown value)."""
    if label is None or answer is None:
        shown = None
        if answer:
            shown = answer.get("choice") or answer.get("noul") or answer.get("score")
        return None, shown, None
    t = answer["type"]
    if t == "choice":
        c, p = decide.top_choice(answer)
        return c == label, c, p
    if t == "noul":
        p = decide.prob_true(answer)
        return (p >= 0.5) == label, round(p, 2), p
    if t == "score":
        level, p = decide.top_level(answer)
        return level == label, level, p
    return None, None, None


def is_complete(r):
    """HTTP 200, not blocked by an input filter, and an answer for every question that was asked."""
    if r["status"] != "ok" or (r.get("prompt_feedback") or {}).get("block_reason"):
        return False
    return all(q in (r.get("answers") or {}) for q in r["questions"])


def expected_route(labels, questions, answers=None):
    """What the policy should do with this ticket. If the labels say route:X but the model's own
    top category probability is below ROUTE_MIN, review is the policy-correct action, so a
    low-confidence hold is not counted as a routing mistake (category accuracy is scored separately)."""
    if "sensitive" in questions and labels.get("sensitive"):
        return "redact"
    if "conflict" in questions and labels.get("conflict"):
        return "review"
    if labels["category"] == "unclear" or not labels.get("enough", True):
        return "clarify"
    if answers and "category" in answers and decide.top_choice(answers["category"])[1] < decide.ROUTE_MIN:
        return "review"
    return f"route:{labels['category']}"


def summarize_cases(records, cases):
    http_ok = [r for r in records if r["status"] == "ok"]
    ok = [r for r in http_ok if is_complete(r)]   # only complete responses are scored
    out = {"requests": len(records), "errors": len(records) - len(http_ok),
           "error_samples": [{"case": r["case"], "http_status": r.get("http_status"), "error": r.get("error")}
                             for r in records if r["status"] != "ok"][:10],
           "blocked": [r["case"] for r in http_ok if (r.get("prompt_feedback") or {}).get("block_reason")],
           "incomplete": [{"case": r["case"], "run": r["run"],
                           "missing": [q for q in r["questions"] if q not in (r.get("answers") or {})]}
                          for r in http_ok if not is_complete(r)
                          and not (r.get("prompt_feedback") or {}).get("block_reason")]}

    # --- formats: the same ten messages in six formats
    fmt = defaultdict(lambda: defaultdict(list))
    by_scenario = defaultdict(lambda: defaultdict(list))
    for r in ok:
        c = cases[r["case"]]
        if c["group"] != "formats":
            continue
        f = fmt[c["format"]]
        for q in ["category", "urgent", "impact", "enough", "sensitive"]:
            correct, shown, p = judge(q, r["answers"].get(q), c["labels"].get(q))
            if correct is not None:
                f[q].append(correct)
        f["top_p"].append(decide.top_choice(r["answers"]["category"])[1])
        f["route_ok"].append(decide.route(r["answers"])[0] == expected_route(c["labels"], c["questions"], r["answers"]))
        f["tokens"].append(r["usage"].get("total_input_tokens", 0))
        f["latency"].append(r["latency_ms"])
        by_scenario[c["scenario"]][c["format"]].append(r["answers"]["category"])
    formats = {}
    for name in FORMAT_LABELS:
        f = fmt.get(name)
        if not f:
            continue
        formats[name] = {
            "requests": len(f["tokens"]),
            **{q: [sum(f[q]), len(f[q])] for q in ["category", "urgent", "impact", "enough", "sensitive"]},
            "route_as_expected": [sum(f["route_ok"]), len(f["route_ok"])],
            "mean_top_category_p": round(statistics.mean(f["top_p"]), 3),
            "mean_input_tokens": round(statistics.mean(f["tokens"])),
            "latency_p50_ms": p50(f["latency"]), "latency_p95_ms": p95(f["latency"]),
            "cost_per_1000_usd": round(decide.cost(statistics.mean(f["tokens"])) * 1000, 4),
        }
    agreement = {}
    for sid, per_fmt in sorted(by_scenario.items()):
        label = cases[f"fmt-{sid}-text"]["labels"]["category"]
        choices = {k: [a["choice"] for a in v] for k, v in per_fmt.items()}
        p_label = [a["probabilities"].get(label, 0) for v in per_fmt.values() for a in v]
        agreement[sid] = {"label": label, "choices": choices,
                          "all_same": len({c for v in choices.values() for c in v}) == 1,
                          "p_label_min": round(min(p_label), 3), "p_label_max": round(max(p_label), 3)}
    out["formats"] = formats
    out["format_agreement"] = agreement

    # --- attachments, mixed and resolution: one row per case
    rows = defaultdict(list)
    for r in ok:
        c = cases[r["case"]]
        if c["group"] == "formats":
            continue
        checks = {}
        for q in r["questions"]:
            correct, shown, p = judge(q, r["answers"].get(q), c["labels"].get(q))
            checks[q] = {"label": c["labels"].get(q), "answer": shown,
                         "p": round(p, 3) if p is not None else None, "correct": correct}
        row = {"case": c["id"], "run": r["run"], "description": c.get("description", ""),
               "resolution": c.get("resolution"), "checks": checks,
               "tokens": r["usage"].get("total_input_tokens", 0),
               "tokens_by_modality": modality_tokens(r["usage"]), "latency_ms": r["latency_ms"]}
        if "enough" in r["answers"]:
            row["route"] = decide.route(r["answers"])[0]
            row["expected_route"] = expected_route(c["labels"], c["questions"], r["answers"])
        rows[c["group"]].append(row)
    out["attachments"] = collapse(rows.get("attachments", []))
    out["mixed"] = collapse(rows.get("mixed", []))
    out["resolution"] = collapse(rows.get("resolution", []))

    # --- stability across runs
    runs = defaultdict(list)
    for r in ok:
        runs[r["case"]].append(r["answers"].get("category", {}).get("choice"))
    multi = {k: v for k, v in runs.items() if len(v) > 1}
    if multi:
        out["stability"] = {"cases_with_repeats": len(multi),
                            "category_always_same": sum(len(set(v)) == 1 for v in multi.values()),
                            "changed": {k: v for k, v in multi.items() if len(set(v)) > 1}}

    toks = [r["usage"].get("total_input_tokens", 0) for r in ok]
    out["total_input_tokens"] = sum(toks)
    out["total_cost_usd"] = round(decide.cost(sum(toks)), 4)
    out["latency_p50_ms"] = p50([r["latency_ms"] for r in ok])
    return out


def summarize_scale(records):
    http_ok = [r for r in records if r["status"] == "ok"]
    by_size = defaultdict(list)
    for r in http_ok:
        by_size[r["size"]].append(r)
    ok = http_ok
    sizes = {}
    baseline = {}
    for size in sorted(by_size):
        rs_all = by_size[size]
        requested = sum(r.get("n_questions", size) for r in rs_all)
        received = sum(len(r.get("answers") or {}) for r in rs_all)
        # fact accuracy and drift use complete responses only, so a missing answer can't look like a correct one
        rs = [r for r in rs_all if len(r.get("answers") or {}) == r.get("n_questions", size)
              and not (r.get("prompt_feedback") or {}).get("block_reason")]
        if not rs:
            sizes[size] = {"requests": len(rs_all), "complete_requests": 0, "questions_requested": requested,
                           "answers_received": received, "answers_missing": requested - received}
            continue
        tp = fn = fp = tn = hard_fp = hard_n = 0
        for r in rs:
            for k, t in r["truth"].items():
                a = r["answers"][k]
                yes = decide.prob_true(a) >= 0.5
                if t["label"]:
                    tp += yes
                    fn += not yes
                else:
                    fp += yes
                    tn += not yes
                    if t["hard"]:
                        hard_n += 1
                        hard_fp += yes
        # how far the triage answers move compared with the smallest request that asked them
        drift = {}
        for q in ["category", "urgent", "enough", "conflict", "wrong_address"]:
            vals = []
            for r in rs:
                a = r["answers"].get(q)
                if a:
                    vals.append(a["probabilities"][a["choice"]] if a["type"] == "choice" else a["noul"])
            if vals:
                mean = statistics.mean(vals)
                baseline.setdefault(q, mean)
                drift[q] = {"mean_p": round(mean, 3), "vs_first_size": round(mean - baseline[q], 3)}
        toks = [r["usage"].get("total_input_tokens", 0) for r in rs]
        lat = [r["latency_ms"] for r in rs]
        sizes[size] = {
            "requests": len(rs_all), "complete_requests": len(rs), "questions_requested": requested,
            "answers_received": received, "answers_missing": requested - received,
            "latency_p50_ms": p50(lat), "latency_min_ms": round(min(lat)),
            "latency_max_ms": round(max(lat)), "mean_input_tokens": round(statistics.mean(toks)),
            "tokens_by_modality": modality_tokens(rs[0]["usage"]),
            "cost_per_request_usd": round(decide.cost(statistics.mean(toks)), 6),
            "cost_per_question_usd": round(decide.cost(statistics.mean(toks)) / size, 8),
            "facts": {"true_found": [tp, tp + fn], "false_rejected": [tn, tn + fp],
                      "near_miss_false_positives": [hard_fp, hard_n]},
            "triage_answers": drift,
        }
    return {"requests": len(records), "errors": len(records) - len(http_ok), "sizes": sizes,
            "error_samples": [{"size": r["size"], "http_status": r.get("http_status"), "error": r.get("error")}
                              for r in records if r["status"] != "ok"][:5]}


def frac(pair):
    return pct(*pair)


def collapse(rows):
    """One row per case across runs. Each check keeps run 1's answer, plus the range of p,
    the share of runs that were correct, and whether the answer changed between runs."""
    by = defaultdict(list)
    for row in rows:
        by[row["case"]].append(row)
    out = []
    for case, rs in by.items():
        first = dict(rs[0])
        first["runs"] = len(rs)
        checks = {}
        for q, chk in rs[0]["checks"].items():
            ps = [r["checks"][q]["p"] for r in rs if r["checks"][q]["p"] is not None]
            answers = {json.dumps(r["checks"][q]["answer"]) for r in rs}
            correct = [r["checks"][q]["correct"] for r in rs if r["checks"][q]["correct"] is not None]
            checks[q] = {**chk, "p_min": min(ps) if ps else None, "p_max": max(ps) if ps else None,
                         "answer_changed": len(answers) > 1,
                         "correct_runs": [sum(correct), len(correct)] if correct else None}
        first["checks"] = checks
        first["latency_ms"] = statistics.median(r["latency_ms"] for r in rs)
        routes = [r.get("route") for r in rs]
        first["route_runs"] = routes
        first["route_ok_runs"] = [sum(r.get("route") == r.get("expected_route") for r in rs), len(rs)]
        out.append(first)
    return out


def fmt_answer(a):
    return f"{a:.2f}" if isinstance(a, float) else f"{a}"


def mark(check):
    shown = fmt_answer(check["answer"]) if check["answer"] is not None else "–"
    if check.get("answer_changed"):
        shown += f" ({check['p_min']:.2f}–{check['p_max']:.2f})"
    if check["correct"] is None:
        return shown
    runs = check.get("correct_runs")
    if runs and 0 < runs[0] < runs[1]:
        return f"~ {shown} ({runs[0]}/{runs[1]} runs)"
    return f"{'✓' if check['correct'] else '✗'} {shown}"


def write_report(folder, summary, meta):
    L = [f"# Gemini Decisions API: multimodal triage results", "",
         f"Model `{meta.get('model')}`, endpoint `{meta.get('endpoint')}`. "
         f"Started {meta.get('cases_started') or meta.get('scale_started')}. "
         f"Prices at ${meta.get('price_per_m', decide.PRICE_PER_M)} per million input tokens.", ""]
    cs = summary.get("cases")
    if cs:
        L += [f"{cs['requests']} requests, {cs['errors']} errors, {cs['total_input_tokens']:,} input tokens, "
              f"${cs['total_cost_usd']} in total. Median latency {cs['latency_p50_ms']} ms "
              "(client-observed HTTP time of the final attempt; excludes encoding and retry backoff).", ""]
        if cs.get("incomplete"):
            L += ["Responses missing answers (excluded from scoring): "
                  + ", ".join(f"{i['case']} run {i['run']} ({', '.join(i['missing'])})" for i in cs["incomplete"]), ""]
        if cs["blocked"]:
            L += [f"Blocked by input filters: {', '.join(cs['blocked'])}", ""]
        if cs["formats"]:
            L += ["## Same message, six formats", "",
                  "Ten customer messages, each sent as text, a photographed letter, a voicemail, a PDF form, "
                  "a scanned PDF and a video message. Counts are correct answers out of labelled answers.", "",
                  "| Format | Category | Urgent | Impact | Enough | Sensitive (should be no) | Route as expected "
                  "| Mean top p | Input tokens | p50 ms | $ per 1,000 |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for k, f in cs["formats"].items():
                L.append(f"| {FORMAT_LABELS[k]} | {frac(f['category'])} | {frac(f['urgent'])} | "
                         f"{frac(f['impact'])} | {frac(f['enough'])} | {frac(f['sensitive'])} | "
                         f"{frac(f['route_as_expected'])} | {f['mean_top_category_p']} | {f['mean_input_tokens']:,} | "
                         f"{f['latency_p50_ms']} | {f['cost_per_1000_usd']} |")
            L += ["", "Did each message get the same category in every format?", ""]
            for sid, a in cs["format_agreement"].items():
                diff = "" if a["all_same"] else "  ← " + ", ".join(f"{k}: {'/'.join(v)}"
                                                                    for k, v in a["choices"].items())
                L.append(f"- {sid} ({a['label']}): {'same' if a['all_same'] else 'differs'}, "
                         f"P({a['label']}) {a['p_label_min']}–{a['p_label_max']}{diff}")
            L.append("")
        for group, title in [("attachments", "Messages with attachments"), ("mixed", "All five formats in one request")]:
            if not cs[group]:
                continue
            qs = []
            for row in cs[group]:
                qs += [q for q in row["checks"] if q not in qs]
            L += [f"## {title}", "", "✓/✗ against the label; noul answers show P(yes). One row per case: run 1's "
                  "answer, with the range in brackets when runs differed. Unlabelled answers are shown without a mark.", "",
                  "| Case | " + " | ".join(qs) + " | Route (expected) | Tokens | ms |",
                  "| --- " * (len(qs) + 4) + "|"]
            for row in cs[group]:
                cells = [mark(row["checks"][q]) if q in row["checks"] else "" for q in qs]
                rt = "/".join(sorted(set(row.get("route_runs") or [row.get("route", "")])))
                good, n = row.get("route_ok_runs", [rt == row.get("expected_route"), 1])
                ok = "✓" if good == n else ("✗" if good == 0 else f"~{good}/{n}")
                L.append(f"| {row['case']} | " + " | ".join(cells) +
                         f" | {ok} {rt} ({row.get('expected_route')}) | {row['tokens']:,} | {row['latency_ms']:.0f} |")
            L.append("")
        if cs["resolution"]:
            L += ["## Media resolution", "",
                  "| Case | Resolution | Answer | p | Media tokens | Total tokens | ms |", "| --- " * 7 + "|"]
            for row in cs["resolution"]:
                q = next(iter(row["checks"]))
                chk = row["checks"][q]
                media = sum(v for m, v in row["tokens_by_modality"].items() if m != "text")
                L.append(f"| {q} | {row['resolution']} | {mark(chk)} | {chk['p']:.3f} | {media:,} | "
                         f"{row['tokens']:,} | {row['latency_ms']:.0f} |")
            L.append("")
        if cs.get("stability"):
            s = cs["stability"]
            L += ["## Repeat runs", "", f"Category identical across runs for {s['category_always_same']} of "
                  f"{s['cases_with_repeats']} cases.", ""]
            for k, v in s["changed"].items():
                L.append(f"- {k}: {v}")
            L.append("")
        if cs["error_samples"]:
            L += ["## Errors", ""] + [f"- {e['case']}: HTTP {e['http_status']} {json.dumps(e['error'])[:300]}"
                                       for e in cs["error_samples"]] + [""]
    sc = summary.get("scale")
    if sc and sc["sizes"]:
        L += ["## Questions per request", "",
              "Same shared input every time (text, image, audio, PDF, video). The question set changes with the size "
              "(1 = category only; 10+ = 7 triage questions plus fact checks), so this describes these workloads, "
              "not question count in isolation. Fact accuracy counts complete responses only.",
              "", "| Questions | Requests (complete) | Answers received / requested | p50 ms (min–max) | Input tokens | $ per request | $ per question "
              "| True facts found | False facts rejected | Near-miss false positives |",
              "| --- " * 10 + "|"]
        for size, s in sc["sizes"].items():
            if not s.get("complete_requests"):
                L.append(f"| {size} | {s['requests']} (0) | {s['answers_received']:,} / {s['questions_requested']:,} |"
                         + " – |" * 7)
                continue
            f = s["facts"]
            L.append(f"| {size} | {s['requests']} ({s['complete_requests']}) | "
                     f"{s['answers_received']:,} / {s['questions_requested']:,} | {s['latency_p50_ms']} ({s['latency_min_ms']}–{s['latency_max_ms']}) | "
                     f"{s['mean_input_tokens']:,} | {s['cost_per_request_usd']:.6f} | {s['cost_per_question_usd']:.8f} | "
                     f"{frac(f['true_found'])} | {frac(f['false_rejected'])} | {frac(f['near_miss_false_positives'])} |")
        L += ["", "Triage answers as questions are added (mean probability; change from the first size that asked it):", ""]
        for size, s in sc["sizes"].items():
            parts = [f"{q} {d['mean_p']} ({d['vs_first_size']:+})" for q, d in s["triage_answers"].items()]
            L.append(f"- {size}: " + ", ".join(parts))
        L.append("")
        if sc["error_samples"]:
            L += ["Errors:", ""] + [f"- size {e['size']}: HTTP {e['http_status']} {json.dumps(e['error'])[:300]}"
                                    for e in sc["error_samples"]] + [""]
    (folder / "report.md").write_text("\n".join(L))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1])
    meta = json.loads((folder / "meta.json").read_text()) if (folder / "meta.json").exists() else {}
    cases = {c["id"]: c for c in decide.load_cases()}
    summary = {"meta": meta}
    responses = read_jsonl(folder / "responses.jsonl")
    if responses:
        summary["cases"] = summarize_cases(responses, cases)
    scale = read_jsonl(folder / "scale.jsonl")
    if scale:
        summary["scale"] = summarize_scale(scale)
    if len(summary) == 1:
        sys.exit(f"No responses.jsonl or scale.jsonl in {folder}")
    (folder / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    write_report(folder, summary, meta)
    print(f"Wrote {folder / 'summary.json'} and {folder / 'report.md'}")


if __name__ == "__main__":
    main()
