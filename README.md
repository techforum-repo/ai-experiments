# AI Experiments

Small, self-contained AI experiments and demos — each folder runs on its own and has its
own setup notes. Copy `.env.example` to `.env` in a folder before running it.

| Folder | What it is |
|---|---|
| [aem-generative-ai-samples](aem-generative-ai-samples/) | Generative AI in AEM: prompt samples and the techforum-generative-ai-aem demo (set `OPENAI_API_KEY`) |
| [agent-design-experiments](agent-design-experiments/) | Reproducible tests of how coding agents behave when they have to work from a design system |
| [albinsblog-webmcp](albinsblog-webmcp/) | Cloudflare Worker exposing the blog to AI agents as a read-only WebMCP endpoint at www.albinsblog.com/mcp (deploy with `wrangler deploy` from this folder) |
| [claude-dashboard-bigquery-demo](claude-dashboard-bigquery-demo/) | Claude Dashboards over a zero-billing BigQuery Sandbox view of the public NYC Citi Bike dataset |
| [coveo-crga-atomic-local](coveo-crga-atomic-local/) | Local Coveo Atomic search page loaded from Coveo's CDN |
| [edge-ai-my-profile](edge-ai-my-profile/) | Cloudflare Worker powering the portfolio's AI routes: RAG chat, contact-form analysis, visitor personalization |
| [jev-decision-api-triage](jev-decision-api-triage/) | Support-request triage with TypeSafe Jev, compared with the OpenAI Decisions API on 120 labelled messages: accuracy, abstention, calibration, option order, latency, cost |
| [lightning-ai-clip](lightning-ai-clip/) | Lightning AI Studio demo: OpenAI CLIP image classification with a Streamlit UI |
| [openai-agents-api](openai-agents-api/) | Live tests of OpenAI's Agents API sandbox sessions, verified against computed ground truth |
| [openai-decision-api-triage](openai-decision-api-triage/) | DAM asset-intake triage with the OpenAI Decisions API, using image and text input |

Adobe-specific tools (`cja-mcp`, `target-mcp`) moved to
[martech-architect-toolkit](https://github.com/techforum-repo/martech-architect-toolkit).
`openai-agents-api`, `agent-design-experiments`, `aem-generative-ai-samples` and `albinsblog-webmcp` came from their now-archived repos with history included;
`lightning-ai-clip` came from the former `lightning.ai` repo (current files only).

## License

[MIT](LICENSE)
