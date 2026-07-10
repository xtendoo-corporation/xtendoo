# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class GeminiFeedback(models.Model):
    _inherit = "gemini.feedback"

    source_model = fields.Selection(
        selection_add=[("purchase.order", "Pedido de compra")],
        ondelete={"purchase.order": "cascade"},
    )
    purchase_order_id = fields.Many2one(
        "purchase.order", string="Pedido de compra", ondelete="set null"
    )

