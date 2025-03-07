from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"


    def action_validate_picking_and_invoice(self):
        for order in self:
            if order.state == 'draft':
                order.action_confirm()
            order.picking_ids.action_assign()
            order.picking_ids.button_validate()

            invoice = order._create_invoices()
            if not invoice:
                continue

            invoice.action_post()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Customer Invoice',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
                'target': 'current',
            }
