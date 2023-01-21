# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class CODAcquirer(models.Model):
	_inherit = 'payment.provider'

	code = fields.Selection(selection_add=[('cod', 'Cash on Delivery')], ondelete={'cod': 'set default'})

	def _get_providers(self):
		providers = super(CODAcquirer, self)._get_providers()
		providers.append(['cod', _('Cash on Delivery')])
		return providers

	def cod_get_form_action_url(self):
		return '/cod/payment/feedback'

	def cod_compute_fees(self, amount, currency_id, country_id):
		""" Compute paypal fees.

			:param float amount: the amount to pay
			:param integer country_id: an ID of a res.country, or None. This is
									   the customer's country, to be compared to
									   the acquirer company country.
			:return float fees: computed fees
		"""
		if not self.fees_active:
			return 0.0
		country = self.env['res.country'].browse(country_id)
		if country and self.company_id.country_id.id == country.id:
			fixed = self.delivery_fees
		else:
			fixed = self.delivery_fees
		fees = fixed #(percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
		return fees

class CODPaymentTransaction(models.Model):
	_inherit = 'payment.transaction'

	@api.model
	def _cod_form_get_tx_from_data(self, data):
		reference, amount, currency_name = data.get('reference'), data.get('amount'), data.get('currency_name')
		tx = self.search([('reference', '=', reference)])
		tx.update({
			'state':'pending'
			})
		for order in tx.sale_order_ids:
			order.order_cod_available = True
		if not tx or len(tx) > 1:
			error_msg = _('received data for reference %s') % (pprint.pformat(reference))
			if not tx:
				error_msg += _('; no order found')
			else:
				error_msg += _('; multiple order found')
			_logger.info(error_msg)
			raise ValidationError(error_msg)

		return tx

	@api.model
	def _get_tx_from_notification_data(self, provider, data):
		""" Override of payment to find the transaction based on Sips data.

		:param str provider: The provider of the acquirer that handled the transaction
		:param dict data: The feedback data sent by the provider
		:return: The transaction if found
		:rtype: recordset of `payment.transaction`
		:raise: ValidationError if the data match no transaction
		:raise: ValidationError if the currency is not supported
		:raise: ValidationError if the amount mismatch
		"""
		tx = super()._get_tx_from_notification_data(provider, data)
		if provider != 'cod':
			return tx

		reference, amount, currency_name = data.get('reference'), data.get('amount'), data.get('currency_name')
		tx = self.search([('reference', '=', reference)])
		tx.update({
			'state': 'pending'
		})
		if not tx or len(tx) > 1:
			error_msg = _('received data for reference %s') % (pprint.pformat(reference))
			if not tx:
				error_msg += _('; no order found')
			else:
				error_msg += _('; multiple order found')
			_logger.info(error_msg)
			raise ValidationError(error_msg)

		return tx

	@api.model
	def _credit_form_get_tx_from_data(self, data):
		reference, amount, currency_name = data.get('reference'), data.get('amount'), data.get('currency_name')
		tx = self.search([('reference', '=', reference)])
		tx.update({
			'state':'pending'
			})
		if not tx or len(tx) > 1:
			error_msg = _('received data for reference %s') % (pprint.pformat(reference))
			if not tx:
				error_msg += _('; no order found')
			else:
				error_msg += _('; multiple order found')
			_logger.info(error_msg)
			raise ValidationError(error_msg)

		return tx

	def _get_specific_rendering_values(self, processing_values):
		""" Override of payment to return Alipay-specific rendering values.

		Note: self.ensure_one() from `_get_processing_values`

		:param dict processing_values: The generic and specific processing values of the transaction
		:return: The dict of acquirer-specific processing values
		:rtype: dict
		"""
		res = super()._get_specific_rendering_values(processing_values)
		if self.provider_id.code != 'cod':
			return res

		else :
			rendering_values = {
				'reference': self.reference,
				'tx_url': self.provider_id.cod_get_form_action_url(),
				'subject': self.reference,
				'currency': self.currency_id,
			}

		return rendering_values
