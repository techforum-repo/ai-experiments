"""Support-ticket triage with the Gemini Decisions API, across text, images, audio, video and PDFs.

One module holds everything the runners share:
  - QUESTIONS: every question the experiment asks, in the API's own format
  - build_request(): turns a case from cases.jsonl into a POST /v1beta/decisions body
  - decide(): sends it (standard library only), with retries and a simple rate limiter
  - route(): the plain-Python policy that turns answers into an action

Model and endpoint can be overridden with GEMINI_DECISIONS_MODEL and GEMINI_BASE_URL.
"""
import base64
import json
import os
import random
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = os.environ.get("GEMINI_DECISIONS_MODEL", "gemini-decision-1")
BASE_URL = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
URL = f"{BASE_URL}/v1beta/decisions"
PRICE_PER_M = float(os.environ.get("GEMINI_DECISIONS_PRICE_PER_M", "0.10"))  # USD per 1M input tokens

FRAMING = "A customer contacted Fernway support. Their message and any attachments follow.\n"

CATEGORY_OPTIONS = {
    "billing": "Payments, charges, invoices, receipts, refunds, plans and prices.",
    "account": "Signing in, passwords, verification, security, and profile details.",
    "technical": "A feature or part of the app or product that does not work as expected.",
    "delivery": "Packages, shipping, tracking, couriers, and returns labels.",
    "unclear": "Too little information, or more than one request with no clear primary one.",
}

QUESTIONS = {
    # The four triage questions from the Jev post, reworded to cover attachments.
    "category": {
        "type": "choice",
        "instructions": "Identify the single primary request the customer is making, using their message "
                        "and any attachments. Choose unclear if it cannot be determined without guessing.",
        "criteria": CATEGORY_OPTIONS,
    },
    "urgent": {
        "type": "noul",
        "instructions": "Does the customer explicitly say the request is urgent, or give a deadline "
                        "within the next few days?",
    },
    "impact": {
        "type": "score",
        "instructions": "How serious is the impact the customer describes?",
        "criteria": [
            "Routine: a question or routine request; nothing is broken or lost.",
            "Inconvenience: something is wrong or degraded, but the customer can still get things done.",
            "Blocked or loss: the customer is blocked, has lost money or goods, or something has failed.",
        ],
    },
    "enough": {
        "type": "noul",
        "instructions": "Is there enough information to identify exactly one primary request category: "
                        "billing, account, technical, or delivery?",
    },
    # Questions that only make sense once there are attachments.
    "sensitive": {
        "type": "noul",
        "instructions": "Does the input show a full payment card number, a card security code, a password, "
                        "or a one-time code in readable form?",
    },
    "conflict": {
        "type": "noul",
        "instructions": "Does any document, screenshot or recording in the input contradict what the "
                        "customer says happened?",
        "criteria": {
            "true_description": "An attachment shows something different from the customer's account of events.",
            "false_description": "The attachments agree with the customer, or there is nothing to compare.",
        },
    },
    "wrong_address": {
        "type": "noul",
        "instructions": "Does the house number on the proof-of-delivery photo differ from the house number "
                        "in the shipping address on the invoice?",
    },
    # Reading small details, used to compare media resolutions.
    "error_code": {
        "type": "choice",
        "instructions": "Which error code does the image show?",
        "criteria": {"SYN-4127": "", "SYN-4172": "", "SYN-1427": "", "SYN-7421": "",
                     "other": "No error code is visible, or it is a different code."},
    },
    "receipt_total": {
        "type": "choice",
        "instructions": "What total amount does the receipt show?",
        "criteria": {"47.85": "", "47.58": "", "74.85": "", "45.87": "",
                     "other": "No total is readable, or it is a different amount."},
    },
    "tracking_number": {
        "type": "choice",
        "instructions": "Which tracking number is printed on the shipping label?",
        "criteria": {"PR-7781-2290": "", "PR-7781-2209": "", "PR-7718-2290": "", "PR-1778-2290": "",
                     "other": "No tracking number is readable, or it is a different one."},
    },
    "lock_duration": {
        "type": "choice",
        "instructions": "According to the recording, for how long is sign-in locked?",
        "criteria": {"1_hour": "One hour.", "12_hours": "Twelve hours.", "24_hours": "24 hours.",
                     "48_hours": "48 hours.", "other": "It is not locked, or the duration is different or not shown."},
    },
}

# Policy thresholds. Starting points, not recommendations: set them from labelled traffic.
ROUTE_MIN = 0.75       # top category probability needed to route without a person
ENOUGH_MIN = 0.50
SENSITIVE_MIN = 0.50   # above this, hold the ticket until the attachment is redacted
CONFLICT_MIN = 0.50    # above this, a person checks the evidence before anything is automated


def load_cases(path=HERE / "cases.jsonl"):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def content_blocks(case):
    """The case's parts as API content blocks. Media is sent inline as base64."""
    blocks = []
    if case["group"] != "resolution":
        blocks.append({"type": "text", "text": FRAMING})
    for p in case["parts"]:
        if p["type"] == "text":
            t = p["text"]
            blocks.append({"type": "text", "text": t if t.endswith("\n") else t + "\n"})
            continue
        block = {"type": p["type"], "mime_type": p["mime_type"],
                 "data": base64.b64encode((HERE / p["path"]).read_bytes()).decode()}
        if p.get("resolution"):
            block["resolution"] = p["resolution"]
        blocks.append(block)
    return blocks


