from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def product_price_update_before_done(self, forced_qty=None):
        """Override para el método de coste 'Last Purchase Price'.

        Odoo 18: _get_price_unit() devuelve un dict {lot_record: float}
        en lugar de un float. Se usa next(iter(...)) para extraer el precio.

        El super() ejecuta la lógica AVCO/FIFO estándar y luego sobreescribimos
        el standard_price con el precio real de la última compra.
        """
        super().product_price_update_before_done(forced_qty=forced_qty)
        for move in self.filtered(
            lambda m: m.with_company(m.company_id).product_id.cost_method == 'last'
            and m.product_id.valuation in ['real_time', 'manual_periodic']
        ):
            # Odoo 18: _get_price_unit() retorna {lot_record: float}
            price_unit = next(iter(move._get_price_unit().values()))
            move.product_id.with_company(move.company_id.id).with_context(
                disable_auto_svl=True
            ).sudo().write({'standard_price': price_unit})
