from odoo import models, fields, api
from odoo.tools.float_utils import float_compare


class StockMinimumNotification(models.Model):
    _name = 'stock.minimum.notification'
    _description = 'Notificaciones de stock mínimo'
    _inherit = ['mail.thread']

    name = fields.Char('Nombre', required=True)
    active = fields.Boolean('Activo', default=True)
    min_quantity = fields.Float(string='Cantidad mínima', required=True)
    location_id = fields.Many2one('stock.location', string='Ubicación', required=True)
    notify_user_ids = fields.Many2many('res.users', string='Usuarios a notificar')
    last_notification = fields.Datetime('Última notificación')

    def _cron_check_stock_levels(self):
        rules = self.search([('active', '=', True)])
        for rule in rules:
            self._check_location_stock(rule)

    def _check_location_stock(self, rule):
        domain = [('location_id', '=', rule.location_id.id)]
        quants = self.env['stock.quant'].search(domain)

        product_quantities = {}
        low_stock_products = []

        for quant in quants:
            product_id = quant.product_id.id
            if product_id not in product_quantities:
                product_quantities[product_id] = 0
            product_quantities[product_id] += quant.quantity - quant.reserved_quantity

        for product_id, available_qty in product_quantities.items():
            if float_compare(available_qty, rule.min_quantity, precision_digits=2) < 0:
                product = self.env['product.product'].browse(product_id)
                low_stock_products.append({
                    'id': product_id,
                    'name': product.name,
                    'qty': available_qty
                })
        if low_stock_products:
            self._notify_low_stock_summary(rule, low_stock_products)

    def _notify_low_stock_summary(self, rule, low_stock_products):
        #Envíamos notificación por chat usando OdooBot
        rule.last_notification = fields.Datetime.now()
        odoobot = self.env.ref('base.partner_root')

        product_count = len(low_stock_products)
        message = "⚠️ ALERTA: Se han detectado {} productos con stock por debajo del mínimo ".format(product_count)
        message += "configurado ({}) en {}.\n\n".format(rule.min_quantity, rule.location_id.display_name)

        # Lista de los primeros 5 productos (para no saturar el mensaje)
        for i, product in enumerate(low_stock_products[:5]):
            message += "• {} (cantidad: {})\n".format(product['name'], product['qty'])

        if product_count > 5:
            message += "• ... y {} productos más\n\n".format(product_count - 5)

        product_ids = [p['id'] for p in low_stock_products]

        action = self.env['ir.actions.act_window'].create({
            'name': 'Productos con Stock Bajo',
            'res_model': 'product.product',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', product_ids)],
            'context': {'create': False},
            'target': 'current',
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env.ref('stock.menu_stock_root').id
        action_id = action.id

        action_url = "{}/web#id={}&view_type=list&model=product.product&action={}&menu_id={}".format(
            base_url, product_ids[0], action_id, menu_id)

        message += "\n<a href='{}'>Ver todos los productos con stock bajo</a>".format(action_url)

        subtype_id = self.env.ref('mail.mt_comment').id

        for user in rule.notify_user_ids:
            channel = self.env['mail.channel'].channel_get([user.partner_id.id, odoobot.id])
            self.env['mail.channel'].browse(channel["id"]).message_post(
                body=message,
                author_id=odoobot.id,
                message_type='comment',
                subtype_id=subtype_id,
            )

    def action_check_stock_now(self):
        """Verifica niveles de stock manualmente"""
        self._check_location_stock(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Verificación completada',
                'message': 'Se ha verificado el stock y enviado notificaciones si corresponde',
                'type': 'success',
            }
        }
