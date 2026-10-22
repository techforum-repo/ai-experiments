# OpenAI Agents API: Our CSV Sandbox Experiment

We built a Python runner that sends a deliberately messy transactions CSV to an
OpenAI-hosted Agents API sandbox and checks its output independently. The task
is unchanged: four sales, a refund, and an invalid row. The revised runner makes
inputs reproducible and retains evidence for inspection.

## Run

Requires Python 3.10+ and an OpenAI project key with `api.agents.read`,
`api.agents.write`, and `api.responses.write`. Keep the key in the application
environment. Each live trial uses model tokens and hosted compute.

```bash
cd openai-agents-api
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
python sandbox_check.py --seed 42          # one trial
python sandbox_check.py 5 --seed 42        # five trials, seeds 42–46
```

Options: positive positional trial count (default 1), `--seed`, `--model`
(default `gpt-6-astra`), `--timeout` (default 180 seconds), and `--output-dir`.
An existing output directory is rejected so previous evidence is not overwritten.
The pinned dependency is `openai==3.13.0`, matching the originally recorded SDK.
The revised API flow has offline test coverage; it has not been rerun live.

## What the runner does

1. Generate amounts in integer cents with a local seeded PRNG. Every fixture
   includes currency symbols, a thousands separator, whitespace, a negative
   refund, and `N/A`. Compute the reference directly from generated integers.
2. Create an Agents API session with `openai_hosted`, disabled sandbox network
   access, and the CSV seeded under `/workspace/data.csv`.
3. Ask the agent to write and execute `calculate.py`, then publish that script
   and `summary.json` under `/workspace/outputs`.
4. Poll the session and target root turn. Record observed timings and server
   turn data. Distinguish failures and required actions instead of calling every
   stalled run the same bug.
5. Save session items; find artifacts by path **and turn ID**; download both.
6. Validate exactly three integer fields: `total_cents`, `valid_rows`, and
   `invalid_rows`. Compare all three to the reference. Reject extra, missing,
   duplicate, boolean, float, and nonfinite values.
7. Save the result and attempt session cleanup, cancelling unfinished work first.

## Saved evidence

```text
runs/<timestamp>/
  run.json                  # model, installed SDK version, seed, settings
  results.json              # aggregate trial outcomes
  trial-001/
    data.csv                # exact input
    expected.json           # independent local reference
    request.json            # submitted agent/environment/input configuration
    session.json            # latest successfully retrieved session
    turns.json              # turn metadata, server timestamps and usage if present
    items.json              # saved messages/tool calls for inspection
    artifacts.json          # artifact metadata
    summary.json            # downloaded result
    calculate.py            # downloaded agent-generated script
    result.json             # checks, IDs, observed timing, errors and cleanup
```

Failure runs contain only files obtained before the failure. `passed` means the
required files were downloaded and all structured values matched. It does not
automatically prove the script executed: inspect command calls/results in
`items.json` and the script. The runner never executes downloaded code locally.

All timing fields are seconds from immediately before session creation. The
verification timing includes download and checking; cleanup timing is separate.
HTTP phase timeouts are capped at 15 seconds with automatic retries disabled.
The polling budget is checked between calls and pages; it is not a hard process
kill timer for a blocking transport or local disk operation. Cleanup has its own
10-second request timeouts and at most three deletion attempts for `409`.

Exit code 0 requires every trial's exact result check and confirmed deletion;
otherwise the runner returns 1. Invalid arguments return 2. Cleanup errors remain
visible separately from result correctness. If creation times out before returning
an ID, remote creation may still have happened; inspect the platform logs.

## Offline tests

No SDK, API key, or network required:

```bash
python -m unittest discover -s . -p test_sandbox_check.py -v
```

Checks cover reproducible fixtures against a separately parsed Decimal reference,
strict schema and exact amounts, stale/missing artifacts, setup/session failure,
required action, failed/cancelled turns, request failure, deadline cancellation,
cleanup failure, and invalid trial counts. Fake API responses exercise client
logic; they do not establish live SDK/service compatibility.

## Historical results: September 15, 2026

The earlier runner reported the following five trials. It returned a numeric
`total`, used float arithmetic with a tolerance smaller than one cent, and did
not save the complete evidence bundle above. These are historical observations,
not results from the revised runner. Its clocks started **after** the create
response and stopped **before** artifact download.

| Trial | Turn first observed | Session settled | Expected | Reported | Correct |
|---|---|---|---|---|---|
| 1 | 3.5s | 45.9s | 2650.52 | 2650.52 | ✅ |
| 2 | 75.8s | 85.6s | 4370.83 | 4370.83 | ✅ |
| 3 | 14.2s | 44.1s | 6139.28 | 6139.28 | ✅ |
| 4 | 3.8s | 43.1s | 3077.89 | 3077.89 | ✅ |
| 5 | 4.5s | 122.9s | 3332.67 | 3332.67 | ✅ |

Five matches describe this small run; they do not establish general reliability.
Earlier turn-start symptoms were consistent with the
[September 14 incident](https://status.openai.com/incidents/01M2H3J1D6Y7RHAP49GRWGJAY0).
That is not request-level proof of its cause.

## References

- [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview)
- [Hosted environments](https://developers.openai.com/api/docs/guides/agents-api/environments/openai-hosted)
- [Sessions and cancellation](https://developers.openai.com/api/docs/guides/agents-api/sessions)
- [Files and artifacts](https://developers.openai.com/api/docs/guides/agents-api/environments/files)
- [Research review](RESEARCH.md) — the pre-revision findings and source review.
