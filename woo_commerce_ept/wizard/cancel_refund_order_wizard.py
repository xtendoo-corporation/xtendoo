# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger("WooCommerce")


class WooCancelOrderWizard(models.TransientModel):
    _name = "woo.cancel.order.wizard"
    _description = "WooCommerce Cancel Order"

    message = fields.Char("Reason")
    journal_id = fields.Many2one('account.journal', 'Journal',
                                 help="You can select the journal to use for the credit note that will be created. If "
                                      "it is empty, then it will use the same journal as the current invoice.")
    auto_create_credit_note = fields.Boolean("Create Credit Note In ERP", default=True,
                                             help="It will create a credit not in Odoo")
    refund_date = fields.Date(default=fields.Date.context_today, required=True)

    def cancel_in_woo(self):
        """
        Cancel Order In Woocommerce store.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 23-11-2019.
        Task Id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        sale_order_obj = self.env['sale.order']
        active_id = self._context.get('active_id')
        order = sale_order_obj.browse(active_id)
        instance = order.woo_instance_id

        wcapi = instance.woo_connect()
        info = {'status': 'cancelled', 'id': order.woo_order_id}

        try:
            response = wcapi.post('orders/batch', {'update': [info]})
        except Exception as error:
            raise UserError(_("Something went wrong while Updating Orders.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        _logger.info("Cancel sale order: %s in WooCommere store with Woo commerce order id: %s", order.name,
                     order.woo_order_id)
        if not isinstance(response, requests.models.Response):
            raise UserError(_("Cancel Order \nResponse is not in proper format :: %s", response))

        if response.status_code in [200, 201]:
            order.write({'canceled_in_woo': True, 'woo_status': 'cancelled'})
        else:
            raise UserError(_("Error in Cancel Order %s", response.content))

        if self.auto_create_credit_note:
            self.woo_create_credit_note(order)

        return True

    def woo_create_credit_note(self, order_id):
        """
        It will create a credit note in Odoo.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 23-11-2019.
        Task Id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        moves = order_id.invoice_ids.filtered(lambda invoice:
                                              invoice.move_type == 'out_invoice' and
                                              invoice.payment_state in ['paid', 'in_payment'])
        if not moves:
            order_id._cr.commit()
            warning_message = "Order cancel in WooCommerce But unable to create a credit note in Odoo \n" \
                              "Since order may be uncreated or unpaid invoice"
            raise UserError(warning_message)

        default_values_list = []
        for move in moves:
            date = self.refund_date or move.date
            default_values_list.append({
                'ref': _('Reversal of: %s, %s') % (move.name, self.message) if self.message else _(
                    'Reversal of: %s') % move.name,
                'date': date,
                'invoice_date': move.is_invoice(include_receipts=True) and date or False,
                'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
                'invoice_payment_term_id': None,
                'auto_post': date > fields.Date.context_today(self),
            })
        moves._reverse_moves(default_values_list)

        return True
