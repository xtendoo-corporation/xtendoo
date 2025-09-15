# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv.expression import OR

from odoo.addons.payment_cashondelivery import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'
    is_published = fields.Boolean('Publicado en web', default=True)

    _sql_constraints = [(
        'cashondelivery_providers_setup',
        "CHECK(cashondelivery_mode IS NULL OR (code = 'cashondelivery' AND cashondelivery_mode IS NOT NULL))",
        "Only cashondelivery providers should have a cashondelivery mode."
    )]

    code = fields.Selection(
        selection_add=[('cashondelivery', "Custom")], ondelete={'cashondelivery': 'set default'}
    )
    cashondelivery_mode = fields.Selection(
        string="Custom Mode",
        selection=[('cashondelivery', "Contrarreembolso")],
        required_if_provider='cashondelivery',
    )
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by contrarreembolso.")

    @api.model_create_multi
    def create(self, values_list):
        providers = super().create(values_list)
        providers.filtered(lambda p: p.cashondelivery_mode == 'cashondelivery').pending_msg = None
        return providers

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'cashondelivery').update({
            'show_credentials_page': False,
            'show_pre_msg': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

    def action_recompute_pending_msg(self):
        """ Recompute the pending message to include the existing bank accounts. """
        account_payment_module = self.env['ir.module.module']._get('account_payment')
        if account_payment_module.state == 'installed':
            for provider in self.filtered(lambda p: p.cashondelivery_mode == 'cashondelivery'):
                company_id = provider.company_id.id
                accounts = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company_id),
                    ('type', '=', 'bank'),
                ]).bank_account_id
                account_names = "".join(f"<li><pre>{account.display_name}</pre></li>" for account in accounts)
                provider.pending_msg = f'<div>' \
                    f'<h5>{_("Please use the following transfer details")}</h5>' \
                    f'<p><br></p>' \
                    f'<h6>{_("Bank Account") if len(accounts) == 1 else _("Bank Accounts")}</h6>' \
                    f'<ul>{account_names}</ul>'\
                    f'<p><br></p>' \
                    f'</div>'

    @api.model
    def _get_removal_domain(self, provider_code):
        return OR([
            super()._get_removal_domain(provider_code),
            [('code', '=', 'cashondelivery'), ('cashondelivery_mode', '=', provider_code)],
        ])

    @api.model
    def _get_removal_values(self):
        """ Override of `payment` to nullify the `cashondelivery_mode` field. """
        res = super()._get_removal_values()
        res['cashondelivery_mode'] = None
        return res

    def _transfer_ensure_pending_msg_is_set(self):
        transfer_providers_without_msg = self.filtered(
            lambda p: p.cashondelivery_mode == 'cashondelivery' and not p.pending_msg
        )
        if transfer_providers_without_msg:
            transfer_providers_without_msg.action_recompute_pending_msg()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.cashondelivery_mode != 'cashondelivery':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _get_specific_rendering_values(self, processing_values):
        if self.code == 'cashondelivery':
            # No hace falta renderización especial
            return {}
        return super()._get_specific_rendering_values(processing_values)

    def _get_form_action_url(self):
        if self.code == 'cashondelivery':
            # No necesita acción/formulario externo
            return None
        return super()._get_form_action_url()
