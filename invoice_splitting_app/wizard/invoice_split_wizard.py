# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SplitInvoiceWiz(models.TransientModel):
	_name = "split.invoice.wiz"
	_description = 'Split Invoice'

	split_invoice_ids = fields.One2many('split.invoice.wiz.line', 'split_id')
	split_invoice_line_ids = fields.One2many('split.invoice.wiz.line', 'split_line_id')
	split_selection = fields.Selection(
		[('full_invoice', 'Full Invoice'), ('invoice_line', 'Invoice Line')],
		string='Split Selection',
		default='full_invoice')
	customer_or_supplier=fields.Many2one('res.partner',string="Customer")
	split_quantity=fields.Integer(string="Split Quantity")
	split_by_line=fields.Selection([('by_quantity','Quantity'), ('by_unit_price','Unit Price'), ('by_delete_lines','Delete Lines')],
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
				split_order_lines.append((0,0, {
					'split_id' : self.id,
					'split_line_id' : self.id,
					'product_id_split' : line.product_id.id,
					'product_id' : line.product_id.id,
					'product_description_split' : line.name,
					'product_description' : line.name,
					'product_quantity_split' : line.quantity,
					'product_quantity' : line.quantity,
					'product_unit_price_split' : line.price_unit,
					'product_unit_price' : line.price_unit,
					'invoice_line_id' : line.id,
					'split_qty' : 1,
					'price_subtotal' : line.price_subtotal,
					'invoice_text_ids' : [(6,0,line.tax_ids.ids)],
					'account_id' : line.account_id.id,
					'uom_id' : line.product_uom_id.id,
					'discount' : line.discount,
					'sale_line_id': line.sale_line_id.id,
				}))
			res.update({
				'split_invoice_ids': split_order_lines,
				'split_invoice_line_ids': split_order_lines,
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

				if self.split_quantity < 0.0:
					raise UserError("Sorry, Split Quantity is not less to the 0.0")
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
				for line in invoice.invoice_line_ids:
					inv_line_id = self.env['account.move.line'].\
						with_context(check_move_validity=False).create({
						'product_id': line.product_id.id,
						'name':line.name,
						'account_id':line.account_id.id,
						'quantity':self.split_quantity,
						'product_uom_id':line.product_uom_id.id,
						'price_unit':line.price_unit,
						'discount':line.discount,
						'tax_ids':[(6,0,line.tax_ids.ids)],
						'price_subtotal':line.price_subtotal,
						'sale_line_id': line.sale_line_id.id,
						'move_id': account_move.id
					})
					line.with_context(check_move_validity=False, skip_account_move_synchronization=True).update({'quantity':line.quantity - self.split_quantity})

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
					invoice_line_lst = []
					for line in self.split_invoice_ids:
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
						division=value.product_unit_price
						if value.split_price > division:
							raise UserError("You have not used split Price greater than the unit Price.")
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
						'invoice_cash_rounding_id':invoice.invoice_cash_rounding_id.id
					}
					account_move = self.env['account.move'].create(account_move_vals)
					invoice_line_lst = []
					for line in self.split_invoice_ids:
						inv_line_id = self.env['account.move.line'].\
							with_context(check_move_validity=False).create({
								'product_id': line.product_id.id,
								'name':line.product_description,
								'account_id':line.account_id.id,
								'quantity':line.product_quantity,
								'product_uom_id':line.uom_id.id,
								'price_unit':line.split_price,
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
								'price_unit':inv_line.price_unit - line.split_price
							})
							invoice_line_lst.append(inv_line.id)
						line.sale_line_id.update({'invoice_lines': [(6, 0, invoice_line_lst)]})

				# Delete Entry
				if self.split_by_line == 'by_delete_lines':
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
					for line in self.split_invoice_line_ids:
						invoice_line_lst = []
						line.invoice_line_id.with_context(check_move_validity=False).tax_ids = [(6, 0, [])]
						inv_line_id = self.env['account.move.line'].\
							with_context(check_move_validity=False).create({
								'product_id': line.product_id.id,
								'name':line.product_description,
								'account_id':line.account_id.id,
								'quantity':line.product_quantity,
								'product_uom_id':line.uom_id.id,
								'price_unit':line.product_unit_price,
								'discount':line.discount,
								'tax_ids':[(6,0,line.invoice_text_ids.ids)],
								'price_subtotal':line.price_subtotal,
								'sale_line_id': line.sale_line_id.id,
								'move_id': account_move.id
						})
						# New Acocunt Move
						invoice_line_lst.append(inv_line_id.id)
						line.sale_line_id.update({'invoice_lines': [(6, 0, invoice_line_lst)]})
						# Old Account Move
						line.invoice_line_id.with_context(check_move_validity=False).unlink()

						
class SplitInvoiceWizLine(models.TransientModel):
	_name = "split.invoice.wiz.line"
	_description = 'Split Invoice Line'

	split_id = fields.Many2one('split.invoice.wiz', 'Split Invoice')
	split_line_id = fields.Many2one('split.invoice.wiz', 'Split Invoice Line')
	product_id_split = fields.Many2one('product.product','Split Product')
	product_id = fields.Many2one('product.product', related='product_id_split', 
		string='Product', readonly=True, store=False)
	product_description_split = fields.Char(string="Split Description")
	product_description = fields.Char(related='product_description_split', 
		string='Description', readonly=True, store=False)
	product_quantity_split = fields.Float(string="Split Quantity")
	product_quantity = fields.Float(related='product_quantity_split', 
		string='Quantity', readonly=True, store=False)
	split_qty = fields.Float(string="Split Qty")
	product_unit_price_split = fields.Float(string="Split Unit Price")
	product_unit_price = fields.Float(related='product_unit_price_split', 
		string='Unit Price', readonly=True, store=False)
	split_price = fields.Float(string="Split Price",store=True)
	price_subtotal = fields.Float(string='Subtotal')
	invoice_text_ids = fields.Many2many('account.tax',string="Invoice Text")
	account_id = fields.Many2one('account.account',string="Account")
	uom_id = fields.Many2one('uom.uom',string="Unit of Measure")
	discount = fields.Float(string="Discount")
	invoice_line_id = fields.Many2one('account.move.line',string="Move Line")
	sale_line_id = fields.Many2one('sale.order.line', string='Order Line')




