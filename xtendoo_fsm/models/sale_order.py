# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_order_id = fields.Many2one(
        'fsm.order',
        string='Orden de Trabajo FSM',
        help="Orden de trabajo FSM que originó esta orden de venta"
    )
    aseguradora_id = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        help='Aseguradora asociada a la orden de trabajo FSM'
    )
    importe_franquicia = fields.Float(
        string='Importe Franquicia',
        help='Importe de la franquicia de la orden de trabajo FSM'
    )
    insurance_partner_id = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        help='Compañía aseguradora asociada a la orden de venta.'
    )
    franchise_amount = fields.Float(
        string='Importe Franquicia',
        help='Importe de la franquicia asociada a la orden de venta.'
    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        self.ensure_one()
        # Si no hay aseguradora o no tiene franquicia, nos salimos del flujo normal
        if not self.insurance_partner_id or self.franchise_amount == 0:
            # Llamada al super solo con los argumentos que acepta la versión base
            return super()._create_invoices(grouped=grouped, final=final)

        # Factura para la aseguradora
        invoice_vals_aseguradora = self._prepare_invoice()
        invoice_vals_aseguradora['partner_id'] = self.insurance_partner_id.id
        invoice_line_vals = []
        for line in self.order_line:
            invoice_line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
            }))
        invoice_vals_aseguradora['invoice_line_ids'] = invoice_line_vals
        invoice_aseguradora = self.env['account.move'].create(invoice_vals_aseguradora)
        invoice_aseguradora.write({
            'invoice_line_ids': [(0, 0, {
                'name': 'Franquicia',
                'quantity': 1,
                'price_unit': -self.franchise_amount,
                'tax_ids': [(6, 0, self.order_line[0].tax_id.ids)] if self.order_line else [],
            })]
        })
        # Factura para el cliente solo por la franquicia, aplicando IVA
        invoice_vals_cliente = self._prepare_invoice()
        invoice_vals_cliente['partner_id'] = self.partner_id.id
        # Tomar los mismos impuestos que la primera línea de la orden
        tax_ids = [(6, 0, self.order_line[0].tax_id.ids)] if self.order_line else []
        invoice_vals_cliente['invoice_line_ids'] = [(0, 0, {
            'name': 'Franquicia',
            'quantity': 1,
            'price_unit': self.franchise_amount,
            'tax_ids': tax_ids,
        })]
        invoice_cliente = self.env['account.move'].create(invoice_vals_cliente)
        return invoice_aseguradora | invoice_cliente
