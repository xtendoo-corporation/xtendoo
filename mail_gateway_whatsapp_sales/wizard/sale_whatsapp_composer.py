# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

class SaleWhatsappComposer(models.TransientModel):
    _name = 'sale.whatsapp.composer'
    _description = 'Enviar WhatsApp desde pedido de venta'

    sale_order_id = fields.Many2one('sale.order', string='Pedido de venta', required=True)
    gateway_id = fields.Many2one('mail.gateway', string='Gateway', required=True, domain="[('gateway_type', '=', 'whatsapp')]")
    template_id = fields.Many2one(
        'mail.whatsapp.template',
        string='Plantilla',
        domain="[('model_id.model', '=', 'sale.order'), ('state', '=', 'approved'), ('is_supported', '=', True)]",
        required=True
    )
    body = fields.Text('Mensaje')

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.body = self.template_id.body

    def action_send_whatsapp(self):
        self.ensure_one()
        # Registrar el mensaje en el chatter del pedido
        self.sale_order_id.message_post(
            body=self.body,
            author_id=self.env.user.partner_id.id,
            gateway_type='whatsapp',
            subtype_xmlid='mail.mt_comment',
            message_type='comment',
        )
        # Aquí puedes añadir la lógica para enviar el mensaje real por WhatsApp usando el gateway
        # ...
        return {'type': 'ir.actions.act_window_close'}

