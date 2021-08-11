from odoo import api, fields, models

class AccountInvoice(models.Model):
    _inherit = "account.move"

    palets_number = fields.Integer(compute='compute_palets_number', string='Pallets number')

    lumps_number = fields.Integer(compute='compute_lumps_number', string='Lumps number')

    has_picking = fields.Boolean(compute='compute_has_picking', string='Has Picking')

    def compute_palets_number(self):
        palets_number=0
        if self.invoice_origin != False:
            sales_name = self.invoice_origin
            i=0
            while i < 1:
                position=sales_name.find(',')
                if position is -1:
                    sale_name=sales_name
                    i=1
                else:
                    sale_name=sales_name[0:position]
                    sales_name=sales_name[position+2:]
                sale_id=self.env['sale.order'].search([('name', '=', sale_name)])
                palets_number+=sale_id.palets_number
        self.palets_number=palets_number

    def compute_lumps_number(self):
        lumps_number=0
        if self.invoice_origin != False:
            sales_name = self.invoice_origin
            i=0
            while i < 1:
                position=sales_name.find(',')
                if position is -1:
                    sale_name=sales_name
                    i=1
                else:
                    sale_name=sales_name[0:position]
                    sales_name=sales_name[position+2:]
                sale_id=self.env['sale.order'].search([('name', '=', sale_name)])
                lumps_number+=sale_id.lumps_number
        self.lumps_number=lumps_number

    def compute_has_picking(self):
        has_picking=False
        if self.invoice_origin != False:
            sales_name=self.invoice_origin
            i=0
            while i < 1:
                position=sales_name.find(',')
                if position is -1:
                    sale_name=sales_name
                    i=1
                else:
                    sale_name=sales_name[0:position]
                    sales_name=sales_name[position+2:]
                sale_id=self.env['sale.order'].search([('name', '=', sale_name)])
                if sale_id.has_picking == True:
                    has_picking=True
        self.has_picking=has_picking



