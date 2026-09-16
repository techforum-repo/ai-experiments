#!/usr/bin/env python3
"""Our Agents API CSV experiment: reproducible inputs and checked artifacts."""
import argparse
import base64
import csv
import io
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MODEL = "gpt-6-astra"
INSTRUCTIONS = (
    "Write /workspace/outputs/calculate.py and run it with Python. "
    "Read /workspace/data.csv. Strip whitespace, dollar signs and thousands "
    "separators from amounts. Skip non-numeric amounts; include negative refunds. "
    "Use Decimal or integer cents, never binary float arithmetic. Write "
    "/workspace/outputs/summary.json with exactly these integer fields: "
    "total_cents, valid_rows, invalid_rows. Count each data row once; exclude "
    "the header. Preserve calculate.py as an output artifact."
)
INPUT = "Clean and total /workspace/data.csv according to your instructions."
TERMINAL = {"completed", "failed", "cancelled"}


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def as_dict(value):
    return value.model_dump(mode="json")


def make_dataset(seed):
    """Every fixture contains currency, a thousands separator, N/A and a refund."""
    rng = random.Random(seed)
    sales = [rng.randint(100_000, 200_000)] + [rng.randint(1_000, 99_999) for _ in range(3)]
    refund = -rng.randint(1_000, 20_000)

    def money(cents):
        sign = "-" if cents < 0 else ""
        whole, fraction = divmod(abs(cents), 100)
        return f"{sign}${whole:,}.{fraction:02d}"

    rows = [(f" {money(value)} ", "sale") for value in sales]
    rows += [(money(refund), "refund"), ("N/A", "voided")]
    rng.shuffle(rows)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["amount", "note"])
    writer.writerows(rows)
    return buffer.getvalue(), {
        "total_cents": sum(sales) + refund, "valid_rows": 5, "invalid_rows": 1,
    }


def validate_summary(content, expected):
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate field: {key}")
            result[key] = value
        return result

    value = json.loads(content, parse_constant=reject_constant, object_pairs_hook=unique_fields)
    if not isinstance(value, dict) or value.keys() != expected.keys():
        raise ValueError("Expected exactly total_cents, valid_rows and invalid_rows")
    if any(type(number) is not int for number in value.values()):
        raise ValueError("Every summary field must be an integer, not a boolean")
    return value, value == expected


class TrialFailure(Exception):
    def __init__(self, outcome, detail):
        super().__init__(detail)
        self.outcome = outcome


def cleanup(client, session_id, cancel):
    """Bounded best effort; errors never hide the trial's original outcome."""
    api = client.with_options(timeout=10, max_retries=0).beta.agents.sessions
    result = {"deleted": False, "errors": []}
    if cancel:
        try:
            api.events.create(session_id, events=[{"type": "agent.session.input.cancel"}])
        except Exception as exc:
            result["errors"].append(f"cancel: {exc}")
    for attempt in range(3):
        try:
            api.delete(session_id)
            result["deleted"] = True
            break
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                result["deleted"] = True
                break
            if getattr(exc, "status_code", None) == 409 and attempt < 2:
                time.sleep(1)
                continue
            result["errors"].append(f"delete: {exc}")
            break
    return result


