# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SplitInvoiceWiz(models.TransientModel):
	_name = "split.invoice.wiz"
	_description = 'Split Invoice'

	split_invoice_ids = fields.One2many('split.invoice.wiz.line', 'split_id')
	split_selection = fields.Selection(
		[('full_invoice', 'Full Invoice'), ('invoice_line', 'Invoice Line')],
		string='Split Selection',
		default='full_invoice')
	customer_or_supplier=fields.Many2one('res.partner',string="Customer")
	split_quantity=fields.Integer(string="Split Quantity")
	split_by_line=fields.Selection([('by_quantity','Quantity'), ('by_unit_price','Unit Price')],
		string="Split Line By",
		default='by_quantity')
	payment_term_id = fields.Many2one('account.payment.term',string="Payment Terms")
	date_due=fields.Date(string="Duo Date")
	user_id=fields.Many2one('res.users',string="Salesperson")
	team_id=fields.Many2one('crm.team',string="Sales Team")

	@api.model
	def default_get(self, fields):
		res=super(SplitInvoiceWiz, self).default_get(fields)
		active_ids=self._context.get('active_ids')
		invoice_order_ids=self.env['account.move'].browse(active_ids)
		split_order_lines=[]
		for order in invoice_order_ids:
			for line in order.invoice_line_ids:
				split_order_lines.append({
							'split_id':self.id,
							'product_id':line.product_id.id,
							'product_description':line.name,
							'product_quantity':line.quantity,
							'product_unit_price':line.price_unit,
							'invoice_line_id':line.id,
							'split_qty':1,
							'price_subtotal':line.price_subtotal,
							'invoice_text_ids':[(6,0,line.tax_ids.ids)],
							'account_id':line.account_id.id,
							'uom_id':line.product_uom_id.id,
							'discount':line.discount,
							'sale_line_id': line.sale_line_id.id,
					})
			res.update({
				'split_invoice_ids': [(0,0,split_order_line) for split_order_line in split_order_lines],
				'customer_or_supplier':order.partner_id.id,
				'payment_term_id':order.invoice_payment_term_id.id,
				'date_due':order.invoice_date,
				'user_id':order.invoice_user_id.id,
				'team_id':order.team_id.id
			})
		return res

	def button_split(self):
		invoice_order_ids = self.env['account.move'].browse(self.env.context.get('active_ids'))
		for invoice in invoice_order_ids:
			if invoice.state != 'draft':
				raise UserError("Only Draft invoice Record Can be splitted.")
			if self.split_selection == 'full_invoice':
				if self.split_quantity ==  False:
					raise UserError("You need to add split Quantity.")
				account_move_vals = {
					'invoice_origin': invoice.invoice_origin,
					'journal_id':invoice.journal_id.id,
					'move_type':invoice.move_type,
					'partner_id': invoice.partner_id.id ,
					'invoice_date': invoice.invoice_date,
					'invoice_date': invoice.invoice_date,
					'invoice_payment_term_id': invoice.invoice_payment_term_id.id,
					'invoice_user_id':invoice.invoice_user_id.id,
					'team_id':invoice.team_id.id,
					'partner_shipping_id':invoice.partner_shipping_id.id,
					'invoice_cash_rounding_id':invoice.invoice_cash_rounding_id.id}
				account_move = self.env['account.move'].create(account_move_vals)
				invoice_line_ids = []
				count=0
				for line in invoice.invoice_line_ids:
					if count >= self.split_quantity:
						break
					inv_line_id = self.env['account.move.line'].\
						with_context(check_move_validity=False).create({
						'product_id': line.product_id.id,
						'name':line.name,
						'account_id':line.account_id.id,
						'analytic_account_id':line.analytic_account_id.id,
						'quantity':line.quantity,
						'product_uom_id':line.product_uom_id.id,
						'price_unit':line.price_unit,
						'discount':line.discount,
						'tax_ids':[(6,0,line.tax_ids.ids)],
						'price_subtotal':line.price_subtotal,
						'sale_line_id': line.sale_line_id.id,
						'move_id': account_move.id
					})
					inv_line_id.sale_line_id.update({'invoice_lines': [(6, 0, inv_line_id.ids)]})
					count+=1
					line.with_context(check_move_validity=False, skip_account_move_synchronization=True).unlink()


			if self.split_selection == 'invoice_line':
				# Split By Quantity
				if self.split_by_line == 'by_quantity':
					account_move_vals = {
						'invoice_origin': invoice.invoice_origin,
						'journal_id':invoice.journal_id.id,
						'move_type':invoice.move_type,
						'partner_id': invoice.partner_id.id ,
						'invoice_date': invoice.invoice_date,
						'invoice_date': invoice.invoice_date,
						'invoice_payment_term_id': invoice.invoice_payment_term_id.id,
						'invoice_user_id':invoice.invoice_user_id.id,
						'team_id':invoice.team_id.id,
						'partner_shipping_id':invoice.partner_shipping_id.id,
						'invoice_cash_rounding_id':invoice.invoice_cash_rounding_id.id}
					account_move = self.env['account.move'].create(account_move_vals)
					for line in self.split_invoice_ids:
						invoice_line_lst = []
						inv_line_id = self.env['account.move.line'].\
							with_context(check_move_validity=False).create({
								'product_id': line.product_id.id,
								'name':line.product_description,
								'account_id':line.account_id.id,
								'quantity':line.split_qty,
								'product_uom_id':line.uom_id.id,
								'price_unit':line.product_unit_price,
								'discount':line.discount,
								'tax_ids':[(6,0,line.invoice_text_ids.ids)],
								'price_subtotal':line.price_subtotal,
								'sale_line_id': line.sale_line_id.id,
								'move_id': account_move.id
						})
						invoice_line_lst.append(inv_line_id.id)
						invoice_line_ids =self.env['account.move.line'].with_context(check_move_validity=False).search([('id','in',line.invoice_line_id.ids)])
						for inv_line in invoice_line_ids:
							inv_line.with_context(check_move_validity=False, skip_account_move_synchronization=True).update({'quantity':inv_line.quantity - line.split_qty})
							invoice_line_lst.append(inv_line.id)
						line.sale_line_id.update({'invoice_lines': [(6, 0, invoice_line_lst)]})

				# Split By Unit Price
				if self.split_by_line == 'by_unit_price':
					for value in self.split_invoice_ids:
						division=value.product_unit_price / 2
						if value.split_price > division:
							raise UserError("Please Enter half split price of Actual Unit Price.")
						if value.split_price < division:
							raise UserError("Please Enter half split price of Actual Unit Price.")
					account_move_vals = {
						'invoice_origin': invoice.invoice_origin,
						'journal_id':invoice.journal_id.id,
						'move_type':invoice.move_type,
						'partner_id': invoice.partner_id.id ,
						'invoice_date': invoice.invoice_date,
						'invoice_date': invoice.invoice_date,
						'invoice_payment_term_id': invoice.invoice_payment_term_id.id,
						'invoice_user_id':invoice.invoice_user_id.id,
						'team_id':invoice.team_id.id,
						'partner_shipping_id':invoice.partner_shipping_id.id,
						'invoice_cash_rounding_id':invoice.invoice_cash_rounding_id.id}
					account_move = self.env['account.move'].create(account_move_vals)
					for line in self.split_invoice_ids:
						invoice_line_lst = []
						inv_line_id = self.env['account.move.line'].\
							with_context(check_move_validity=False).create({
								'product_id': line.product_id.id,
								'name':line.product_description,
								'account_id':line.account_id.id,
								'quantity':line.product_quantity/2,
								'product_uom_id':line.uom_id.id,
								'price_unit':line.product_unit_price/2,
								'discount':line.discount,
								'tax_ids':[(6,0,line.invoice_text_ids.ids)],
								'price_subtotal':line.price_subtotal,
								'sale_line_id': line.sale_line_id.id,
								'move_id': account_move.id,
						})
						invoice_line_lst.append(inv_line_id.id)
						invoice_line_ids =self.env['account.move.line'].with_context(check_move_validity=False).search([('id','in',line.invoice_line_id.ids)])
						for inv_line in invoice_line_ids:
							inv_line.with_context(check_move_validity=False, skip_account_move_synchronization=True).update({
								'price_unit':line.product_unit_price/2,
								'quantity':line.product_quantity/2,
							})
							invoice_line_lst.append(inv_line.id)
						line.sale_line_id.update({'invoice_lines': [(6, 0, invoice_line_lst)]})


class SplitInvoiceWizLine(models.TransientModel):
	_name = "split.invoice.wiz.line"
	_description = 'Split Invoice Line'

	split_id = fields.Many2one('split.invoice.wiz', 'Barcode labels')
	product_id = fields.Many2one('product.product',' Product')
	product_description=fields.Char(string="Description")
	product_quantity=fields.Float(string="Quantity")
	split_qty=fields.Float(string="Split Qty")
	product_unit_price=fields.Float(string="Unit Price")
	split_price=fields.Float(string="Split Price")
	price_subtotal = fields.Float(string='Subtotal')
	invoice_text_ids=fields.Many2many('account.tax',string="Invoice Text")
	account_id=fields.Many2one('account.account',string="Account")
	uom_id=fields.Many2one('uom.uom',string="Unit of Measure")
	discount=fields.Float(string="Discount")
	invoice_line_id = fields.Many2one('account.move.line',string="Move Line")
	sale_line_id = fields.Many2one('sale.order.line', string='Order Line')




