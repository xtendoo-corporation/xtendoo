# Copyright 2020 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    margin_percent = fields.Float(
        string='Margin Percent',
        readonly=True,
        digits=(16, 2),
        )

    def _query(self, with_clause="", fields=None, groupby="", from_clause=""):
        if fields is None:
            fields = {}
        fields.update(
            {
                "margin_percent":
                " , CASE"
                "       WHEN"
                "           l.untaxed_amount_to_invoice = 0"
                "       THEN"
                "            0"
                "       ELSE"
                "            SUM((l.margin / l.untaxed_amount_to_invoice) / COALESCE(s.currency_rate, 1.0)) * 100"
                "       END"
                "       AS"
                "            margin_percent"
            }
        )
        groupby += ', l.untaxed_amount_to_invoice'

        return super()._query(
            with_clause=with_clause,
            fields=fields,
            groupby=groupby,
            from_clause=from_clause,
        )

# "margin_percent": " ,SUM("
# "((l.margin / l.untaxed_amount_to_invoice)"
# " / COALESCE(s.currency_rate, 1.0)) * 100)"
# "AS margin_percent"
# "margin_percent":
#     " ,SUM("
#                 "(l.untaxed_amount_to_invoice)"
#                 " / (1.0)) * 100)"
#                 "AS margin_percent"
