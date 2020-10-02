# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("partner_id")
    def _get_domain(self):
        show_all_clients = True
        if (
            self.env["res.users"].has_group(
                "sale_order_only_comercial_clients.comercial_group"
            )
            == True
        ):
            show_all_clients = False
        # self.env.user.create_direct_invoice
        if show_all_clients == True:
            domain = {"partner_id": [("customer", "=", True)]}
        else:
            domain = {"partner_id": [("user_id", "=", self.env.user.id)]}

        return {"domain": domain}

