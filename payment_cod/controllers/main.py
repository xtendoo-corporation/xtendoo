# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint
import logging

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class CustomController(Controller):
    _process_url = '/payment/custom/process'

    @route(_process_url, type='http', auth='public', methods=['POST'], csrf=False)
    def custom_process_transaction(self, **post):
        _logger.info("Handling custom processing with data:\n%s", pprint.pformat(post))

        # Obtener la transacción desde los datos de notificación
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'custom', post
        )

        if tx_sudo:
            # Procesar la notificación
            tx_sudo._handle_notification_data('custom', post)
        else:
            _logger.warning("No transaction found for custom payment with data: %s", post)

        return request.redirect('/payment/status')
