from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_print_labels(self):
        self.ensure_one()
        product_ids = self.move_line_ids.mapped('product_id')
        action = self.env.ref('xtendoo_product_label.action_print_label_from_product').read()[0]
        action['context'] = {
            'default_product_product_ids': product_ids,
            'active_model': 'stock.picking',
            'active_id': self.id,
            'active_ids': [self.id],
        }
        return action
