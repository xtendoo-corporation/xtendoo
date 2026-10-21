"""Test-only toolbox.

``_xtd_ai_test_only = True`` makes the registry ignore this model unless Odoo
runs with ``--test-enable``, so these tools never exist in a normal server.
"""

from odoo import models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError

from ..tools import xtd_ai_tool
from ..tools.errors import XtdAiDraftOnlyError, XtdAiToolError

_ERRORS = [
    "access",
    "user",
    "validation",
    "missing",
    "not_found",
    "ambiguous",
    "internal",
    "draft",
]


class XtdAiToolboxTest(models.AbstractModel):
    _name = "xtd.ai.toolbox.test"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: tests only"

    _xtd_ai_test_only = True
    _xtd_ai_skills = {"test_skill": "data/skills/contactos.md"}

    @xtd_ai_tool(
        name="zz_test_echo",
        title="Echo",
        description="Test tool: echoes its arguments.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "maxLength": 20}},
            "required": ["text"],
            "additionalProperties": False,
        },
        kind="read",
    )
    def tool_zz_test_echo(self, args):
        return {"data": {"echo": args["text"]}, "records": []}

    @xtd_ai_tool(
        name="zz_test_env",
        title="Env",
        description="Test tool: reports the execution env.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        kind="read",
    )
    def tool_zz_test_env(self, args):
        return {
            "data": {
                "uid": self.env.uid,
                "su": self.env.su,
                "allowed_company_ids": self.env.context.get("allowed_company_ids"),
                "xtd_ai_run": self.env.context.get("xtd_ai_run"),
            },
            "records": self.env.user,
        }

    @xtd_ai_tool(
        name="zz_test_error",
        title="Error",
        description="Test tool: raises an error.",
        input_schema={
            "type": "object",
            "properties": {"kind": {"type": "string", "enum": _ERRORS}},
            "required": ["kind"],
            "additionalProperties": False,
        },
        kind="read",
    )
    def tool_zz_test_error(self, args):
        kind = args["kind"]
        if kind == "access":
            raise AccessError(self.env._("no access"))
        if kind == "user":
            raise UserError(self.env._("user error"))
        if kind == "validation":
            raise ValidationError(self.env._("invalid"))
        if kind == "missing":
            raise MissingError(self.env._("gone"))
        if kind == "not_found":
            raise XtdAiToolError("not_found", "nothing")
        if kind == "ambiguous":
            raise XtdAiToolError("ambiguous", "many", data={"candidates": [{"id": 1}]})
        if kind == "draft":
            raise XtdAiDraftOnlyError("draft only")
        raise RuntimeError("secret internal detail")

    @xtd_ai_tool(
        name="zz_test_guard",
        title="Guard",
        description="Test tool: tries to delete a partner.",
        input_schema={
            "type": "object",
            "properties": {"partner_id": {"type": "integer"}},
            "required": ["partner_id"],
            "additionalProperties": False,
        },
        kind="read",
    )
    def tool_zz_test_guard(self, args):
        self.env["res.partner"].browse(args["partner_id"]).unlink()
        return {"data": {}, "records": []}

    @xtd_ai_tool(
        name="zz_test_manager_only",
        title="Manager",
        description="Test tool: managers only.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        kind="read",
        groups=["xtd_ai_gateway.group_xtd_ai_manager"],
    )
    def tool_zz_test_manager_only(self, args):
        return {"data": {"ok": True}, "records": []}

    @xtd_ai_tool(
        name="zz_test_draft",
        title="Draft",
        description="Test tool: creates a partner tag.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 50}},
            "required": ["name"],
            "additionalProperties": False,
        },
        kind="draft",
        preview="_xtd_ai_preview_zz_test_draft",
    )
    def tool_zz_test_draft(self, args):
        tag = self.env["res.partner.category"].create({"name": args["name"]})
        return {"data": {"id": tag.id}, "records": tag}

    def _xtd_ai_preview_zz_test_draft(self, args):
        return {"summary": f"Create tag {args['name']}", "lines": []}

    @xtd_ai_tool(
        name="zz_test_create",
        title="Create",
        description="Test tool: creates a partner tag.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 50}},
            "required": ["name"],
            "additionalProperties": False,
        },
        kind="create",
        preview="_xtd_ai_preview_zz_test_draft",
    )
    def tool_zz_test_create(self, args):
        tag = self.env["res.partner.category"].create({"name": args["name"]})
        return {"data": {"id": tag.id}, "records": tag}
