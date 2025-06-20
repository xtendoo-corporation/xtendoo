from odoo import models, fields, api


class StockNotificationWizard(models.TransientModel):
    _name = 'stock.notification.wizard'
    _description = 'Wizard para productos con stock bajo'

    product_ids = fields.Many2many('product.product', string='Productos con stock bajo')

    def action_view_products(self):
        return {
            'name': 'Productos con stock bajo',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }
