# Research review: choosing and verifying an Agents API sandbox

Researched September 15, 2026. Scope: the `picking-a-sandbox.html` draft and this directory's Python sample. This is a documentation and static-code review; no new live API trials were run. The five results in the original README are author-reported observations, not independently reproduced results from this review. The default local Python interpreter does not have `openai` installed.

## Recommendation

**Title: OpenAI Agents API: Choosing a Sandbox and Checking Its Work**

Suggested subtitle: *Who runs the agent, where its code executes, and how to verify the files it produces—with a reproducible reconciliation example.*

The article's strongest contribution is a practical decision followed by evidence a reader can inspect. Keep the three environment choices, shorten the configuration inventory, and make a checked artifact the center of the walkthrough. A broad provider comparison would need comparable live runs; the current sample only exercises `openai_hosted`.

Alternative titles:

- **Where Your OpenAI Agent Runs—and How to Verify the Result** — more accessible.
- **From a Messy CSV to a Verified Report with the OpenAI Agents API** — best if the walkthrough becomes most of the article.
- **Choosing an Execution Environment for the OpenAI Agents API** — best for an architecture-only article with the experiment as a sidebar.

## 1. What the official sources establish

### Runtime ownership

The September 10 announcement establishes the public-beta launch and Codex harness relationship. Use that primary source rather than a recap for launch claims. Avoid changing the claim to an exact identity with every ChatGPT agent-mode implementation. [OpenAI announcement](https://openai.com/index/introducing-the-agents-api/)

The application chooses the environment. OpenAI runs the managed harness. With `none`, function handlers can still execute application code and remote MCP servers can do work. What is absent is the environment filesystem, built-in Bash/apply-patch execution, and executor MCPs. Therefore, “nobody runs code” is misleading. [Architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)

The relevant runtime comparison is Agents API versus Agents SDK versus Responses API: managed harness, an SDK runner in your application, or direct integration with model responses. SDK sessions and Responses Conversations also support state; “you manage state in your own process” is too restrictive. [Runtime comparison](https://developers.openai.com/api/docs/guides/agents)

Responses also offers hosted shell execution. Sandbox access alone does not explain why a workload needs the Agents API. The article should explain why managed sessions and orchestration matter to its example. [Responses shell guide](https://developers.openai.com/api/docs/guides/tools-shell)

### Hosted configuration and lifetime

The hosted guide supports the draft's package, setup, file, environment-variable, skills, plugin, and capability-directory descriptions. Important additions/corrections:

- Network access defaults to enabled unless a template supplies a policy.
- Restricted access uses exact hosts; redirect destinations and subdomains need entries.
- Template overrides cannot broaden the template's network policy.
- Packages and seeded files precede setup commands; setup failure prevents startup.
- Templates preserve configuration, not a running filesystem.
- Connected sandboxes receive keep-alives between turns. Expiration can follow an hour without activity **and** keep-alives; it is not simply an hour after creation or an hour after a turn ends.
- Hosted deletion can return `409`; use bounded retries and preserve results first.

Call the table “settings used in this guide,” or “hosted configuration at the time of writing,” rather than promising every future configuration knob. [Hosted sandbox guide](https://developers.openai.com/api/docs/guides/agents-api/environments/openai-hosted)

### Output retrieval differs by environment

OpenAI publishes hosted files under `/workspace/outputs` as immutable artifacts. Self-hosted files do **not** use the Artifacts API—even at that same path. Retrieve them through provider file APIs or your own storage. Match a hosted artifact by both path and turn ID. Published copies survive sandbox expiration; download them before session deletion.

Current documented limits include 50 initial files; 5 MiB per inline file and 10 MiB combined inline content before base64; 50 MiB per Files API input; 200 MiB per published artifact and 500 MiB combined output. Link these limits rather than making them the main article. [Files and artifacts](https://developers.openai.com/api/docs/guides/agents-api/environments/files)

### Self-hosted does not mean the full agent is local

The executor runs commands and file operations in your environment, while the harness remains hosted. Start it with the returned remote URL **and environment ID**. It uses outbound connections and a separate restricted environment key; keep the broader application key outside the sandbox. [Self-hosted guide](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted)

The API currently retains session state, supports US data residency only, and does not support Zero Data Retention. Self-hosting does not make this API ZDR-eligible. Replace the table's broad “compliance” recommendation with specific needs such as a custom image or private-network access, and state this limitation. [Agents API overview](https://developers.openai.com/api/docs/guides/agents-api/overview)

Network restrictions must be understood per connection: executor MCP traffic originates in your environment; remote MCP traffic originates in OpenAI's service. “Network disabled” is not a universal claim about all tool traffic. [Sandbox security](https://developers.openai.com/api/docs/guides/agents-api/environments/security)

### Session, turn, and environment are different states

Session status is `idle`, `in_progress`, `requires_action`, or `failed`. The draft is correct that a session has no `completed` status. [Session reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/retrieve)

A turn record can be queued before execution starts; the reference exposes separate `created_at`, `started_at`, and `completed_at` fields. A newly visible turn is not necessarily a started calculation. [Turn reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/subresources/turns/methods/list)

An idle-session input starts a turn; active-turn input steers ongoing work. Keep this explanation, with a direct citation. [Sessions guide](https://developers.openai.com/api/docs/guides/agents-api/sessions)

Streams do not replay missed events. Reconnect, buffer new events, retrieve session/items, then reconcile by item ID. This restores the application's view; it does not promise recovery of every interrupted command. The draft's diagram is broadly useful but its following paragraph confuses events/items with streams/webhooks. [Events and items](https://developers.openai.com/api/docs/guides/agents-api/sessions/events)

Webhook `agent.session.action_required` and stream `agent.session.requires_action` use different names. Inspect the required action: a function result and an environment connection require different responses. A completed turn can contain failed tool calls. [Webhooks](https://developers.openai.com/api/docs/guides/agents-api/sessions/webhooks)

A session can outlive its compute. Use one lifecycle owner, check current state before provisioning or shutdown, and manage provider teardown separately from session deletion. An idle event is insufficient to safely stop compute. Replacement compute does not restore old files merely by reusing an environment ID. [Sandbox lifecycle](https://developers.openai.com/api/docs/guides/agents-api/environments/lifecycle)

### Incident and cost claims

The linked incident is real and describes turn-start delays beginning September 14 at 13:30 Pacific. That time is the reported **onset**, not the publication time of the initial status update. The page displays mitigation and resolution updates at 23:28 and 23:39. Its rendered timestamps do not explicitly label their timezone, so verify that conversion before publishing a fully Pacific timeline. The public incident supports a matching symptom, not proof that every local failure had that cause. [Incident record](https://status.openai.com/incidents/01M2H3J1D6Y7RHAP49GRWGJAY0)

The sample should record token usage and compute assumptions. The pricing page lists container charges per 20-minute session, with rates depending on memory. Do not infer an exact trial cost from elapsed time alone. [Pricing](https://developers.openai.com/api/docs/pricing)

The Assistants shutdown date in the draft matches the deprecations page, but that history can be one sentence or omitted. [Deprecations](https://developers.openai.com/api/docs/deprecations)

## 2. What other posts and implementations add

These sources were read for editorial positioning and implementation examples. Official documentation remains the authority for API semantics. Provider performance statements were not independently benchmarked.

| Source | Useful contribution | How to use it |
| --- | --- | --- |
| [Vercel reference implementation](https://github.com/vercel-labs/openai-agents-api-vercel) | Concrete application, queue, webhook, and sandbox integration. Reads current state and uses deterministic naming and locking for repeated provisioning requests. | Link as the larger deployment follow-up; do not add this much infrastructure to the small Python demo. |
| [Daytona guide](https://www.daytona.io/docs/en/guides/openai/openai-agents-api-self-hosted-sandbox/) | Clear application-managed executor setup, connection flow, and cleanup sections. | Useful runnable alternative when explaining what a self-hosted integration actually requires. |
| [E2B workbench](https://e2b.dev/resources/build-an-agent-workbench-on-openais-agents-api) | Per-chat sandbox ownership, prepared templates, workspace visibility, and follow-up sessions. | Inspiration for inspectable output. Its cold-start claim is not comparable to your observed turn-appearance timings. |
| [Cloudflare tutorial](https://developers.cloudflare.com/sandbox/tutorials/openai-agents-api/) | Worker/Durable Object ownership, signed webhooks, stopping and restoring compute. Snapshot access is currently private beta; snapshots are not durable backups. | Good second article if you want a Cloudflare continuation. Verify account feature access first. |
| [General Analysis lifecycle article](https://generalanalysis.com/guides/openai-agents-api-sandbox-lifecycle) | Organizes the discussion around lifecycle ownership and separate cleanup operations. | Useful editorial model for explaining application responsibilities; its API claims should cite OpenAI directly. |
| [PacketNebula overview](https://packetnebula.com/articles/openai-agents-api-beta-no-fee-no-zdr-one-hour-sandbox/) | Leads with cost, retention, and lifetime limitations. | Shows that another generic overview adds little. Its headline shorthand about an idle timeout needs the keep-alive qualification found in the docs and its own FAQ. |

The exact Tech Insider article linked by the draft could not be fetched, and a targeted search did not recover it. This does not prove the page never existed. Remove its quote and “independently confirmed” framing until it can be checked; the official session reference already supports the useful point. A Muddaser quickstart was found in search but its page also failed retrieval, so it is not evidence for this review.

The distinct opportunity for this post is **a small, reproducible task with saved inputs, execution evidence, and independently checked outputs**. The official hosted guide already demonstrates summing a CSV into `summary.json`; randomizing six rows is a useful smoke-test extension, but a limited new use case.

## 3. Static review of the sample code

Locations refer to the original runner reviewed on September 15; the shared implementation is now `sandbox_check.py`.

### Fix before sharing

1. **The 180-second limit does not bound the full operation.** Lines 94–105 create the session before starting the clock; synchronous requests can also block inside the polling loop. Lines 125 and 147 exclude artifact retrieval from elapsed time. Start timing before create; set explicit request timeouts/retry behavior; report creation, observed turn, completion, download, and verification separately. The SDK documents a ten-minute default request timeout and automatic retries. [SDK behavior](https://github.com/openai/openai-python#timeouts)

2. **A failed trial is reported as a successful process exit.** `run()` at line 168 prints failures but returns normally. CI and shell callers can see exit code zero when all calculations fail. Return a nonzero exit code when any required verification fails; reject zero or negative trial counts.

3. **Failures are conflated and exceptions abort the batch.** Lines 110–133 ignore required actions and classify “no observed turn” without preserving the session error. Lines 187–202 diagnose a reproduced bug or resolution from those counters. Record session/environment/turn status and errors. Distinguish create/request failure, setup failure, action required, no turn observed by deadline, turn failure/cancellation, missing artifact, invalid JSON, and wrong result. Preserve a per-trial outcome when an API request raises.

4. **There is no cleanup.** `run_trial()` has multiple exits without cancelling unfinished work or deleting sessions. Use a bounded cleanup path after saving evidence and artifacts, and record cleanup failures without hiding the original error. A client timeout is not server-side cancellation.

5. **The experiment does not verify the claimed execution method.** Lines 141–153 download a JSON value and compare it. That verifies a result artifact, not that Python performed the arithmetic or that the cleaning rules were followed. Random numbers do not prove execution. Save generated code and inspect corresponding command calls/results. Keep separate checks for execution evidence, artifact presence, and output correctness. The API supports inspection of saved work and command execution. [Observability](https://developers.openai.com/api/docs/guides/agents-api/observability)

6. **Money uses float arithmetic and a tolerance.** Lines 69–86 generate float values; line 150 accepts errors smaller than a cent. Use integer cents for fixture generation and reference results, or `Decimal` from strings. Validate the JSON schema and reject booleans, nonfinite values, and extra/missing fields as appropriate. Exact integer comparison is simpler.

7. **Trials are not reproducible.** No seed, original CSV, JSON result file, prompt/config snapshot, SDK version, session/turn/artifact IDs, or command evidence is retained. Save a local run directory and seed. The current results table cannot be regenerated from the checked-in sample alone.

8. **The dependency declaration permits incompatible old SDKs.** `openai>=2.0.0` does not express the version claimed by the article. `openai` 3.13.0 exists, but this review did not install or run it. Pin the version used in the next validated run and record it with the results. [3.13.0 package](https://pypi.org/project/openai/3.13.0/)

### Improve while revising

- Match artifacts by turn ID and path, especially when adding a follow-up turn.
- Replace `export $(cat .env | xargs)` with a direct environment export or an explicitly supported dotenv loader. The current command does not robustly parse dotenv syntax.
- Use `argparse` with positive `--trials`, `--seed`, `--model`, `--timeout`, and `--output-dir` options. Keep the model used in the original results identifiable; do not silently change it while retaining those numbers.
- Guarantee each intended formatting edge case in the fixture. Four random sales can all fall below 1,000, so thousands separators are not guaranteed in every current trial.
- Save errors in machine-readable fields, rather than only stderr. Missing artifacts and invalid content currently leave `error` as `None`.
- Do not describe five successes as production reliability, incident root-cause proof, or a benchmark.

## 4. Recommended example: reconcile two messy exports

**Task:** Compare a synthetic order export with a synthetic settlement export and produce a checked exception report.

This gives a reader a recognizable task with multiple inputs and useful output files. The agent writes transformation code for an unfamiliar export; an independent local verifier checks the result. Once a format and policy are stable, ordinary deterministic ETL may be the better recurring implementation. State that directly.

### Inputs and explicit rules

- `orders.csv`: order ID, customer reference, amount, currency.
- `settlements.csv`: settlement ID, order ID, amount, currency.
- `rules.md`: one currency only in the first version; normalize whitespace and dollar formatting; compare integer cents; skip and report invalid amounts; report duplicate IDs without silently deduplicating; signed refunds are valid; unmatched and mismatched records require explanation.
- A seeded generator injects a known mismatch, a missing settlement, a duplicate, an invalid amount, and a refund. The local oracle knows the injected cases without using the agent's parsing code.

### Required outputs

- `reconciliation.json`: exact totals, row counts, matched IDs, and exceptions with source row references.
- `exceptions.csv`: reviewable discrepancy list.
- `report.md`: brief human-readable summary tied to the structured result.
- `reconcile.py`: code that produced the output.

The host validates exact totals and exception identities, schema, row accounting, and consistency across the files. Save tool-call evidence of running the script. Treat a script file alone as insufficient evidence that it executed.

### Optional second turn

Supply a corrected settlement file and ask the same session to update the report. Download artifacts for the new turn ID and show that the corrected exception disappeared. This demonstrates continuing work with a retained workspace; only claim persistence while that sandbox remains available.

### Alternatives

| Use case | Strength | Tradeoff |
| --- | --- | --- |
| Existing CSV total, hardened | Smallest runnable smoke test | Very close to the official example; does not motivate managed sessions strongly |
| Two-export reconciliation | Best fit for the current article and independent verification | Requires explicit reconciliation policy |
| Synthetic incident-log investigation | Natural multi-file exploration with traceable event evidence | Some conclusions need semantic grading |
| Small bug reproduction and patch | Clear shell/test value for developer readers | More environment setup and supply-chain variability |

These are proposed designs, not live-tested examples or measured provider comparisons.

## 5. Proposed article structure and replacement copy

1. **Open with the task and output.** Show the input files and the checked report.
2. **Who runs what?** Explain application, managed harness, and optional environment in one diagram.
3. **Choose an environment.** Three concise rows with file retrieval and lifecycle responsibility.
4. **Run the hosted example.** Seed files, disable unneeded sandbox network access, submit input.
5. **Check the work.** Track the target turn, inspect execution evidence, download artifacts, validate against the oracle.
6. **What happens on failure?** Deadlines, required actions, failed tools, and cleanup. Keep the incident as a dated sidebar.
7. **When to move execution elsewhere.** Custom image/private network, output retrieval differences, retained managed state.
8. **Reproduce it.** Repository link, pinned setup, saved results, and primary references.

Suggested opening:

> I gave an agent two transaction exports and asked it to explain why their totals disagreed. The useful result was a report I could download and check against known discrepancies. This walkthrough follows that job from environment selection through execution, output verification, and cleanup.

Use that opening only after implementing and running the proposed example. Until then, retain the actual CSV-total experiment and describe it accurately.

Suggested replacement for the current results conclusion:

> In these five recorded trials, the downloaded total matched the reference calculation. The script measured time from the create response to observing a settled session; it excluded session creation and artifact download. These runs demonstrate the tested path on that date. They do not establish a general reliability rate or prove the cause of earlier failures.

Suggested replacement for the incident conclusion:

> The earlier symptoms were consistent with OpenAI's reported turn-start incident. Without retained request-level evidence, I cannot attribute every stuck session to that incident. Check service status alongside the session, environment, and turn errors.

Remove the “held at arm's length” source language, “every configuration knob,” and the claim that random totals cannot be guessed. Replace the blanket Verified badge with separate **documentation checked** and **experiment run** dates. Preserve original results as historical observations; publish fresh numbers only with a fresh run and its evidence.

## 6. Verification before publishing the revision

- Offline checks: fixture oracle, exact arithmetic, malformed JSON, missing artifacts, failed setup, required action, timeout, and cleanup error paths.
- One live smoke run using the pinned dependency, with inputs and evidence saved; repeat only if the article will discuss variation.
- A follow-up run only if the article claims a continued-session workflow.
- Label server timestamps versus client observations and include download time in end-to-end latency.
- Preserve output and evidence before deleting sessions.
- Check HTML on mobile and desktop after changing headings, tables, and diagram labels.

Research limitations: the original run logs and installed SDK used for the reported five trials were not available in the inspected sample. Raw GitHub URLs for the proposed versioned SDK source files failed retrieval; API-shape conclusions above use the official reference instead. No assertion here depends on inaccessible third-party pages.
