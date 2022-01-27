from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    palets_number = fields.Integer(
        compute='compute_palets_number',
        string='Pallets number'
    )
    lumps_number = fields.Integer(
        compute='compute_lumps_number',
        string='Lumps number'
    )
    has_picking = fields.Boolean(
        compute='compute_has_picking',
        string='Has Picking'
    )

    def compute_palets_number(self):
        for invoice in self.filtered(lambda x: x.invoice_origin):
            palets_number = 0
            sales_name = invoice.invoice_origin
            i = 0
            while i < 1:
                position = sales_name.find(',')
                if position is -1:
                    sale_name = sales_name
                    i = 1
                else:
                    sale_name = sales_name[0:position]
                    sales_name = sales_name[position+2:]
                sale_id = self.env['sale.order'].search([('name', '=', sale_name)])
                palets_number += sale_id.palets_number
            invoice.palets_number = palets_number

    def compute_lumps_number(self):
        for invoice in self.filtered(lambda x: x.invoice_origin):
            lumps_number = 0
            sales_name = invoice.invoice_origin
            i = 0
            while i < 1:
                position=sales_name.find(',')
                if position is -1:
                    sale_name = sales_name
                    i = 1
                else:
                    sale_name = sales_name[0:position]
                    sales_name = sales_name[position+2:]
                sale_id = self.env['sale.order'].search([('name', '=', sale_name)])
                lumps_number += sale_id.lumps_number
            invoice.lumps_number = lumps_number

    def compute_has_picking(self):
        self.has_picking = False
        for invoice in self.filtered(lambda x: x.invoice_origin):
            sales_name = self.invoice_origin
            i = 0
            while i < 1:
                position = sales_name.find(',')
                if position is -1:
                    sale_name = sales_name
                    i = 1
                else:
                    sale_name = sales_name[0:position]
                    sales_name = sales_name[position+2:]
                sale_id = self.env['sale.order'].search([('name', '=', sale_name)])
            invoice.has_picking = sale_id.has_picking
