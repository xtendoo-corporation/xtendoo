# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_sale_order_confirm_and_delivery(self):
        self.action_confirm()
        for picking in self.picking_ids:
            for line in picking.move_lines.filtered(
                lambda m: m.state not in ["done", "cancel"]
            ):
                line.quantity_done = line.product_uom_qty
            picking.with_context(skip_overprocessed_check=True).button_validate()

    def action_sale_order_confirm_and_invoice(self):
        self.action_sale_order_confirm_and_delivery()
        payment = self.env["sale.advance.payment.inv"].create({})
        payment.with_context(active_ids=self.ids).create_invoices()

        # self.action_invoice_create()
        # for invoice in self.invoice_ids:
        #     invoice.action_invoice_open()

    # Pedido confirmado( ya es un pedido de ventas)

    def action_sale_order_delivery(self):
        for picking in self.picking_ids:
            if picking.state != "done":
                for line in picking.move_lines:
                    line.quantity_done = line.product_uom_qty
                picking.button_validate()

    def action_sale_order_delivery_and_invoiced(self):
        # logging.info('Cambiamos el env')
        self = self.with_context({"is_sale": True,})
        self.action_sale_order_delivery()
        self.action_invoice_create()
        for invoice in self.invoice_ids:
            invoice.action_invoice_open()
