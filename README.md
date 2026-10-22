# AI Experiments

Small, self-contained AI experiments and demos — each folder runs on its own and has its
own setup notes. Copy `.env.example` to `.env` in a folder before running it.

| Folder | What it is |
|---|---|
| [claude-dashboard-bigquery-demo](claude-dashboard-bigquery-demo/) | Claude Dashboards over a zero-billing BigQuery Sandbox view of the public NYC Citi Bike dataset |
| [coveo-crga-atomic-local](coveo-crga-atomic-local/) | Local Coveo Atomic search page loaded from Coveo's CDN |
| [edge-ai-my-profile](edge-ai-my-profile/) | Cloudflare Worker powering the portfolio's AI routes: RAG chat, contact-form analysis, visitor personalization |
| [openai-agents-api](openai-agents-api/) | Live tests of OpenAI's Agents API sandbox sessions, verified against computed ground truth |
| [openai-decision-api-triage](openai-decision-api-triage/) | DAM asset-intake triage with the OpenAI Decisions API, using image and text input |

Adobe-specific tools (`cja-mcp`, `target-mcp`) moved to
[martech-architect-toolkit](https://github.com/techforum-repo/martech-architect-toolkit).
`openai-agents-api` came from the now-archived `ai-agents-experimentation` repo, history included.
