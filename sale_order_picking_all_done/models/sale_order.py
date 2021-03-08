# Part of Odoo. See LICENSE file for full copyright and licensing details.

<<<<<<< HEAD
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)
=======
from odoo import _, api, fields, models
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708


class SaleOrder(models.Model):
    _inherit = "sale.order"

<<<<<<< HEAD
    # Pedido no confirmado(Es aun presupuesto)

    @api.multi
=======
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
    def action_sale_order_confirm_and_delivery(self):

        self.action_confirm()
        for picking in self.picking_ids:
            for line in picking.move_lines:
                line.quantity_done = line.product_uom_qty
            picking.button_validate()

    @api.multi
    def action_sale_order_confirm_and_invoiced(self):
        # logging.info('Cambiamos el env')
        self = self.with_context({"is_sale": True,})
        self.action_sale_order_confirm_and_delivery()
        self.action_invoice_create()
        for invoice in self.invoice_ids:
            invoice.action_invoice_open()

    # Pedido confirmado( ya es un pedido de ventas)

    @api.multi
    def action_sale_order_delivery(self):

        for picking in self.picking_ids:
            if picking.state != "done":
                for line in picking.move_lines:
                    line.quantity_done = line.product_uom_qty
                picking.button_validate()

    @api.multi
    def action_sale_order_delivery_and_invoiced(self):
        # logging.info('Cambiamos el env')
        self = self.with_context({"is_sale": True,})
        self.action_sale_order_delivery()
        self.action_invoice_create()
        for invoice in self.invoice_ids:
            invoice.action_invoice_open()
