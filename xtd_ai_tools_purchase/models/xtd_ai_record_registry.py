from odoo import api, models

_DRAFT = [("state", "=", "draft")]


class XtdAiRecordRegistry(models.AbstractModel):
    _inherit = "xtd.ai.record.registry"

    @api.model
    def _xtd_ai_record_specs(self):
        specs = super()._xtd_ai_record_specs()
        specs["purchase.order"] = {
            "label": self.env._("petición de presupuesto"),
            "skill": "compras",
            "create": False,
            "update": True,
            "domain": _DRAFT,
            "fields": {
                "partner_ref": {
                    "label": self.env._("Referencia del proveedor"),
                    "risk": "low",
                },
                "date_planned": {"label": self.env._("Fecha prevista"), "risk": "low"},
                "note": {"label": self.env._("Nota"), "risk": "low"},
                "partner_id": {"risk": "forbidden"},
                "payment_term_id": {"risk": "forbidden"},
                "fiscal_position_id": {"risk": "forbidden"},
            },
        }
        specs["purchase.order.line"] = {
            "label": self.env._("línea de compra"),
            "skill": "compras",
            "create": False,
            "update": True,
            "domain": [("order_id.state", "=", "draft")],
            "fields": {
                "product_qty": {"label": self.env._("Cantidad"), "risk": "low"},
                "name": {"label": self.env._("Descripción"), "risk": "low"},
                "date_planned": {"label": self.env._("Fecha prevista"), "risk": "low"},
                "price_unit": {"label": self.env._("Precio unitario"), "risk": "money"},
                "discount": {
                    "label": self.env._("Descuento (%)"),
                    "risk": "low",
                    "money_above": "_xtd_ai_discount_threshold",
                },
                "tax_ids": {
                    "label": self.env._("Impuestos"),
                    "risk": "money",
                    "domain": "_xtd_ai_domain_purchase_taxes",
                },
                "product_id": {"risk": "forbidden"},
            },
        }
        return specs
