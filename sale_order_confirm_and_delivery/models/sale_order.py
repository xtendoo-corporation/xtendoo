from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Estos dos métodos se han añadido para poder confirmar y entregar un pedido en un solo clic
    # y para confirmar y facturar un pedido en un solo clic.
    # Pero la entrega y la factura hay que confirmarlas manualmente.
    def action_confirm_and_deliver(self):
        self.action_confirm()
        for order in self.filtered(lambda o: o.state == 'sale'):
            for picking in order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel']):
                picking.action_assign()
                for move in picking.move_ids_without_package:
                    move._action_assign()
                    move._set_quantity_done(move.product_uom_qty)
                picking.with_context(skip_immediate=True, skip_sms=True).button_validate()

    def action_confirm_and_invoice(self):
        self.action_confirm_and_deliver()
        for order in self:
            order._create_invoices()
            for invoice in order.invoice_ids:
                invoice.action_post()
