from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .xtd_ai_policy import (
    FIXED_CLASSES,
    FLOOR,
    LEVEL_LABELS,
    LEVELS,
    OP_CLASS_LABELS,
    POLICY_TABLE,
    max_level,
)


class XtdAiPolicyRule(models.Model):
    """Row of the policy table of a company (ANALISIS_PERMISOS §6.1, §6.5).

    An operation-class row may harden the profile or relax it down to the
    Ágil floor; a tool row can only harden. Fixed classes (read, publish,
    pay, administration) are shown but cannot be edited.
    """

    _name = "xtd.ai.policy.rule"
    _description = "AI agent policy table row"
    _order = "company_id, sequence, op_class, tool_name"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.company,
    )
    sequence = fields.Integer(default=10)
    op_class = fields.Selection(
        list(OP_CLASS_LABELS.items()), string="Clase de operación"
    )
    tool_name = fields.Selection(selection="_selection_tool_name", string="Herramienta")
    level = fields.Selection(
        [(lvl, LEVEL_LABELS[lvl]) for lvl in LEVELS if lvl != "N0"],
        string="Nivel elegido",
        help="Vacío: el del perfil de la compañía.",
    )
    profile_level = fields.Selection(
        list(LEVEL_LABELS.items()),
        string="Nivel del perfil",
        compute="_compute_levels",
    )
    effective_level = fields.Selection(
        list(LEVEL_LABELS.items()),
        string="Nivel aplicado",
        compute="_compute_levels",
    )
    editable = fields.Boolean(compute="_compute_levels")

    _class_unique = models.Constraint(
        "UNIQUE(company_id, op_class)", "Esa clase ya está en la tabla."
    )
    _tool_unique = models.Constraint(
        "UNIQUE(company_id, tool_name)", "Esa herramienta ya está en la tabla."
    )

    @api.model
    def _selection_tool_name(self):
        tools = self.env["xtd.ai.toolbox"]._xtd_ai_tools()
        return sorted(
            (name, f"{tool['title']} ({name})")
            for name, tool in tools.items()
            if tool["kind"] != "read" and not name.startswith("zz_test")
        )

    @api.depends("op_class", "tool_name", "level", "company_id.xtd_ai_profile")
    def _compute_levels(self):
        policy = self.env["xtd.ai.policy"]
        for row in self:
            company_policy = policy.with_company(row.company_id)
            if row.op_class:
                row.profile_level = company_policy._xtd_ai_profile_level(row.op_class)
                row.effective_level = company_policy._xtd_ai_level(row.op_class)
                row.editable = row.op_class not in FIXED_CLASSES
            else:
                row.profile_level = False
                row.effective_level = row.level or False
                row.editable = True

    @api.constrains("op_class", "tool_name", "level")
    def _check_rule(self):
        for row in self:
            if bool(row.op_class) == bool(row.tool_name):
                raise ValidationError(
                    self.env._(
                        "Cada fila es de una clase de operación o de una herramienta."
                    )
                )
            if row.op_class and row.level:
                if row.op_class in FIXED_CLASSES:
                    raise ValidationError(
                        self.env._(
                            "«%(op)s» no se puede cambiar: está fijado en %(level)s.",
                            op=OP_CLASS_LABELS[row.op_class],
                            level=POLICY_TABLE[row.op_class][0],
                        )
                    )
                floor = FLOOR[row.op_class]
                if max_level(row.level, floor) != row.level:
                    raise ValidationError(
                        self.env._(
                            "«%(op)s» no puede bajar de %(floor)s.",
                            op=OP_CLASS_LABELS[row.op_class],
                            floor=floor,
                        )
                    )

    @api.model
    def _xtd_ai_ensure_rows(self, company):
        """One row per operation class for ``company`` (shown in the table)."""
        existing = set(
            self.search([("company_id", "=", company.id)]).mapped("op_class")
        )
        self.create(
            [
                {"company_id": company.id, "op_class": op, "sequence": i}
                for i, op in enumerate(POLICY_TABLE)
                if op not in existing
            ]
        )

    @api.model
    def action_xtd_ai_open_table(self):
        company = self.env.company
        self._xtd_ai_ensure_rows(company)
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Tabla de políticas del agente IA"),
            "res_model": self._name,
            "view_mode": "list",
            "domain": [("company_id", "=", company.id)],
            "context": {"default_company_id": company.id},
            "target": "current",
        }
