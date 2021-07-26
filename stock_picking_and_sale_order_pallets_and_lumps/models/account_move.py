from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    pallets_number = fields.Integer(
        compute='_compute_pallets_number',
        string='Pallets number')

    lumps_number = fields.Integer(
        compute='_compute_lumps_number',
        string='Lumps number')

    has_picking = fields.Boolean(
        compute='_compute_has_picking',
        string='Has Picking')

    def _compute_pallets_number(self):
        pallets_number = 0
        if self.invoice_origin:
            sales_name = self.invoice_origin
            i = 0
            while i < 1:
                position = sales_name.find(',')
                if position is -1:
                    sale_name = sales_name
                    i = 1
                else:
                    sale_name = sales_name[0:position]
                    sales_name = sales_name[position + 2:]
                sale_id = self.env['sale.order'].search([('name', '=', sale_name)])
                pallets_number += sale_id.pallets_number
        self.pallets_number = pallets_number

    def _compute_lumps_number(self):
        lumps_number = 0
        if self.invoice_origin:
            sales_name = self.invoice_origin
            i = 0
            while i < 1:
                position = sales_name.find(',')
                if position is -1:
                    sale_name = sales_name
                    i = 1
                else:
                    sale_name = sales_name[0:position]
                    sales_name = sales_name[position + 2:]
                sale_id = self.env['sale.order'].search([('name', '=', sale_name)])
                lumps_number += sale_id.lumps_number
        self.lumps_number = lumps_number

    def _compute_has_picking(self):
        has_picking = False
        if self.invoice_origin:
            sales_name = self.invoice_origin
            i = 0
            while i < 1:
                position = sales_name.find(',')
                if position is -1:
                    sale_name = sales_name
                    i = 1
                else:
                    sale_name = sales_name[0:position]
                    sales_name = sales_name[position + 2:]
                sale_id = self.env['sale.order'].search([('name', '=', sale_name)])
                if sale_id.has_picking:
                    has_picking = True
        self.has_picking = has_picking
