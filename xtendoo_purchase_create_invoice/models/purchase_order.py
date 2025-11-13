# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_create_invoice_direct(self):
        """
        Crea directamente la factura sin pasar por wizards ni intervención del usuario.
        Factura todas las líneas pendientes del pedido (cantidades recibidas).
        Este es el comportamiento más común y eficiente.
        """
        self.ensure_one()

        if self.state not in ['purchase', 'done']:
            raise UserError(_('No puede crear una factura para un pedido de compra que no está confirmado.'))

        if self.invoice_status != 'to invoice':
            raise UserError(_('No hay nada que facturar en este pedido.'))

        # Crear la factura
        invoice_vals = self._prepare_invoice()

        # Añadir las líneas de factura (solo cantidades pendientes de facturar)
        invoice_line_vals = []
        for line in self.order_line.filtered(lambda l: not l.display_type and l.qty_to_invoice > 0):
            invoice_line_vals.append((0, 0, line._prepare_account_move_line()))

        if not invoice_line_vals:
            raise UserError(_('No hay líneas pendientes de facturar.'))

        invoice_vals['invoice_line_ids'] = invoice_line_vals

        # Crear la factura
        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Mensaje de éxito
        self.message_post(
            body=_('Factura %s creada automáticamente desde el pedido de compra.') % invoice.name,
            message_type='notification',
        )

        # Mostrar la factura creada
        return self.action_view_invoice(invoice)