def build_request(case, questions=None):
    keys = questions or case["questions"]
    return {"model": MODEL, "input": content_blocks(case),
            "questions": {k: QUESTIONS[k] for k in keys}}


def estimate_tokens(case, n_questions):
    """Rough input-token estimate, used only to pace requests under a tokens-per-minute limit."""
    est = 200 + 40 * n_questions
    for p in case["parts"]:
        if p["type"] == "text":
            est += len(p["text"]) // 3
        elif p["type"] == "image":
            est += 2200 if p.get("resolution") == "ultra_high" else 1200
        elif p["type"] == "audio":
            est += int(p.get("seconds", 15) * 32)
        elif p["type"] == "video":
            per_frame = 70 if p.get("resolution") == "low" else 260
            est += int(p.get("seconds", 15) * (per_frame + 32))
        elif p["type"] == "document":
            est += p.get("pages", 1) * 600
    return est


class Pacer:
    """Keeps requests under per-minute request and token limits (free tier: 200 RPM, 50,000 TPM).
    Set GEMINI_RPM / GEMINI_TPM to your tier's limits, or 0 to turn pacing off."""

    def __init__(self):
        self.rpm = int(os.environ.get("GEMINI_RPM", "200"))
        self.tpm = int(os.environ.get("GEMINI_TPM", "50000"))
        self.log = deque()  # (time, tokens)

    def wait(self, tokens):
        if not self.rpm and not self.tpm:
            return
        while True:
            now = time.monotonic()
            while self.log and now - self.log[0][0] > 60:
                self.log.popleft()
            used = sum(t for _, t in self.log)
            ok_r = not self.rpm or len(self.log) < self.rpm
            ok_t = not self.tpm or used + tokens <= self.tpm or not self.log
            if ok_r and ok_t:
                self.log.append((now, tokens))
                return
            time.sleep(max(0.5, 60 - (now - self.log[0][0]) + 0.1))

    def record(self, tokens):
        """Replace the latest estimate with the real token count."""
        if self.log:
            t, _ = self.log.pop()
            self.log.append((t, tokens))


def decide(body, api_key, pacer=None, est_tokens=0, max_retries=6):
    """POST one request. Returns a dict with status, latency, usage, answers, and any error."""
    data = json.dumps(body).encode()
    retries = 0
    while True:
        if pacer:
            pacer.wait(est_tokens)
        req = urllib.request.Request(URL, data=data, method="POST", headers={
            "Content-Type": "application/json", "x-goog-api-key": api_key})
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                payload = json.loads(resp.read())
                latency = (time.perf_counter() - start) * 1000
            usage = payload.get("usage") or {}
            if pacer:
                pacer.record(usage.get("total_input_tokens", est_tokens))
            return {"status": "ok", "http_status": 200, "latency_ms": round(latency, 1), "retries": retries,
                    "request_bytes": len(data), "usage": usage, "answers": payload.get("answers") or {},
                    "prompt_feedback": payload.get("prompt_feedback")}
        except urllib.error.HTTPError as e:
            latency = (time.perf_counter() - start) * 1000
            text = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and retries < max_retries:
                retries += 1
                time.sleep(min(60, 5 * 2 ** (retries - 1)) + random.random())
                continue
            try:
                err = json.loads(text)
            except ValueError:
                err = text[:2000]
            return {"status": "error", "http_status": e.code, "latency_ms": round(latency, 1),
                    "retries": retries, "request_bytes": len(data), "error": err}
        except (urllib.error.URLError, TimeoutError) as e:
            if retries < max_retries:
                retries += 1
                time.sleep(min(60, 5 * 2 ** (retries - 1)))
                continue
            return {"status": "error", "http_status": None, "retries": retries, "request_bytes": len(data),
                    "error": str(e)}


# ---------------------------------------------------------------------------
# Reading answers
# ---------------------------------------------------------------------------
def prob_true(answer):
    """P(yes) for a noul answer."""
    return answer["noul"]


def top_choice(answer):
    return answer["choice"], answer["probabilities"][answer["choice"]]


def top_level(answer):
    """Most likely level of a score answer (an int), and its probability."""
    level = max(answer["probabilities"], key=lambda k: answer["probabilities"][k])
    return int(level), answer["probabilities"][level]


def route(answers):
    """The policy, in code. Returns (action, reason).

    redact   an attachment shows card details, a password or a code: hold it before anyone works on it
    review   the evidence disagrees with the customer, or the model isn't sure enough to route
    clarify  not enough information, or no single request: ask the customer
    route:X  send to queue X automatically
    """
    if "sensitive" in answers and prob_true(answers["sensitive"]) >= SENSITIVE_MIN:
        return "redact", "sensitive data in the input"
    if "conflict" in answers and prob_true(answers["conflict"]) >= CONFLICT_MIN:
        return "review", "attachments contradict the customer"
    category, p = top_choice(answers["category"])
    if category == "unclear" or prob_true(answers["enough"]) < ENOUGH_MIN:
        return "clarify", "not enough information for one category"
    if p < ROUTE_MIN:
        return "review", f"top category {category} only {p:.2f}"
    return f"route:{category}", f"{category} at {p:.2f}"


def cost(input_tokens):
    return input_tokens * PRICE_PER_M / 1_000_000
