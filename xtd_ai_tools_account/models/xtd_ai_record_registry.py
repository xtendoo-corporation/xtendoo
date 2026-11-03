from odoo import api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiToolError

# Only draft documents the agent prepares: invoices, bills and manual entries
_MOVE_TYPES = ("out_invoice", "out_refund", "in_invoice", "in_refund", "entry")


class XtdAiRecordRegistry(models.AbstractModel):
    _inherit = "xtd.ai.record.registry"

    @api.model
    def _xtd_ai_record_specs(self):
        specs = super()._xtd_ai_record_specs()
        specs["account.move"] = {
            "label": self.env._("factura o asiento en borrador"),
            "skill": "contabilidad",
            "create": False,
            "update": True,
            "domain": [("state", "=", "draft"), ("move_type", "in", _MOVE_TYPES)],
            "fields": {
                "invoice_date": {
                    "label": self.env._("Fecha de factura"),
                    "risk": "low",
                },
                "invoice_date_due": {
                    "label": self.env._("Fecha de vencimiento"),
                    "risk": "low",
                },
                "date": {"label": self.env._("Fecha contable"), "risk": "low"},
                "ref": {"label": self.env._("Referencia"), "risk": "low"},
                "narration": {"label": self.env._("Nota"), "risk": "low"},
                # used to match bank payments: a card
                "payment_reference": {
                    "label": self.env._("Referencia de pago"),
                    "risk": "money",
                },
                "partner_id": {"risk": "forbidden"},
                "partner_bank_id": {"risk": "forbidden"},
                "invoice_payment_term_id": {"risk": "forbidden"},
                "fiscal_position_id": {"risk": "forbidden"},
                "currency_id": {"risk": "forbidden"},
            },
        }
        specs["account.move.line"] = {
            "label": self.env._("línea de factura o apunte en borrador"),
            "skill": "contabilidad",
            "create": False,
            "update": True,
            "domain": [
                ("move_id.state", "=", "draft"),
                ("move_id.move_type", "in", _MOVE_TYPES),
                ("display_type", "=", "product"),
            ],
            "check": "_xtd_ai_check_account_move_line",
            "fields": {
                "name": {"label": self.env._("Descripción"), "risk": "low"},
                "quantity": {"label": self.env._("Cantidad"), "risk": "low"},
                "date_maturity": {"label": self.env._("Vencimiento"), "risk": "low"},
                "price_unit": {"label": self.env._("Precio unitario"), "risk": "money"},
                "discount": {
                    "label": self.env._("Descuento (%)"),
                    "risk": "low",
                    "money_above": "_xtd_ai_discount_threshold",
                },
                "tax_ids": {
                    "label": self.env._("Impuestos"),
                    "risk": "money",
                    "domain": "_xtd_ai_domain_line_taxes",
                },
                # manual entries only (checked): the account of an invoice line
                # comes from the product
                "account_id": {
                    "label": self.env._("Cuenta"),
                    "risk": "low",
                    "domain": "_xtd_ai_domain_accounts",
                },
                "debit": {"label": self.env._("Debe"), "risk": "money"},
                "credit": {"label": self.env._("Haber"), "risk": "money"},
                "partner_id": {"risk": "forbidden"},
                "product_id": {"risk": "forbidden"},
                "amount_currency": {"risk": "forbidden"},
                "reconciled": {"risk": "forbidden"},
            },
        }
        return specs

    @api.model
    def _xtd_ai_domain_line_taxes(self, model):
        return [
            ("type_tax_use", "in", ("sale", "purchase")),
            ("company_id", "in", self.env.companies.ids),
        ]

    @api.model
    def _xtd_ai_domain_accounts(self, model):
        return [
            ("active", "=", True),
            ("account_type", "!=", "off_balance"),
            ("company_ids", "in", self.env.companies.ids),
        ]

    @api.model
    def _xtd_ai_check_account_move_line(self, line, vals):
        if not line:
            return
        entry_only = {"account_id", "debit", "credit"} & set(vals)
        if entry_only and line.move_id.move_type != "entry":
            raise XtdAiToolError(
                "forbidden",
                self.env._(
                    "En una factura la cuenta y los importes salen del producto y "
                    "de las cantidades: cambia la cantidad o el precio."
                ),
            )
        invoice_only = {"quantity", "price_unit", "discount", "tax_ids"} & set(vals)
        if invoice_only and line.move_id.move_type == "entry":
            raise XtdAiToolError(
                "forbidden",
                self.env._(
                    "En un asiento manual cambia la cuenta, el debe o el haber."
                ),
            )
