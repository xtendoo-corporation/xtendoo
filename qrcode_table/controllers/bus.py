# -*- coding: utf-8 -*
from odoo.addons.bus.controllers.main import BusController
from odoo.http import request

class BusController(BusController):

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        channels = list(channels)
        if options.get('table.order'):
            qrcode_order_channel = (
                request.db,
                'table.order',
                options.get('table.order')
            )
            channels.append(qrcode_order_channel)
        print('OOOOOOOOOOOOO', options)
        return super(BusController, self)._poll(dbname, channels, last, options)