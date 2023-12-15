# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from datetime import timedelta

from odoo import _, api, fields, models


class StockProductionLot(models.Model):

    _inherit = "stock.production.lot"

    @api.onchange("life_date")
    def _onchange_life_date(self):
        if self.product_id.alert_time and self.expiration_date:
            self.alert_date = self.expiration_date - timedelta(
                days=self.product_id.alert_time
            )
