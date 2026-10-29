AI assistant integrated in Odoo (no external service). One module with three layers:

- **Gateway**: security barrier between the agent and Odoo (MCP endpoint, user
  permissions, drafts only, audit log).
- **Agent**: the agent loop runs inside Odoo (Anthropic provider over `requests`),
  executed in background with `queue_job` (thread fallback); settings under Settings →
  Agente IA.
- **Chat**: systray icon, floating window and full-screen app.

Tool modules (`xtd_ai_tools_sale`, `xtd_ai_tools_crm`, `xtd_ai_tools_purchase`,
`xtd_ai_tools_stock`, `xtd_ai_tools_account`) are installed automatically when their
Odoo app is present.
