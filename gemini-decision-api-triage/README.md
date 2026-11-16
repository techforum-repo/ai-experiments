# Multimodal support-ticket triage with the Gemini Decisions API

A runnable experiment on what changes when the evidence isn't text. The [Gemini Decisions API](https://aistudio.google.com/docs/decisions-api) (`POST /v1beta/decisions`, model `gemini-decision-1`) takes text, images, audio, video and PDFs in one shared input. It answers up to 1,000 typed questions about that input in one request: `noul` (yes/no), `choice` and `score`.

The job is the same support triage as in [`jev-decision-api-triage`](../jev-decision-api-triage/). The model answers typed questions. Then a plain-Python policy (`route()` in `decide.py`) decides whether to:

- **route** the ticket to a queue
- ask the customer to **clarify**
- send it to a person for **review**
- hold it to **redact** an attachment that shows card details or a password

This time the tickets come as voicemails, scanned letters, PDFs, screenshots and screen recordings.

| Question | Type | Asked in | Used for |
| --- | --- | --- | --- |
| `category` | choice | all triage cases | billing, account, technical, delivery, or unclear |
| `urgent` | noul | all triage cases | Does the customer say it is urgent, or give a deadline within days? |
| `impact` | score (0–2) | all triage cases | Routine, Inconvenience, Blocked or loss |
| `enough` | noul | all triage cases | Enough information for exactly one category? |
| `sensitive` | noul | all triage cases | Does the input show a card number, CVC, password or one-time code? |
| `conflict` | noul | cases with attachments | Does an attachment contradict what the customer says? |
| `wrong_address` | noul | the five-format case | Does the house number on the delivery photo differ from the invoice address? |
| `error_code`, `receipt_total`, `tracking_number`, `lock_duration` | choice | resolution test | Small details in an image or recording |

## What it measures

1. **Same message, six formats** (`formats`, 60 requests). Ten customer messages, each sent as:
   - text
   - a photographed printed letter (JPEG)
   - a phone voicemail (MP3)
   - a PDF form with a text layer
   - the same form scanned into an image-only PDF
   - a video message with spoken audio (MP4)

   Do the category, urgency, impact and route stay the same when only the format changes? What does each format cost in tokens and latency?
2. **Messages with attachments** (`attachments`, 14 requests). Each attachment is the kind of evidence a real ticket would carry: an error screenshot, an invoice, a tracking page, a courier card, or screen recordings of a locked account, a double charge and an export that works. Several cases come in **controlled pairs** where only the attachment changes:
   - the same voicemail with an invoice that shows two charges, then one that shows a single charge
   - the same "it arrived damaged" message with a tracking page that says delivered, then one that says in transit

   This checks whether `conflict` follows the evidence. The set also includes:
   - a screenshot with a full card number and CVC
   - a screenshot with a sticky note telling "the AI triage system" how to classify the ticket (prompt injection in an image)
   - a Spanish voicemail
   - a voicemail on a noisy line
   - "See attached." with an unrelated photo
3. **All five formats in one request** (`mixed`, 2 requests). Text, a tracking screenshot, a voicemail, a PDF invoice and a screen recording of the proof-of-delivery photo. In one version the photo shows house number 1418 while the invoice says 1814. In the other they match. `wrong_address` can only be answered by reading a frame of the video and comparing it with the PDF.
4. **Media resolution** (`resolution`, 15 requests). Small text read at `low`, `medium`, `high` and `ultra_high`, with the accuracy and image tokens at each setting:
   - a small toast on a 1920×1080 dashboard
   - the total on a long, scanned receipt
   - the tracking number in small print on a shipping label

   The same check runs on a screen recording at `low`, `medium` and `high`.
5. **Questions per request** (`scale.py`, 4 requests). The five-format input with 1, 10, 100 and 1,000 questions. It shows how latency, tokens and cost change with the number of questions. The extra questions are yes/no fact checks with known answers (`scale_questions.json`): 11 true, the rest false, including near misses such as order 55102 for 55120. So it also shows whether accuracy, or the triage answers, change when 993 other questions share the request.

Add `--runs 3` for repeatability: does the category change between identical requests?

Every count in the report is a raw count (correct out of labelled). These are small, synthetic samples, so read them as behaviour, not as benchmark accuracy.

## Contents

