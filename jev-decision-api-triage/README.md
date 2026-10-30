# Support-request triage with TypeSafe Jev, compared with the OpenAI Decisions API

A small, runnable comparison of two decision APIs on the same job. Each one reads a short customer message and answers four typed questions. Then a plain-Python policy decides whether to **route** the message to a team automatically, ask the customer to **clarify**, or send it to a person for **review**.

- [TypeSafe Jev](https://docs.typesafe.ai) (`POST /v1/systemone`, `jev-latest`): `choice`, `noul`, and `score` questions.
- [OpenAI Decisions API](https://developers.openai.com/api/docs/guides/decisions) (`POST /v1/decisions`, `gpt-6-luna`, generally available since 22 October 2026): `choice`, `predicate`, and `score` questions. Optional: it runs only when `OPENAI_API_KEY` is set.

| Question | Jev | OpenAI | Used for |
| --- | --- | --- | --- |
| `category` | choice | choice | billing, account, technical, delivery, or unclear |
| `urgent` | noul | predicate | Does the message say it is urgent or give a deadline? |
| `impact` | score (0–2) | score (0–2) | Routine, Inconvenience, or Blocked or loss |
| `enough` | noul | predicate | Is there enough information to pick one category? |

`route()` in `decide.py` holds the policy. A message is routed only if the top category isn't `unclear`, `enough` is at least 0.50, and the top category's probability is at least 0.75. Everything else goes to a person or back to the customer. The thresholds are starting points, not recommendations.

## What it measures

`compare.py` sends all 120 labelled messages in `cases.jsonl` to each API, and `report.py` turns the answers into:

- **Category accuracy**, overall and by kind of message (clear, competing keywords, short, vague, more than one request).
- **Abstention:** how often the 24 messages with no clear category were chosen as `unclear`, or held back by the policy.
- **Coverage and accuracy together:** how many messages the policy routes automatically, and how many of those are right, for thresholds from 0.50 to 0.99.
- **Calibration:** expected calibration error of the top category probability, and Brier scores for the `enough` and `urgent` probabilities.
- **Option order:** each message is sent again with only the category question and its options reversed. TypeSafe's [Jev 1.13 notes](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md) say option order can affect a choice, and early OpenAI forum tests reported the same for Decisions.
- **Repeatability** with `--runs 2` or more, **latency** (p50, p95), **input tokens**, and **cost** per 1,000 messages.

Every rate is reported with its count and a 95% Wilson interval. 120 messages is a small sample, so read differences of a few points as noise.

## Contents

```
run.sh            runs everything: the comparison, then one message through the TypeSafe SDK
decide.py         the questions, the request for each API, response normalization, route()
compare.py        sends cases.jsonl to each API and saves the raw responses (standard library only)
report.py         turns a results folder into summary.json and report.md
sdk_example.py    one message through the TypeSafe Python SDK, with the same questions and route()
cases.jsonl       120 synthetic, labelled support messages, 24 per category
.env.example      copy to .env and add your keys (.env is git-ignored)
results/          written by each run (git-ignored)
published-results/2026-10-30/
                  the run behind the blog post: raw responses from both APIs, summary.json, report.md
```

To check the post's numbers without spending anything: `python3 report.py published-results/2026-10-30`.

See also [`openai-decision-api-triage`](../openai-decision-api-triage/), an image-and-text example of the Decisions API.

## The test messages

`cases.jsonl` has 24 messages for each of billing, account, technical, delivery, and unclear. Each one is labelled with its expected `category`, `urgent`, `impact` (0–2, or `null` when the message doesn't state one), `enough`, and a `kind`:

| Kind | Count | Example |
| --- | --- | --- |
| clear | 65 | "Export to CSV produces an empty file." |
| competing | 22 | "I'm trying to get my receipt, not reset my account password." |
| short | 9 | "receipt pls" |
| vague | 17 | "I have a problem with my order." |
| multi | 7 | "My card was billed two times, and now I'm locked out of my account as well." |

The messages and labels are synthetic and were written for this experiment by one person. They haven't been independently reviewed, so they show how the APIs behave, not how they'll do on your traffic.

## Requirements

- Python 3.10+ and bash
- A `TYPESAFE_API_KEY` from the [TypeSafe console](https://console.typesafe.ai), and optionally an `OPENAI_API_KEY` with Decisions access
- `run.sh` creates `.venv/` and installs `requirements.txt` (`typesafe-sdk`) for the SDK step. `compare.py` and `report.py` need only the standard library.

## Run it

```bash
cp .env.example .env          # add TYPESAFE_API_KEY, and OPENAI_API_KEY to compare
./run.sh                      # every API with a key
./run.sh --limit 10           # a quick check on the first 10 messages
./run.sh --runs 3             # send each message three times
./run.sh --providers jev      # Jev only
```

**Step 1, `compare.py`:** sends every message to each API with all four questions (once per run), and once more with only the category question and its options reversed. Errors are recorded, not skipped. Everything goes into a new `results/<timestamp>/` folder: `jev.jsonl` and `openai.jsonl` (raw responses, latency, token usage), `summary.json`, and `report.md`.

**Step 2, `sdk_example.py`:** sends one message through the TypeSafe Python SDK, as you would in production, and prints the answers and the route. Pass your own message as an argument: `.venv/bin/python sdk_example.py "Same issue as last week."`

To rebuild the report from an earlier run: `python3 report.py results/<timestamp>`.

At list prices ($0.042 per million input tokens for Jev, $0.10 for OpenAI Decisions), one full run costs a few cents. Check your own `usage` numbers in the report.

## Make it yours

1. Replace `cases.jsonl` with a few hundred of your own messages, labelled by the people who route them today.
2. Rewrite the category options in `decide.py` as definitions of your own queues. The option descriptions are effectively part of the prompt.
3. Choose `ROUTE_MIN` from the coverage table in `report.md`, weighing what a wrong route costs against what a review costs.
4. Pin model versions in `.env` (`JEV_MODEL=jev-1.14.0`) once you have tuned thresholds, because `jev-latest` moves when TypeSafe ships a release.
5. Run it in shadow mode next to your current routing before letting it act.

## Notes

- **Prices and models change.** Jev's price is from TypeSafe's [models page](https://docs.typesafe.ai/models.md); OpenAI's from the [Decisions guide](https://developers.openai.com/api/docs/guides/decisions) (uncached input; cache hits are discounted). Override the prices with `JEV_PRICE_PER_M` and `OPENAI_PRICE_PER_M`.
- **Same questions, different APIs.** The wording is shared. Jev's score levels are sent as `"Label: description"` strings, and OpenAI's as `label` and `description` fields.
- **Gating number.** The policy gates on the top category probability, computed the same way for both APIs. Jev's own `confidence` for a choice is a rescaling of that number, so it gives the same ranking.
- **Cost per 1,000 messages** counts the four-question request only, not the extra reversed-options request.
