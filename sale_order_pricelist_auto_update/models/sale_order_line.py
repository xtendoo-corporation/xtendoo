# Copyright 2021 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    purchase_price = fields.Float(string='Cost', digits='Product Price', store=True)

    state = fields.Selection(
        related="order_id.state"
    )
    is_pricelist_change = fields.Boolean(
        "The pricelist has changed",
        compute="_compute_is_pricelist_change",
    )

    def _write(self,vals):
        for line in self:
            line._onchange_price_unit()
            print("*"*80)
            print("values",vals)
            print("*" * 80)
        return super(SaleOrderLine, self)._write(vals)


    @api.onchange("price_unit")
    def _onchange_price_unit(self):
            if not self.product_id:
                return
            if self.price_unit == 0.0:
                return
            if self.price_unit < self.product_id.standard_price:
                raise UserError(
                    _("The unit price of %s, can't be lower than cost price %.2f")
                    % (self.product_id.name, self.product_id.standard_price)
                )

    @api.depends("price_unit")
    def _compute_is_pricelist_change(self):
        for line in self:
            if line.product_id:
                try:
                    display_price = line._get_display_price(line.product_id)
                    pricelist_price_unit = self.env[
                        "account.tax"
                    ]._fix_tax_included_price_company(
                        display_price,
                        line.product_id.taxes_id,
                        line.tax_id,
                        line.company_id,
                    )
                    line.is_pricelist_change = (
                        line.price_unit - pricelist_price_unit
                    ) != 0.0
                except:
                    line.is_pricelist_change = False
            else:
                line.is_pricelist_change = False

    def action_update_pricelist(self):
        for line in self:
            items = self.env["product.pricelist.item"].search(
                [
                    ("pricelist_id", "=", line.order_id.pricelist_id.id),
                    ("product_tmpl_id", "=", line.product_id.product_tmpl_id.id),
                    ("applied_on", "=", "1_product"),
                    ("compute_price", "=", "fixed"),
                ]
            )
            if items:
                items.write({"fixed_price": line.price_unit})
            else:
                self.env["product.pricelist.item"].create(
                    [
                        {
                            "pricelist_id": line.order_id.pricelist_id.id,
                            "product_tmpl_id": line.product_id.product_tmpl_id.id,
                            "fixed_price": line.price_unit,
                            "applied_on": "1_product",
                            "base": "list_price",
                            "compute_price": "fixed",
                        }
                    ]
                )
