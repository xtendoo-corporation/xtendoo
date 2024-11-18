# Copyright © 2018 Garazd Creation (<https://garazd.biz>)
# @author: Yurii Razumovskyi (<support@garazd.biz>)
# @author: Iryna Razumovska (<support@garazd.biz>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from odoo import api, fields, models


class PrintProductLabelLine(models.TransientModel):
    _name = "print.product.label.line"
    _description = 'Line with a Product Label Data'
    _order = 'sequence'

    sequence = fields.Integer(default=900)
    selected = fields.Boolean(string='Print', default=True)
    wizard_id = fields.Many2one(comodel_name='print.product.label')  # Do not make required
    product_id = fields.Many2one(comodel_name='product.product', required=True)
    barcode = fields.Char(compute='_compute_barcode')
    qty_initial = fields.Integer(string='Initial Qty', default=1)
    qty = fields.Integer(string='Label Qty', default=1)
    custom_value = fields.Char(help="This field can be filled manually to use in label templates.")
    company_id = fields.Many2one(comodel_name='res.company', compute='_compute_company_id')
    # Allow users to specify a partner to use it on label templates
    partner_id = fields.Many2one(comodel_name='res.partner', readonly=False)

    @api.depends('wizard_id.company_id')
    def _compute_company_id(self):
        for label in self:
            label.company_id = label.wizard_id.company_id.id \
                if label.wizard_id.company_id else self.env.user.company_id.id

    @api.depends('product_id')
    def _compute_barcode(self):
        for label in self:
            label.barcode = label.product_id.barcode

    def action_plus_qty(self):
        self.ensure_one()
        if not self.qty:
            self.update({'selected': True})
        self.update({'qty': self.qty + 1})

    def action_minus_qty(self):
        self.ensure_one()
        if self.qty > 0:
            self.update({'qty': self.qty - 1})
            if not self.qty:
                self.update({'selected': False})
