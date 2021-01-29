# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    margin_percent = fields.Float(string="Margin Percent", digits=(16, 2),)

    def _query(self, with_clause="", fields={}, groupby="", from_clause=""):
        fields["margin_percent"] = ", SUM(l.margin_percent) AS margin_percent"
        return super()._query(with_clause, fields, groupby, from_clause)
