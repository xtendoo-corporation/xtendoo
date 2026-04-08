from odoo import models, fields, api
from odoo.tools import SQL  # Odoo 18: _select() devuelve SQL(), no str


class AccountInvoiceReportExtended(models.Model):
    _inherit = "account.invoice.report"

    price_unit = fields.Float(string='Precio unitario', readonly=True)
    discount = fields.Float(string='Descuento (%)', readonly=True)

    # Odoo 18: indica los campos adicionales de los que depende esta vista SQL
    _depends = {
        'account.move.line': ['price_unit', 'discount'],
    }

    @api.model
    def _select(self) -> SQL:
        # Odoo 18: super()._select() devuelve SQL(), no str; la concatenación con str lanza TypeError.
        # Se usa SQL('%s , extra', parent_sql) para extender de forma segura.
        return SQL(
            '%s , line.price_unit AS price_unit, line.discount AS discount',
            super()._select(),
        )
