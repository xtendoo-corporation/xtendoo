# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging


class StockPickingBatch(models.Model):
    _inherit = ['stock.picking']

    def get_invoice_id(self):
      for picking in self:
        if picking.picking_type_id.id == 8:
            if picking.origin != '':
                invoice_id = self.env['account.invoice'].search([('origin', '=', picking.origin)], limit=1)
                picking.invoice_id = invoice_id


    partner_phone = fields.Char('TLF', related='partner_id.phone', readonly=True)

    total_amount = fields.Float(compute='compute_total_amount', string='Importe')

    payment_term = fields.Char(compute='compute_total_amount', string='Forma de pago')

    lumps_number= fields.Integer(string='Nº de bultos', store=True)

    palets_number = fields.Integer(string='Nº de palets', store=True)

    invoice_id=fields.Many2one('account.invoice', compute='get_invoice_id', string='Factura')

    def compute_total_amount(self):
        for line in self:
            if line.sale_id != '':

                logging.info('entra en calculo')
                logging.info(line.sale_id.payment_term_id.name)
                line.total_amount+=line.sale_id.amount_total
                line.payment_term=line.sale_id.payment_term_id.name
