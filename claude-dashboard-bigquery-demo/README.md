# Claude Dashboards + BigQuery Sandbox demo

Bootstrap a zero-billing BigQuery Sandbox project with a curated view over
Google's public NYC Citi Bike dataset. Use that view as a safe, public-data
source for evaluating Claude Dashboards.

## What this does

- Creates or reuses a Google Cloud project you name.
- Enables the BigQuery API without enabling billing.
- Creates `claude_demo.citibike_dashboard_source`, a view over the public
  Citi Bike dataset.
- Runs a capped validation query (5 GB maximum processed).

It does **not** automate Claude, connect a Claude account, enable Google Cloud
billing, or create a service-account key. Claude Dashboards is currently a web
product feature, so connecting the warehouse and creating the dashboard remain
interactive steps.

## Prerequisites

- A Claude Pro, Max, Team, or Enterprise account with Dashboards available.
- Google Cloud CLI with the `gcloud` and `bq` commands.
- A Google account that can create a Google Cloud project.

### Install Google Cloud CLI on Ubuntu/Debian

The script requires both `gcloud` and `bq`; the official `google-cloud-cli`
package provides both. These commands add Google's APT repository and install
the package, so review them before running:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update
sudo apt-get install -y google-cloud-cli
```

Verify the installation before running the demo:

```bash
gcloud version
bq version
```

For another operating system or current alternatives, use Google's official
[Cloud CLI installation guide](https://cloud.google.com/sdk/docs/install).

## Run

```bash
./setup-demo.sh --project-id YOUR-UNIQUE-PROJECT-ID
```

For example:

```bash
./setup-demo.sh --project-id claude-dash-albin26
```

The script opens Google sign-in if no active `gcloud` account exists. In
Claude, connect BigQuery, create an **Artifacts → Dashboard** artifact,
replace `PROJECT_ID` in [`dashboard-prompt.txt`](dashboard-prompt.txt), and
submit that prompt.

### Connect BigQuery in Claude

Creating the BigQuery project does not connect it to Claude. In Claude's left
sidebar, open **Customize**, then **Connectors**, search for **BigQuery**, and
select **Google Cloud BigQuery** (the connector published by Google). Complete
the Google authorization flow using the account that owns the demo project.
After it appears as connected, create a Dashboard artifact. In that dashboard
chat, open the composer **+ → Connectors** and turn on **Google Cloud BigQuery**
before submitting the prompt.

If the BigQuery connector is absent from the Connectors list, stop there: the
Dashboard artifact is available, but that account does not currently have the
warehouse connector available. This is a Claude beta/availability issue, not a
failure of the setup script. Do not work around it by pasting credentials into
Claude or downloading data from arbitrary links. Check Claude's connectors
catalog or support for the account's current availability.

## Guardrails

- Use a demo-only project; do not point the script at production.
- Review every SQL query Claude generates before relying on its result.
- Avoid service-account keys. If the connector explicitly requires a service
  account, use `--service-account`; this creates no key and grants only
  BigQuery Job User. Grant further access only when the connector documents a
  specific requirement.

## Further reading

- [Claude Dashboards setup guide](https://support.claude.com/en/articles/17454700-get-started-with-claude-dashboards)
- [BigQuery Sandbox documentation](https://cloud.google.com/bigquery/docs/sandbox)
