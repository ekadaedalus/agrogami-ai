# External MCP invocation evidence

These are recorded external-client calls. They are separate from the internal official-SDK tests and the runtime verifier described in [mcp.md](../mcp.md). Only synthetic records were read. No credential, token or endpoint secret is recorded here.

## Agrogami Prism (built)

| Date | Client | Transport | Tool | Input | Observed result |
|---|---|---|---|---|---|
| 2026-10-05 | OpenAI Codex, VS Code extension | Streamable HTTP, `http://127.0.0.1:8001/mcp` | `get_evidence_ledger` | synthetic applicant | Completed call; ledger empty at that time (Codex session log) |
| Undated (before 2026-10-19) | OpenAI Codex, VS Code extension | Streamable HTTP | `get_evidence_ledger` | synthetic applicant `657dea8b-4960-489f-8a3f-9564891ff82c` | One accepted RECEIPT of BDT 100.00, fee 0.00, balance null, superseding a NEEDS_REVIEW version. Team screenshots, held outside the repository and matched against the local database. |
| 2026-10-19 | Claude Code, VS Code extension (project-scoped server, bearer credential) | Streamable HTTP, `http://127.0.0.1:8001/mcp` | `get_evidence_ledger` | synthetic applicant Rahim `600bbe3a-8b59-52ab-99d1-dc12d222b438` | 337 events, all `ACCEPTED` and `MOBILE_MONEY_SMS`: 241 RECEIPT, 53 PAYMENT, 29 SEND_MONEY, 13 CASH_OUT, 1 REVERSAL (242 inflow, 95 outflow). Response keys contained no account ID, counterparty, transaction reference or phone field. |

This makes two external clients, Codex and Claude Code. They use the same endpoint and the same four tool schemas, and neither has client-specific logic.

## CloudCamp BD MCP (used)

| Date | Client | Transport | Call | Observed result |
|---|---|---|---|---|
| 2026-10-19 | Claude Code, VS Code extension | Streamable HTTP. The provider URL contains `/sse`, but the server answers only Streamable HTTP; a legacy SSE connection timed out. | `resources/list`, then `resources/read` of `cloudcamp://knowledge-base` | Server `cloudcamp-mcp` v1.29.0. One resource: the International AI Builders Congress 2026 master knowledge base, 32,000 characters, SHA-256 `65d7e23acb84ef604fcd10d7a18625d6fe334d49940bc7309f0b3bcc8deef950`. |

Nothing from Agrogami was sent to CloudCamp. That covers applicant evidence, identifiers, events, features, scores, explanations, fairness inputs and Prism output. The knowledge base was used only to check the competition submission's fields, character minimums and scoring rubric.

The knowledge base says the one-prompt rule also covers Idea to Unicorn. The official portal FAQ limits it to Zero to Launch. Where the two disagree, the portal is authoritative.
