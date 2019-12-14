# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from datetime import datetime

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    date_next_coming = fields.Datetime(string='Next Coming', help="Date for next coming.",
        compute='_compute_quantities_dict')

    def _compute_quantities(self):
        res = self._compute_quantities_dict()
        
        for template in self:
            template.qty_available = res[template.id]['qty_available']
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.outgoing_qty = res[template.id]['outgoing_qty']
            template.date_next_coming = res[template.id]['date_next_coming']

    def _compute_quantities_dict(self):
        variants_available = self.mapped('product_variant_ids')._product_available()
        prod_available = {}

        for template in self:
            qty_available = 0
            virtual_available = 0
            incoming_qty = 0
            outgoing_qty = 0
            date_next_coming = None

            for p in template.product_variant_ids:
                qty_available += variants_available[p.id]["qty_available"]
                virtual_available += variants_available[p.id]["virtual_available"]
                incoming_qty += variants_available[p.id]["incoming_qty"]
                outgoing_qty += variants_available[p.id]["outgoing_qty"]

                if date_next_coming == None and incoming_qty > 0:
                    date_next_coming = self._get_date_next_coming(p)

            prod_available[template.id] = {
                "qty_available": qty_available,
                "virtual_available": virtual_available,
                "incoming_qty": incoming_qty,
                "outgoing_qty": outgoing_qty,
                "date_next_coming": date_next_coming,
            }

        return prod_available

    def _get_date_next_coming(self, product):
        line = product.env['purchase.order.line'].search(
            [('order_id.state', '=', 'purchase'),
            ('product_id', '=', product.id)],
            order='date_planned asc', limit=1)    

        return line.date_planned
