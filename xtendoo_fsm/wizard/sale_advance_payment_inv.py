from odoo import models, api

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def create_invoices(self):
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        for wizard in self:
            for order in wizard.sale_order_ids:
                if order.insurance_partner_id and order.franchise_amount > 0:
                    # Factura para la aseguradora
                    invoice_vals_aseguradora = order._prepare_invoice()
                    invoice_vals_aseguradora['partner_id'] = order.insurance_partner_id.id
                    invoice_line_vals = []
                    for line in order.order_line:
                        invoice_line_vals.append((0, 0, {
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'quantity': line.product_uom_qty,
                            'price_unit': line.price_unit,
                            'tax_ids': [(6, 0, line.tax_id.ids)],
                        }))
                    invoice_vals_aseguradora['invoice_line_ids'] = invoice_line_vals
                    invoice_aseguradora = order.env['account.move'].create(invoice_vals_aseguradora)
                    # Añadir descuento de franquicia como línea negativa
                    invoice_aseguradora.write({
                        'invoice_line_ids': [(0, 0, {
                            'name': 'Franquicia',
                            'quantity': 1,
                            'price_unit': -order.franchise_amount,
                        })]
                    })
                    # Factura para el cliente solo por la franquicia
                    invoice_vals_cliente = order._prepare_invoice()
                    invoice_vals_cliente['partner_id'] = order.partner_id.id
                    invoice_vals_cliente['invoice_line_ids'] = [(0, 0, {
                        'name': 'Franquicia',
                        'quantity': 1,
                        'price_unit': order.franchise_amount,
                    })]
                    invoice_cliente = order.env['account.move'].create(invoice_vals_cliente)
        return res

