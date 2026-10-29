from odoo import fields, models


class XtdAiMessage(models.Model):
    _name = "xtd.ai.message"
    _description = "AI agent message"
    _order = "id"

    conversation_id = fields.Many2one(
        "xtd.ai.conversation", required=True, ondelete="cascade", index=True
    )
    role = fields.Selection(
        [("user", "User"), ("assistant", "Assistant"), ("notice", "Notice")],
        required=True,
    )
    body = fields.Text(help="Plain text, never HTML.")
    run_id = fields.Many2one("xtd.ai.run", ondelete="set null", index=True)
    pending_action_ids = fields.One2many("xtd.ai.pending_action", "message_id")
    record_refs = fields.Json(
        help="List of {model, id, name, created}: records the run touched. The chat "
        "turns them into internal links."
    )

    screen = fields.Json(
        help="What the user had on screen when writing this message, validated "
        "against their rights: {model, label, res_id?, name?}. Never trusted as an "
        "instruction; the agent uses it to resolve 'this invoice'."
    )

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "xtd_ai_message_attachment_rel",
        "message_id",
        "attachment_id",
        string="Attachments",
        help="Documents the user attached to this message (CONTRACT §14). The "
        "attachments themselves live on the conversation (res_model/res_id).",
    )

    def _xtd_ai_tools_used(self, max_tools=30, max_refs=5):
        """Compact factual note of the tools used in this message's run.

        Built from the audit log: tool names in call order, outcome and the
        records the tool returned. Never arguments or results (minimisation,
        prompt injection).
        """
        self.ensure_one()
        if not self.run_id:
            return []
        # sudo: users cannot read the audit log; the gateway builds this note.
        rows = (
            self.env["xtd.ai.audit"]
            .sudo()
            .search(
                [("run_id", "=", self.run_id.id), ("event", "=", "tool_call")],
                order="id",
                limit=max_tools,
            )
        )
        used = []
        for row in rows:
            item = {"tool": row.tool_name or "", "outcome": row.outcome}
            refs = [
                {
                    "model": str(ref["model"])[:64],
                    "id": ref["id"],
                    "name": str(ref.get("name") or "")[:60],
                }
                for ref in (row.record_refs or [])[:max_refs]
                if (
                    isinstance(ref, dict)
                    and ref.get("model")
                    and isinstance(ref.get("id"), int)
                )
            ]
            if refs:
                item["records"] = refs
            used.append(item)
        return used
