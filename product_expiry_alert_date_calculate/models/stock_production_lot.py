# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, _
from datetime import timedelta


class StockProductionLot(models.Model):

    _inherit = "stock.production.lot"

    @api.onchange('life_date')
    def _onchange_life_date(self):
        if self.product_id.alert_time and self.life_date:
            self.alert_date = self.life_date - timedelta(days=self.product_id.alert_time)