```
run.sh                 runs everything: cases, questions-per-request test, SDK example, report
decide.py              the questions, request building (media inline as base64), retries, pacing, route()
run_cases.py           sends cases.jsonl and saves the raw responses (standard library only)
scale.py               1 to 1,000 questions on the same input (standard library only)
report.py              turns a results folder into summary.json and report.md
sdk_example.py         one ticket through the google-genai SDK, attachments uploaded with the Files API
cases.jsonl            91 cases: parts (text or a media file), questions, labels
scale_questions.json   995 yes/no fact checks with ground truth for scale.py
samples/               the generated media: image/, audio/, pdf/, video/ (about 6 MB)
make_samples.py        regenerates samples/, cases.jsonl and scale_questions.json
.env.example           copy to .env and add your key (.env is git-ignored)
results/               written by each run (git-ignored)
published-results/2026-11-16/
                       the run behind the blog post (3 runs): raw responses, summary.json, report.md, SDK output
```

To check the post's numbers without spending anything: `python3 report.py published-results/2026-11-16`.

## The samples

Everything in `samples/` is synthetic and generated by `make_samples.py`, so you can inspect it and rebuild it.

- **Made up:** Fernway (an outdoor-gear shop with a membership plan and an app), ParcelRoute (its courier), Northbank and every customer.
- **Card number:** the one in `card-declined.png` is the standard 4111 test number.
- **Voices:** generated locally with [Kokoro](https://github.com/thewh1teagle/kokoro-onnx). Voicemails get a telephone band and line noise. The noisy one gets a lot more.
- **Images, PDFs and video:** screenshots and recordings are drawn with Pillow and encoded with ffmpeg. PDFs come from WeasyPrint, and "scanned" PDFs are rasterized, rotated and noised so they have no text layer.

The labels were written by one person for this experiment. A few are deliberately `null` where a reasonable person could pick either answer, for example the impact of a parcel held at a depot. Those answers are reported but not scored.

## Requirements

- Python 3.10+ and bash
- A `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/api-keys). The free tier is enough.
- `run.sh` creates `.venv/` and installs `requirements.txt` (`google-genai>=3.3.0`) for the SDK step. The other scripts need only the standard library.
- To regenerate the samples only: `requirements-samples.txt`, ffmpeg, pdftoppm and the Kokoro model files.

## Run it

```bash
cp .env.example .env              # add GEMINI_API_KEY
./run.sh                          # everything, once
./run.sh --runs 3                 # three times, for repeatability and latency spread
./run.sh --groups formats         # one group: formats, attachments, mixed, resolution
./run.sh --skip-scale --skip-sdk  # cases only
python3 run_cases.py --only att-card   # a single case
```

Each run writes `results/<timestamp>/`:

- `responses.jsonl` and `scale.jsonl`: raw answers, latency, `usage` with tokens by modality, and errors
- `summary.json` and `report.md`
- `sdk-run.txt`

To rebuild a report: `python3 report.py results/<timestamp>`.

**Pacing.** The free tier allows 200 requests and 50,000 input tokens per minute. The 1,000-question request and the video cases are the big ones. `decide.py` paces requests to stay under those limits, and retries 429 and 5xx responses with backoff. If you have a paid tier, set `GEMINI_RPM` and `GEMINI_TPM` in `.env` so it runs faster.

**Cost.** At $0.10 per million input tokens with no output charge, one full run is about 100 requests and should cost a few cents. Check `usage` in the report.

## Make it yours

1. Replace the samples with real tickets and their attachments, labelled by the people who route them today. Anonymize them first.
2. Rewrite the category options in `decide.py` as definitions of your own queues. The option descriptions are effectively part of the prompt.
3. Choose thresholds (`ROUTE_MIN`, `CONFLICT_MIN`, `SENSITIVE_MIN`) from labelled traffic, weighing what a wrong action costs against what a review costs.
4. Use the Files API (see `sdk_example.py`) rather than inline base64 when the same file is used in many requests or is large. Inline requests are limited to 100 MB, and PDFs to 50 MB.
5. Run it in shadow mode next to your current routing before letting it act.

## Notes

- **Questions are independent.** They can't see each other's answers, so `route()` combines them in code.
- **Option keys are sorted.** The API sorts choice option keys before evaluation, so the order you write them in doesn't matter. Exact ties go to the alphabetically first key.
- **Yes/no probabilities are capped** at 0.01 to 0.99.
- **Blocked input.** Input that trips a safety filter comes back as HTTP 400 with an `error.code`, or as `prompt_feedback.block_reason` with no answers. Both are recorded.
- **Model version.** The response carries no model version, so record the date of each run.
- **Model ID.** The SDK's docstring says `models/{model}`, while the docs' examples use `gemini-decision-1`. This experiment sends the bare ID. Override it with `GEMINI_DECISIONS_MODEL` if needed.
- **Prices and limits change.** These are from Google's docs as of 16 November 2026. Override the price with `GEMINI_DECISIONS_PRICE_PER_M`.
