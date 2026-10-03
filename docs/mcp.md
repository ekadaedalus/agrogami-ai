# Agrogami Prism MCP

Prism is a read-only inspection gateway over existing application services and immutable journal records. Official Python MCP SDK 1.30.0, Streamable HTTP `/mcp`, stateless requests, JSON responses. It runs separately on localhost:8001 sharing the API database. No legacy SSE product transport or financial arithmetic exists in tools.

Exactly four product tools:

| Tool | Contract |
|---|---|
| get_evidence_ledger | Accepted event versions and minimized hash/span/region provenance; excludes account IDs, counterparties and transaction references |
| get_assessment_snapshot | Stored status/scope/version/coverage/probabilities/score/limitations; excludes training sample IDs and raw source bytes |
| get_explanation_factors | Stored reasons/TreeSHAP only; no recalculation |
| get_fairness_audit | Stored aggregate fairness; reviewer/admin only; no row-level protected attributes |

Enable AGROGAMI_MCP_ENABLED=true. Configure AGROGAMI_MCP_AUTH_TOKEN (viewer only) and/or the existing AGROGAMI_DEMO_TOKENS role mapping. Send Authorization: Bearer with the secret on every request. Missing/invalid credentials return 401 before protocol parsing; fairness requires reviewer/admin. Local demo access is dataset-wide, not applicant-scoped production authorization. SDK local host protection is retained. Keep this prototype local.

Run `.\.venv\Scripts\python.exe -m agrogami.mcp.server`.

Offline protocol/authorization/minimization tests: tests/integration/test_local_product.py. Live process startup and official SDK initialize/list/read were verified by `python -m scripts.verify_local_runtime`. This internal client is not Codex/Claude/Antigravity external reuse. Manual external-client invocation remains PLANNED. No tool writes evidence, reviews records, retrains, changes scores, recalculates SHAP, decides lending or disburses funds.

CloudCamp BD MCP, supplied by EquiSaaS BD / CloudCamp BD Community, remains external competition guidance only. Its supplied SSE endpoint is not Prism and is not contacted by default tests. Never send applicant evidence, identifiers, events, features, scores, fairness inputs or snapshots there. No external provider invocation or product integration is claimed.

Logs omit financial payloads and tokens. Access logging is disabled and errors are sanitized. Production identity/isolation/consent/retention/rate limiting remain absent. Official reference: [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).
