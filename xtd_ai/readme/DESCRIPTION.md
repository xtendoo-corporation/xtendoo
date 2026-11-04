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

**Data retention (GDPR / LOPDGDD)**: the GDPR sets no number of days; it requires
data minimisation and storage limitation (art. 5.1.c and 5.1.e). By default
conversations (which hold the user's free text) are deleted after 90 days without
activity (last message, run or card; never while a run is in progress or a card is
pending) and the audit log after 180 days, the usual period for security logs. Both
are configurable (`xtd_ai.conversation_retention_days`,
`xtd_ai.audit_retention_days`, minimum 30 days) and purged by daily crons in bounded
batches. The audit log keeps tool, record ids, outcome and error; emails, IBAN,
NIF/CIF/NIE and phone numbers in the arguments are obfuscated (short prefix) before
being stored. Free-text names cannot be detected and are bounded by the short period.
