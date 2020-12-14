# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from datetime import date, timedelta


class StockProductionLot(models.Model):

    _inherit = "stock.production.lot"

    @api.onchange('life_date')
    def _onchange_life_date(self):
        alert_time = self.product_id.alert_time
        if alert_time:
            self.alert_date = self.life_date - timedelta(days=alert_time)

