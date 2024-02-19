# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	def _prepare_invoice_line(self, **optional_values):
		"""
		Prepare the dict of values to create the new invoice line for a sales order line.

		:param qty: float quantity to invoice
		:param optional_values: any parameter that should be added to the returned invoice line
		"""
		self.ensure_one()
		res = {
			'display_type': self.display_type,
			'sequence': self.sequence,
			'name': self.name,
			'product_id': self.product_id.id,
			'product_uom_id': self.product_uom.id,
			'quantity': self.qty_to_invoice,
			'discount': self.discount,
			'price_unit': self.price_unit,
			'tax_ids': [(6, 0, self.tax_id.ids)],
			'sale_line_ids': [(4, self.id)],
			'sale_line_id': self.id,
		}
		if optional_values:
			res.update(optional_values)
		if self.display_type:
			res['account_id'] = False
		return res