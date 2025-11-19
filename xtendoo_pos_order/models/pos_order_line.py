# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.depends("qty", "price_unit", "discount", "tax_ids", "price_subtotal")
    def _compute_amount_line_all(self):
        """
        Asegura que los cálculos de línea funcionen correctamente desde backend.
        Reutiliza la lógica estándar del POS.
        """
        return super()._compute_amount_line_all()

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """
        Auto-completa información del producto al seleccionarlo.
        Útil para la interfaz de backend.
        """
        if self.product_id:
            # Obtener precio desde la lista de precios del POS
            pricelist = False
            if self.order_id and self.order_id.pricelist_id:
                pricelist = self.order_id.pricelist_id
            elif self.order_id and self.order_id.config_id:
                pricelist = self.order_id.config_id.pricelist_id

            if pricelist:
                self.price_unit = pricelist.get_product_price(
                    self.product_id,
                    self.qty or 1.0,
                    self.order_id.partner_id if self.order_id else False
                )
            else:
                self.price_unit = self.product_id.lst_price

            # Asignar impuestos del producto
            if self.order_id and self.order_id.fiscal_position_id:
                taxes = self.order_id.fiscal_position_id.map_tax(
                    self.product_id.taxes_id.filtered(
                        lambda t: t.company_id == self.order_id.company_id
                    )
                )
                self.tax_ids = taxes
            else:
                self.tax_ids = self.product_id.taxes_id.filtered(
                    lambda t: t.company_id == self.env.company
                )

    @api.onchange("qty", "price_unit", "discount")
    def _onchange_qty_price_discount(self):
        """
        Recalcula subtotales cuando cambian cantidad, precio o descuento.
        """
        # Los campos calculados se actualizarán automáticamente
        # gracias a los @api.depends del modelo base
        pass

