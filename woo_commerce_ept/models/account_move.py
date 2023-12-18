# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger("WooCommerce")


class AccountMove(models.Model):
    _inherit = "account.move"

    woo_instance_id = fields.Many2one("woo.instance.ept", "Woo Instance")
    is_refund_in_woo = fields.Boolean("Refund In Woo Commerce", default=False)

    def refund_in_woo(self):
        """
        This method is used for refund process. It'll call order refund api for that process
        Note: - It's only generate refund it'll not make any auto transaction according to woo payment method.
              - @param:api_refund: responsible for auto transaction as per woo payment method.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 23-11-2019.
        Migrated Maulik Barad on Date 07-Oct-2021.
        """
        for refund in self:
            if not refund.woo_instance_id:
                continue
            wc_api = refund.woo_instance_id.woo_connect()
            orders = refund.invoice_line_ids.sale_line_ids.order_id

            for order in orders:
                data = {"amount": str(refund.amount_total), 'reason': str(refund.name or ''), 'api_refund': False}

                try:
                    response = wc_api.post('orders/%s/refunds' % order.woo_order_id, data)
                except Exception as error:
                    raise UserError(_("Something went wrong while refunding Order.\n\nPlease Check your Connection and "
                                      "Instance Configuration.\n\n" + str(error)))

                _logger.info("Refund created in Woocommerce store for woo order id: %s and refund amount is : %s",
                             order.woo_order_id, str(refund.amount_total))
                if not isinstance(response, requests.models.Response):
                    raise UserError(_("Refund \n Response is not in proper format :: %s") % response)

                if response.status_code not in [200, 201]:
                    raise UserError(_("Refund \n%s") % response.content)
                refund.write({'is_refund_in_woo': True})
        return True
