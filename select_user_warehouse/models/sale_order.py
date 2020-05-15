# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.model
    def default_get(self, default_fields):
        fields = super(SaleOrder, self).default_get(default_fields)

        if self.env.user.warehouse_id:
            fields['warehouse_id'] = self.env.user.warehouse_id.id

        return fields
