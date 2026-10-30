from odoo import api, models

_DRAFT = [("state", "=", "draft")]


class XtdAiRecordRegistry(models.AbstractModel):
    _inherit = "xtd.ai.record.registry"

    @api.model
    def _xtd_ai_record_specs(self):
        specs = super()._xtd_ai_record_specs()
        specs["sale.order"] = {
            "label": self.env._("presupuesto"),
            "skill": "ventas",
            "create": False,
            "update": True,
            "domain": _DRAFT,
            "fields": {
                "client_order_ref": {
                    "label": self.env._("Referencia del cliente"),
                    "risk": "low",
                },
                "validity_date": {"label": self.env._("Válido hasta"), "risk": "low"},
                "commitment_date": {
                    "label": self.env._("Fecha de entrega"),
                    "risk": "low",
                },
                "note": {"label": self.env._("Condiciones / nota"), "risk": "low"},
                "partner_id": {"risk": "forbidden"},
                "pricelist_id": {"risk": "forbidden"},
                "payment_term_id": {"risk": "forbidden"},
                "fiscal_position_id": {"risk": "forbidden"},
            },
        }
        specs["sale.order.line"] = {
            "label": self.env._("línea de presupuesto"),
            "skill": "ventas",
            "create": False,
            "update": True,
            "domain": [("order_id.state", "=", "draft")],
            "fields": {
                "product_uom_qty": {"label": self.env._("Cantidad"), "risk": "low"},
                "name": {"label": self.env._("Descripción"), "risk": "low"},
                "price_unit": {"label": self.env._("Precio unitario"), "risk": "money"},
                "discount": {
                    "label": self.env._("Descuento (%)"),
                    "risk": "low",
                    "money_above": "_xtd_ai_discount_threshold",
                },
                "tax_ids": {
                    "label": self.env._("Impuestos"),
                    "risk": "money",
                    "domain": "_xtd_ai_domain_sale_taxes",
                },
                "product_id": {"risk": "forbidden"},
            },
        }
        return specs
