# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        # Acumulamos todas las facturas que cumplen con la condición
        active_ids = []

        for record in self:
            # Buscar la orden de venta correspondiente al registro actual (factura)
            order = self.env['sale.order'].sudo().search([('invoice_ids.id', '=', record.id)], limit=1)

            # Verificar si se encontró una orden de venta
            if order:
                cod_collection = self.env['cod.payment.collection'].sudo().search([('sale_order_id.id', '=', order.id)])

                # Verificar si el COD está disponible
                if order.order_cod_available == True:
                    if cod_collection.ids:
                        for record_cod in cod_collection:
                            if not record_cod.state == 'done':
                                raise ValidationError(
                                    _('You can not register payment because COD payment are still pending.'))
                        # Si la colección COD está lista, agregamos la factura al listado de facturas activas
                        active_ids.append(record.id)
                    else:
                        raise ValidationError(_('You can not register payment because COD payment are still pending.'))
                else:
                    # Si no es COD, agregar la factura al listado de facturas activas
                    active_ids.append(record.id)

        # Si hay facturas activas, abrir el wizard de pago
        if active_ids:
            return {
                'name': _('Register Payment'),
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': active_ids,  # Pasamos todos los ids de las facturas seleccionadas
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }
        else:
            # Si no hay facturas para registrar el pago, mostrar un error
            raise ValidationError(_('No valid invoices found for payment registration.'))


