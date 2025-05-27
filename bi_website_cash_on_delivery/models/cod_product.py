# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID


class ProductCODFees(models.Model):
	_inherit = 'product.template'

	cod_available = fields.Boolean('Allow Cash on Delivery', default=True)
	delivery_fees = fields.Float('Delivery Fees', compute='update_fees')
	
	@api.onchange('list_price')
	def min_max_calculation_product(self):
		cod_acq = self.env['ir.model.data']._xmlid_lookup('bi_website_cash_on_delivery.payment_provider_cod')[2]
		cod_obj = self.env['payment.provider'].sudo().browse(cod_acq)
		for p in self:
			if p.list_price < cod_obj.cod_config.min_amt or p.list_price > cod_obj.cod_config.max_amt:
				p.update({'cod_available': False}) 
			elif p.list_price > cod_obj.cod_config.min_amt or p.list_price < cod_obj.cod_config.max_amt:
				p.update({'cod_available': True})
	
	def update_fees(self):
		cod_obj = self.env['ir.model.data']._xmlid_lookup('bi_website_cash_on_delivery.payment_provider_cod')[2]
		cod_obj = self.env['payment.provider'].sudo().browse(cod_obj)
		for p in self:
			p.update({'delivery_fees': 0.0})
			if p.cod_available == True:
				if cod_obj.delivery_fees:
					p.update({'delivery_fees': cod_obj.delivery_fees})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