def run_trial(client, index, seed, directory, model=MODEL, timeout=180, poll_seconds=1):
    directory.mkdir(parents=True, exist_ok=False)
    csv_text, expected = make_dataset(seed)
    (directory / "data.csv").write_text(csv_text)
    save_json(directory / "expected.json", expected)
    request = {
        "agent": {"model": model, "instructions": INSTRUCTIONS},
        "environment": {
            "type": "openai_hosted", "network": {"access": "disabled"},
            "files": [{"type": "inline", "path": "/workspace/data.csv",
                       "data": base64.b64encode(csv_text.encode()).decode()}],
        },
        "input": INPUT,
    }
    save_json(directory / "request.json", request)
    result = {"trial": index, "seed": seed, "model": model, "expected": expected,
              "outcome": "interrupted", "correct": False, "timings": {},
              "session_id": None, "turn_id": None, "artifact_ids": {}}
    session = None
    turn = None
    started = time.monotonic()
    deadline = started + timeout

    def elapsed():
        return round(time.monotonic() - started, 3)

    def api():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TrialFailure("deadline_exceeded", "No verified result within polling budget")
        return client.with_options(timeout=min(15, remaining), max_retries=0).beta.agents.sessions

    def pages(fetch, **kwargs):
        records = []
        while True:
            page = fetch(api(), **kwargs)
            records.extend(page.data)
            if not page.has_more:
                return records
            if not page.last_id or page.last_id == kwargs.get("after"):
                raise TrialFailure("pagination_error", "Missing or repeated cursor")
            kwargs["after"] = page.last_id

    try:
        session = api().create(**request)
        result["session_id"] = session.id
        result["request_id"] = getattr(session, "_request_id", None)
        result["timings"]["create_response_s"] = elapsed()
        save_json(directory / "session.json", as_dict(session))
        while True:
            session = api().retrieve(session.id)
            save_json(directory / "session.json", as_dict(session))
            result["session_status"] = session.status
            if session.status == "failed":
                raise TrialFailure("session_failed", str(session.error))
            if session.status == "requires_action":
                raise TrialFailure("requires_action", "Inspect required_actions in session.json")
            turns = pages(lambda current, **kw: current.turns.list(session.id, **kw))
            save_json(directory / "turns.json", [as_dict(t) for t in turns])
            root_turns = [t for t in turns if t.subagent_id is None]
            if root_turns:
                turn = root_turns[0] if turn is None else next(t for t in root_turns if t.id == turn.id)
                result["turn_id"] = turn.id
                result["turn_status"] = turn.status
                result["timings"].setdefault("turn_first_seen_s", elapsed())
                if turn.status in TERMINAL:
                    result["timings"]["turn_terminal_seen_s"] = elapsed()
                    if turn.status != "completed":
                        raise TrialFailure(f"turn_{turn.status}", str(turn.error))
                    break
            time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))
        items = pages(lambda current, **kw: current.items.list(session.id, **kw), order="asc")
        save_json(directory / "items.json", [as_dict(item) for item in items])
        artifacts = pages(lambda current, **kw: current.artifacts.list(session.id, **kw))
        save_json(directory / "artifacts.json", [as_dict(a) for a in artifacts])
        for name in ["summary.json", "calculate.py"]:
            artifact = next((a for a in artifacts if a.path == f"/workspace/outputs/{name}"
                             and a.turn_id == turn.id), None)
            if artifact is None:
                raise TrialFailure("missing_artifact", f"No {name} for turn {turn.id}")
            content = api().artifacts.content(artifact.id, session_id=session.id).read()
            (directory / name).write_bytes(content)
            result["artifact_ids"][name] = artifact.id
        result["timings"]["download_complete_s"] = elapsed()
        try:
            reported, correct = validate_summary((directory / "summary.json").read_bytes(), expected)
        except (ValueError, UnicodeError) as exc:
            raise TrialFailure("invalid_summary", str(exc)) from exc
        result.update(reported=reported, correct=correct, outcome="passed" if correct else "wrong_result")
        result["timings"]["verification_complete_s"] = elapsed()
        result["execution_evidence"] = "items.json and calculate.py saved; manual inspection required"
    except TrialFailure as exc:
        result.update(outcome=exc.outcome, error=str(exc))
    except Exception as exc:
        result.update(outcome="request_or_client_error", error=f"{type(exc).__name__}: {exc}",
                      request_id=getattr(exc, "request_id", None))
    finally:
        result["timings"]["work_elapsed_s"] = elapsed()
        save_json(directory / "result.json", result)
        if session is not None:
            result["cleanup"] = cleanup(client, session.id, turn is None or turn.status not in TERMINAL)
        else:
            result["cleanup"] = {"deleted": None, "errors": [],
                "note": "No session ID returned; a create timeout may still leave a remote session."}
        result["timings"]["including_cleanup_s"] = elapsed()
        save_json(directory / "result.json", result)
    return result


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trials", nargs="?", type=positive_int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--timeout", type=positive_int, default=180)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    # Offline checks and --help work without an installed SDK or API key.
    import openai
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output_dir or Path("runs") / stamp
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / "run.json", {"created_at": stamp, "sdk_version": openai.__version__,
        "model": args.model, "seed": args.seed, "trials": args.trials, "timeout": args.timeout})
    results = []
    with openai.OpenAI(timeout=15, max_retries=0) as client:
        for index in range(1, args.trials + 1):
            result = run_trial(client, index, args.seed + index - 1,
                               output / f"trial-{index:03d}", args.model, args.timeout)
            results.append(result)
            save_json(output / "results.json", results)
            print(f"trial {index}: {result['outcome']} ({result['timings']['work_elapsed_s']}s)")
    print(f"Saved results: {output.resolve()}")
    return 0 if all(r["correct"] and r["cleanup"]["deleted"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(run())
