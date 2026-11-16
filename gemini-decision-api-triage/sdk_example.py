"""One ticket through the google-genai Python SDK, with attachments uploaded through the Files API.

The runners send media inline as base64. In production you would more often upload once and
refer to the file by URI, which this example does: a voicemail and a PDF invoice are uploaded,
then the same triage questions and route() policy as the rest of the experiment are applied.

    .venv/bin/python sdk_example.py                      the voicemail + the one-charge invoice
    .venv/bin/python sdk_example.py --invoice two         ... + the invoice that shows both charges

Needs GEMINI_API_KEY and google-genai (requirements.txt).
"""
import argparse
import json
import os
import sys

from google import genai

import decide

FILES = {
    "voicemail": "samples/audio/charged-twice-voicemail.mp3",
    "one": "samples/pdf/invoice-one-charge.pdf",
    "two": "samples/pdf/invoice-two-charges.pdf",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--invoice", choices=["one", "two"], default="one")
    args = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set.")

    client = genai.Client(http_options={"api_version": "v1beta"})
    print(f"google-genai {genai.__version__}, model {decide.MODEL}")

    uploads = []
    try:
        for name in ["voicemail", args.invoice]:
            f = client.files.upload(file=str(decide.HERE / FILES[name]))
            print(f"uploaded {FILES[name]} -> {f.uri} ({f.mime_type})")
            uploads.append(f)
        run(client, *uploads)
    finally:  # delete the uploads even if the request or the printing fails
        for f in uploads:
            try:
                client.files.delete(name=f.name)
            except Exception as e:  # noqa: BLE001 - cleanup must not hide the original error
                print(f"could not delete {f.name}: {e}", file=sys.stderr)


def run(client, voicemail, invoice):
    """The decision request, the answers and the route, for the uploaded voicemail and invoice."""
    keys = ["category", "urgent", "impact", "enough", "sensitive", "conflict"]
    result = client.decisions.create(
        model=decide.MODEL,
        input=[
            {"type": "text", "text": decide.FRAMING},
            {"type": "audio", "uri": voicemail.uri, "mime_type": voicemail.mime_type},
            {"type": "document", "uri": invoice.uri, "mime_type": invoice.mime_type},
        ],
        questions={k: decide.QUESTIONS[k] for k in keys},
    )

    answers = {k: v.model_dump() if hasattr(v, "model_dump") else dict(v) for k, v in result.answers.items()}
    for k in keys:
        a = answers[k]
        if a["type"] == "noul":
            print(f"  {k:<10} P(yes) {a['noul']:.2f}")
        elif a["type"] == "choice":
            print(f"  {k:<10} {a['choice']} ({a['confidence']:.2f})")
        else:
            print(f"  {k:<10} score {a['score']:.2f}, most likely level {decide.top_level(a)[0]} "
                  f"({a['confidence']:.2f})")
    action, reason = decide.route(answers)
    print(f"route: {action} ({reason})")
    usage = result.usage.model_dump() if hasattr(result.usage, "model_dump") else result.usage
    print("usage:", json.dumps(usage, default=str))


if __name__ == "__main__":
    main()
