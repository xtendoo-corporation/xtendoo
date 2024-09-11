from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create_picking_from_pos(self, order_name, vals):
        pos_order = self.env['pos.order'].search([('name', '=', order_name)], limit=1)
        if pos_order:
            picking_vals = {
                'picking_type_id': self.env.ref('stock.picking_type_out').id,
                'partner_id': pos_order.partner_id.id,
                'origin': pos_order.name,
            }
            picking = self.env['stock.picking'].create(picking_vals)
            return picking.id
        return False
