# Agrogami Prism MCP

Prism is a read-only inspection gateway over existing application services and immutable journal records. Official Python MCP SDK 1.30.0, Streamable HTTP `/mcp`, stateless requests, JSON responses. It runs separately on localhost:8001 sharing the API database. No legacy SSE product transport or financial arithmetic exists in tools.

Exactly four product tools:

| Tool | Contract |
|---|---|
| get_evidence_ledger | Accepted event versions and minimized hash/span/region provenance; excludes account IDs, counterparties and transaction references |
| get_assessment_snapshot | Stored status/scope/version/coverage/probabilities/score/limitations; excludes training sample IDs and raw source bytes |
| get_explanation_factors | Stored reasons/TreeSHAP only; no recalculation |
| get_fairness_audit | Stored aggregate fairness; reviewer/admin only; no row-level protected attributes |

Enable AGROGAMI_MCP_ENABLED=true. Configure AGROGAMI_MCP_AUTH_TOKEN (viewer only) and/or the existing AGROGAMI_DEMO_TOKENS role mapping in ignored `.env`. Send Authorization: Bearer with the secret on every request. Missing/invalid credentials return 401 before protocol parsing; fairness requires reviewer/admin. With AGROGAMI_LOCAL_DEMO_MODE=false, nonadmin credentials also need explicit applicant UUID grants through AGROGAMI_APPLICANT_GRANTS. Local demo mode is an explicit localhost synthetic convenience. These static grants are a minimal resource boundary, not production identity or tenant isolation. SDK local host protection is retained. Keep this workbench local.

Start the server separately from the repository root:

```powershell
$env:AGROGAMI_MCP_ENABLED = "true"
.\.venv\Scripts\python.exe -m agrogami.mcp.server
```

The default endpoint is `http://127.0.0.1:8001/mcp`. Override AGROGAMI_MCP_PORT when needed and update the client URL to match. The process speaks Streamable HTTP; starting it as a stdio command is incompatible.

## VS Code connection

The installed VS Code version is 1.140.0. Copy the credential-free example to the ignored local configuration:

```powershell
Copy-Item .vscode/mcp.json.example .vscode/mcp.json
```

The example uses `type: http`, the `/mcp` URL and an Authorization header with a password input. Run **MCP: List Servers**, select **agrogamiPrism**, connect, and supply the configured local secret when prompted. The four tool names above should appear. No secret belongs in either committed examples or the local JSON file; `.vscode/mcp.json` is excluded from Git and Docker contexts. Restart the separately running Prism process after rotating its configured credentials.

VS Code's Agent Host does not forward configurations requiring interactive `${input:...}` values. For that execution mode, use `Bearer ${env:AGROGAMI_MCP_AUTH_TOKEN}` in the ignored configuration, remove `inputs`, and provide the variable to the VS Code process before launching it. A dedicated token remains viewer-only; use a configured reviewer/admin credential when aggregate fairness access is required. See the [official VS Code MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) for HTTP headers, secret inputs and the Agent Host limitation. This schema check does not claim an executed VS Code client connection.

Offline protocol/authorization/minimization tests: tests/integration/test_local_product.py. Live process startup and official SDK initialize/list/read were verified by `python -m scripts.verify_local_runtime`. This internal client is not Codex/Claude/Antigravity external reuse. Manual external-client invocation remains PLANNED. No tool writes evidence, reviews records, retrains, changes scores, recalculates SHAP, decides lending or disburses funds.

CloudCamp BD MCP, supplied by EquiSaaS BD / CloudCamp BD Community, remains external competition guidance only. Its supplied SSE endpoint is not Prism and is not contacted by default tests. Never send applicant evidence, identifiers, events, features, scores, fairness inputs or snapshots there. No external provider invocation or product integration is claimed.

Logs omit financial payloads and tokens. Access logging is disabled and errors are sanitized. Production identity/isolation/consent/retention/rate limiting remain absent. Official reference: [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).
