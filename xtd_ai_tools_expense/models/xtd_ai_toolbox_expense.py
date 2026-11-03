from odoo import models

from odoo.addons.xtd_ai.tools import xtd_ai_tool


class XtdAiToolboxExpense(models.AbstractModel):
    _name = "xtd.ai.toolbox.expense"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: own expenses"

    _xtd_ai_skills = {"gastos": "data/skills/gastos.md"}
    # area of the request (§6.5): models of the screen and words of the message
    _xtd_ai_skill_hints = {
        "gastos": {
            "models": ("hr.expense", "hr.expense.sheet"),
            "words": (
                "gasto",
                "ticket",
                "dieta",
                "kilometraje",
                "taxi",
                "parking",
                "restaurante",
                "comida",
            ),
        }
    }

    @xtd_ai_tool(
        name="my_expenses",
        title="Mis gastos",
        description=(
            "Gastos del PROPIO usuario: por defecto los borradores (los que aún se "
            "pueden corregir con update_record). Devuelve id, fecha, descripción, "
            "categoría, importe, estado y si lleva ticket. No modifica datos."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["draft", "all"],
                    "description": "draft (por defecto) o all.",
                }
            },
            "required": [],
            "additionalProperties": False,
        },
        kind="read",
        skill="gastos",
    )
    def tool_my_expenses(self, args):
        domain = [("employee_id.user_id", "=", self.env.uid)]
        if args.get("state", "draft") == "draft":
            domain.append(("state", "=", "draft"))
        expenses = self.env["hr.expense"].search(
            domain, order="date desc, id desc", limit=self._xtd_ai_limit(None)
        )
        rows = [
            {
                "id": exp.id,
                "date": str(exp.date) if exp.date else None,
                "name": self._xtd_ai_text(exp.name),
                "category": exp.product_id.name or None,
                "total": self._xtd_ai_money(exp.total_amount_currency, exp.currency_id),
                "state": exp.state,
                "has_receipt": bool(exp.nb_attachment),
            }
            for exp in expenses
        ]
        return {"data": self._xtd_ai_list(rows), "records": expenses}
