# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging


class StockPickingBatch(models.Model):
    _inherit = ["stock.picking"]

    def get_invoice_id(self):
        for picking in self:
            if picking.picking_type_id.id == 8:
                if picking.origin != "":
                    invoice_id = self.env["account.invoice"].search(
                        [("origin", "=", picking.origin)], limit=1
                    )
                    picking.invoice_id = invoice_id

    def set_is_back_order(self):
        for picking in self:
            if picking.origin is not False:
                is_back_order = picking.origin.startswith("Retorno")
                if is_back_order is True:
                    picking.is_backorder = True
                else:
                    picking.is_backorder = False
            else:
                picking.is_backorder = False

    def _get_default_is_backorder(self):
        if self.origin is not False:
            is_back_order = self.origin.startswith("Retorno")
            if is_back_order is True:
                return True
            else:
                return False
        else:
            return False

    partner_phone = fields.Char("TLF", related="partner_id.phone", readonly=True)

    total_amount = fields.Float(compute="compute_total_amount", string="Amount")

    payment_term = fields.Char(compute="compute_total_amount", string="Payment Term")

    invoice_id = fields.Many2one(
        "account.invoice", compute="get_invoice_id", string="Invoice"
    )

    is_backorder = fields.Boolean(
        compute="set_is_back_order",
        string="is BackOrder",
        default=lambda self: self._get_default_is_backorder(),
        store=True,
    )

    def compute_total_amount(self):
        for line in self:
            if line.sale_id != "":
                line.total_amount += line.sale_id.amount_total
                line.payment_term = line.sale_id.payment_term_id.name
