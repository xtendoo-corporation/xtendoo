from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    pallets_number = fields.Integer(
        compute='compute_has_picking',
        string='Pallets number'
    )
    lumps_number = fields.Integer(
        compute='compute_has_picking',
        string='Lumps number'
    )
    has_picking = fields.Boolean(
        compute='compute_has_picking',
        string='Has Picking'
    )

    def compute_has_picking(self):
        self.lumps_number = 0
        self.pallets_number = 0
        self.has_picking = False
        for invoice in self.filtered(lambda x: x.invoice_origin):
            lumps_number = 0
            pallets_number = 0
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
                if sale_id:
                    lumps_number += sale_id.lumps_number
                    pallets_number += sale_id.pallets_number

            invoice.lumps_number = lumps_number
            invoice.pallets_number = pallets_number
            invoice.has_picking = sale_id.has_picking
