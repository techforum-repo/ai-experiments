#!/usr/bin/env bash
# Bootstrap a no-cost BigQuery Sandbox project for a Claude Dashboards demo.
# This script never enables billing and never creates a service-account key.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./setup-demo.sh --project-id PROJECT_ID [--project-name "Name"] [--service-account]

Creates (or reuses) a Google Cloud project without enabling billing, enables
BigQuery, creates the claude_demo dataset in US, and creates a read-only view
over Google's public NYC Citi Bike dataset.

Options:
  --project-id ID       Required. Google Cloud project ID (6-30 lowercase
                        letters, digits, or hyphens; must be globally unique).
  --project-name NAME   Display name for a newly-created project.
  --service-account     Create a connector service account and grant only the
                        BigQuery Job User role. No key is generated.
  -h, --help            Show this help.

Before running: install the Google Cloud CLI (including bq) and sign in with
an account allowed to create projects. The BigQuery Sandbox does not require a
credit card. Ubuntu/Debian installation instructions are in README.md and at
https://cloud.google.com/sdk/docs/install. Do not run this against a production
project.
EOF
}

PROJECT_ID=""
PROJECT_NAME="Claude Dashboards Demo"
CREATE_SERVICE_ACCOUNT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id) PROJECT_ID="${2:-}"; shift 2 ;;
    --project-name) PROJECT_NAME="${2:-}"; shift 2 ;;
    --service-account) CREATE_SERVICE_ACCOUNT=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || { echo "--project-id is required." >&2; exit 2; }
[[ "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || {
  echo "Invalid project ID: $PROJECT_ID" >&2; exit 2;
}

for command in gcloud bq; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing required command: $command" >&2
    echo "Install Google Cloud CLI (it includes both gcloud and bq), then retry:" >&2
    echo "  https://cloud.google.com/sdk/docs/install" >&2
    echo "For Ubuntu/Debian commands, see README.md in this folder." >&2
    exit 1
  }
done

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "No active Google Cloud login found. Opening Google sign-in..."
  gcloud auth login
fi

if gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  echo "Using existing project: $PROJECT_ID"
else
  echo "Creating project: $PROJECT_ID"
  gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"
fi

echo "Enabling the BigQuery API (this does not enable billing)..."
gcloud services enable bigquery.googleapis.com --project="$PROJECT_ID"

if bq --project_id="$PROJECT_ID" --location=US show --dataset "$PROJECT_ID:claude_demo" >/dev/null 2>&1; then
  echo "Using existing dataset: $PROJECT_ID:claude_demo"
else
  echo "Creating US dataset: $PROJECT_ID:claude_demo"
  bq --project_id="$PROJECT_ID" --location=US mk --dataset --description \
    "Demo-only views for Claude Dashboards" "$PROJECT_ID:claude_demo"
fi

echo "Creating the dashboard source view..."
bq --project_id="$PROJECT_ID" --location=US query --nouse_legacy_sql \
  "CREATE OR REPLACE VIEW \`$PROJECT_ID.claude_demo.citibike_dashboard_source\` AS
   SELECT
     DATE(starttime) AS trip_date,
     EXTRACT(YEAR FROM starttime) AS trip_year,
     EXTRACT(MONTH FROM starttime) AS trip_month,
     FORMAT_DATE('%A', DATE(starttime)) AS weekday_name,
     EXTRACT(DAYOFWEEK FROM starttime) IN (1, 7) AS is_weekend,
     SAFE_DIVIDE(tripduration, 60.0) AS trip_duration_minutes,
     start_station_name,
     start_station_latitude,
     start_station_longitude,
     ST_GEOGPOINT(start_station_longitude, start_station_latitude) AS start_geo,
     usertype
   FROM \`bigquery-public-data.new_york.citibike_trips\`
   WHERE starttime IS NOT NULL;"

echo "Validating that the view can be queried..."
bq --project_id="$PROJECT_ID" --location=US query --nouse_legacy_sql \
  --maximum_bytes_billed=5000000000 --format=pretty \
  "SELECT trip_year, COUNT(*) AS trips
   FROM \`$PROJECT_ID.claude_demo.citibike_dashboard_source\`
   GROUP BY trip_year
   ORDER BY trip_year;"

if [[ "$CREATE_SERVICE_ACCOUNT" == true ]]; then
  SERVICE_ACCOUNT="claude-dashboard-demo@$PROJECT_ID.iam.gserviceaccount.com"
  if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "Creating service account: $SERVICE_ACCOUNT"
    gcloud iam service-accounts create claude-dashboard-demo --project="$PROJECT_ID" \
      --display-name="Claude Dashboards demo connector"
  fi
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.jobUser" >/dev/null
  echo "Service account created with BigQuery Job User only: $SERVICE_ACCOUNT"
  echo "Do not create a key unless Claude's connector explicitly requires one."
fi

cat <<EOF

Setup complete.

In Claude Pro, connect BigQuery using this project, then select Dashboards and
ask Claude to use:
  $PROJECT_ID.claude_demo.citibike_dashboard_source

See dashboard-prompt.txt for the ready-to-paste prompt. Review every generated
SQL query before treating the result as authoritative.
EOF
