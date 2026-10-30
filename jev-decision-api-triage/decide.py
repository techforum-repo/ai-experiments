"""Support-request triage: four typed questions, two decision APIs, one policy.

The same four questions go to TypeSafe Jev (POST /v1/systemone) and to the
OpenAI Decisions API (POST /v1/decisions). Each API has its own request and
response shape, so this module builds both requests from one definition and
turns both responses into the same normalized answers. route() then decides,
in plain Python, whether to route the request or ask a person.

Standard library only. compare.py imports this module; sdk_example.py shows
the same questions through the TypeSafe Python SDK.
"""
import json
import os
import time
import urllib.error
import urllib.request

JEV_MODEL = os.environ.get("JEV_MODEL", "jev-latest")
OPENAI_MODEL = os.environ.get("OPENAI_DECISIONS_MODEL", "gpt-6-luna")
JEV_URL = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai").rstrip("/") + "/v1/systemone"
OPENAI_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/decisions"

# The questions, written once. Option order matters to both models, so the
# comparison also asks the category question with the options reversed.
CATEGORY = {
    "instructions": "Identify the single primary request in the customer message. "
                    "Choose unclear if it cannot be determined without guessing.",
    "options": {
        "billing": "Payments, charges, invoices, receipts, refunds, plans and prices.",
        "account": "Signing in, passwords, verification, security, and profile details.",
        "technical": "A feature or part of the app or product that does not work as expected.",
        "delivery": "Packages, shipping, tracking, couriers, and returns labels.",
        "unclear": "Too little information, or more than one request with no clear primary one.",
    },
}
URGENT = ("Does the message explicitly say the request is urgent or give a deadline "
          "within the next few days?")
IMPACT = {
    "instructions": "How serious is the impact the customer states in the message?",
    "levels": [
        ("Routine", "A question or routine request; nothing is broken or lost."),
        ("Inconvenience", "Something is wrong or degraded, but the customer can still get things done."),
        ("Blocked or loss", "The customer is blocked, has lost money or data, or something has failed."),
    ],
}
ENOUGH = ("Does the message contain enough information to identify exactly one "
          "primary request category: billing, account, technical, or delivery?")

CATEGORIES = list(CATEGORY["options"])

# Policy thresholds. Starting points; set them from your own labelled data.
ROUTE_MIN = 0.75     # top category probability needed to route without a person
ENOUGH_MIN = 0.50    # below this, the model thinks the message is underspecified
URGENT_MIN = 0.70    # TypeSafe's suggested starting point for a Noul "yes"


def jev_request(message, reverse_options=False):
    options = list(CATEGORY["options"].items())
    if reverse_options:
        return {"model": JEV_MODEL, "state": message, "questions": {"category": {
            "type": "choice", "instructions": CATEGORY["instructions"],
            "criteria": dict(reversed(options))}}}
    return {
        "model": JEV_MODEL,
        "state": message,
        "questions": {
            "category": {"type": "choice", "instructions": CATEGORY["instructions"],
                         "criteria": dict(options)},
            "urgent": {"type": "noul", "instructions": URGENT},
            "impact": {"type": "score", "instructions": IMPACT["instructions"],
                       "criteria": [f"{label}: {text}" for label, text in IMPACT["levels"]]},
            "enough": {"type": "noul", "instructions": ENOUGH},
        },
    }


def openai_request(message, reverse_options=False):
    options = list(CATEGORY["options"].items())
    category = {"type": "choice", "name": "category", "instructions": CATEGORY["instructions"],
                "choices": [{"value": v, "description": d}
                            for v, d in (reversed(options) if reverse_options else options)]}
    if reverse_options:
        return {"model": OPENAI_MODEL, "input": message, "questions": [category]}
    return {
        "model": OPENAI_MODEL,
        "input": message,
        "questions": [
            category,
            {"type": "predicate", "name": "urgent", "instructions": URGENT},
            {"type": "score", "name": "impact", "instructions": IMPACT["instructions"],
             "levels": [{"label": label, "description": text} for label, text in IMPACT["levels"]]},
            {"type": "predicate", "name": "enough", "instructions": ENOUGH},
        ],
    }


def normalize_jev(raw):
    """Jev answers are keyed by question name. Probabilities are maps."""
    out = {}
    for name, a in raw["answers"].items():
        if a["type"] == "choice":
            out[name] = {"choice": a["choice"], "probabilities": a["probabilities"],
                         "confidence": a.get("confidence")}
        elif a["type"] == "score":
            probs = [a["probabilities"][k] for k in sorted(a["probabilities"], key=int)]
            out[name] = {"score": a["score"], "probabilities": probs, "confidence": a.get("confidence")}
        elif a["type"] == "noul":
            out[name] = {"probability": a["noul"]}
    return out


def normalize_openai(raw):
    """Decisions answers are a list with names. Any answer can be a refusal."""
    out = {}
    for a in raw["answers"]:
        name = a["name"]
        if a["type"] == "choice":
            out[name] = {"choice": a["choice"],
                         "probabilities": {p["value"]: p["probability"] for p in a["probabilities"]},
                         "confidence": a.get("confidence")}
        elif a["type"] == "score":
            probs = [p["probability"] for p in sorted(a["probabilities"], key=lambda p: p["value"])]
            out[name] = {"score": a["score"], "probabilities": probs, "confidence": a.get("confidence")}
        elif a["type"] == "predicate":
            out[name] = {"probability": a["probability"]}
        else:
            out[name] = {"refusal": True}
    return out


PROVIDERS = {
    "jev": {"url": JEV_URL, "key_env": "TYPESAFE_API_KEY", "request": jev_request,
            "normalize": normalize_jev},
    "openai": {"url": OPENAI_URL, "key_env": "OPENAI_API_KEY", "request": openai_request,
               "normalize": normalize_openai},
}


def call(provider, request, key, retries=4, timeout=60):
    """POST one request. Retries 429/529/5xx with backoff; returns (raw, latency_ms)."""
    body = json.dumps(request).encode()
    for attempt in range(retries + 1):
        req = urllib.request.Request(PROVIDERS[provider]["url"], data=body, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = json.loads(resp.read())
            return raw, (time.perf_counter() - start) * 1000
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 529) and attempt < retries:
                wait = float(e.headers.get("retry-after") or 2 ** attempt)
                time.sleep(min(wait, 30))
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None


def top(category):
    """The selected option and its probability, the number the policy gates on."""
    choice = max(category["probabilities"], key=category["probabilities"].get)
    return choice, category["probabilities"][choice]


def route(answers, route_min=ROUTE_MIN):
    """Turn normalized answers into (action, reason). Doubt goes to a person."""
    missing = [n for n in ("category", "enough") if n not in answers]
    if missing:
        return "review", f"no answer for: {', '.join(missing)}"
    refused = [n for n, a in answers.items() if a.get("refusal")]
    if refused:
        return "review", f"model refused: {', '.join(refused)}"

    choice, p = top(answers["category"])
    if choice == "unclear":
        return "clarify", "model chose unclear"
    if answers["enough"]["probability"] < ENOUGH_MIN:
        return "clarify", f"not enough information ({answers['enough']['probability']:.2f})"
    if p < route_min:
        return "review", f"{choice} at {p:.2f}, below {route_min}"
    return "route", choice
