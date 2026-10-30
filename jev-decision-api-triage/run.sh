#!/usr/bin/env bash
# Compare TypeSafe Jev and the OpenAI Decisions API on 120 labelled support messages.
#
#   ./run.sh                    every API with a key in .env (Jev, and OpenAI if set)
#   ./run.sh --providers jev    Jev only
#   ./run.sh --runs 3           send each message three times (stability, latency)
#   ./run.sh --limit 10         first 10 messages, for a quick check
#   ./run.sh --skip-sdk         skip step 2 (the TypeSafe SDK example)
#
# Keys come from the environment or from a .env file next to this script
# (copy .env.example to .env and fill it in).
set -euo pipefail

cd "$(dirname "$0")"

SKIP_SDK=0
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-sdk) SKIP_SDK=1; shift ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi
if [[ -z "${TYPESAFE_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "No API key set. Copy .env.example to .env and add TYPESAFE_API_KEY (and optionally OPENAI_API_KEY)." >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  echo "Python 3.10 or later is required (found: $(python3 --version 2>&1))." >&2
  exit 1
fi

echo "== 1/2  Compare: 120 labelled messages against each API (standard library only)"
python3 compare.py ${ARGS[@]+"${ARGS[@]}"}

if [[ "$SKIP_SDK" == 0 && -n "${TYPESAFE_API_KEY:-}" ]]; then
  echo
  echo "== 2/2  One message through the TypeSafe Python SDK"
  if [[ ! -d .venv ]]; then
    echo "Creating .venv and installing requirements.txt ..."
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
  .venv/bin/python sdk_example.py
fi

echo
echo "Done. Results are in the newest folder under results/: report.md, summary.json, and the raw responses."
