# -*- coding: utf-8 -*-
from odoo import models, api

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def action_pay_order_from_kanban(self):
        """
        Método puente para llamar a la acción de pago desde el kanban de métodos de pago
        dentro del formulario del pedido POS.
        """
        self.ensure_one()
        # El active_id en el contexto será el ID del pos.order (el padre del kanban)
        order_id = self.env.context.get('active_id')
        if not order_id:
            return False
            
        order = self.env['pos.order'].browse(order_id)
        if order.exists():
            return order.action_pay_with_method(self)
        return False
