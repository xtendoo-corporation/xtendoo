# Copyright 2020 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    qty_pending = fields.Float(
        string="Pending quantity",
        readonly=True,
    )

    def _query(self, with_clause="", fields=None, groupby="", from_clause=""):
        fields = fields or {}
        fields["qty_pending"] = ", l.qty_pending AS" " qty_pending"
        groupby += ", l.qty_pending"
        return super()._query(with_clause, fields, groupby, from_clause)

