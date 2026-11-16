#!/usr/bin/env bash
# Multimodal support-ticket triage with the Gemini Decisions API.
#
#   ./run.sh                 everything: the cases, the questions-per-request test, the SDK example
#   ./run.sh --runs 3        each case and each size three times (stability, latency)
#   ./run.sh --skip-scale    skip step 2 (up to 1,000 questions in one request)
#   ./run.sh --skip-sdk      skip step 3 (the google-genai SDK example)
#   ./run.sh --groups formats,mixed   only some case groups (formats, attachments, mixed, resolution)
#
# The key comes from the environment or from a .env file next to this script
# (copy .env.example to .env and fill it in).
set -euo pipefail

cd "$(dirname "$0")"

SKIP_SDK=0
SKIP_SCALE=0
RUNS=1
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-sdk) SKIP_SDK=1; shift ;;
    --skip-scale) SKIP_SCALE=1; shift ;;
    --runs) RUNS="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi
if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key." >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  echo "Python 3.10 or later is required (found: $(python3 --version 2>&1))." >&2
  exit 1
fi

OUT="results/$(date +%Y%m%d-%H%M%S)"

echo "== 1/3  Cases: text, images, audio, video and PDFs (standard library only)"
python3 run_cases.py --out "$OUT" --runs "$RUNS" ${ARGS[@]+"${ARGS[@]}"}

if [[ "$SKIP_SCALE" == 0 ]]; then
  echo
  echo "== 2/3  Questions per request: 1, 10, 100 and 1,000 questions on the same input"
  python3 scale.py --out "$OUT" --runs "$RUNS"
fi

python3 report.py "$OUT"

if [[ "$SKIP_SDK" == 0 ]]; then
  echo
  echo "== 3/3  One ticket through the google-genai SDK, attachments uploaded with the Files API"
  if [[ ! -d .venv ]]; then
    echo "Creating .venv and installing requirements.txt ..."
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
  .venv/bin/python sdk_example.py | tee "$OUT/sdk-run.txt"
fi

echo
echo "Done. Results: $OUT/report.md, summary.json, and the raw responses."
