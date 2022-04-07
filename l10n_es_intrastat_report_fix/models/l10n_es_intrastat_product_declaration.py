# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class L10nEsIntrastatProductDeclaration(models.Model):
    _inherit = "l10n.es.intrastat.product.declaration"

    def _gather_invoices(self):
        old_lines = super()._gather_invoices()
        lines = []
        product_model = self.env["product.product"]
        for line in old_lines:
            if self.type == "dispatches" and int(self.year) >= 2022:
                if not line["product_origin_country_code"]:
                    product = product_model.browse(line["product_id"])
                    note = (
                        "\n"
                        + _("Missing origin country on product %s.")
                        % product.name_get()[0][1]
                    )
                    self._note += note
                    continue
            lines.append(line)
        return lines
