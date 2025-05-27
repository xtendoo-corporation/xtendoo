from odoo import models, fields

class PaymentProviderCOD(models.Model):
    _inherit = 'payment.provider'

    def _get_provider_types(self):
        types = super()._get_provider_types()
        types.append(('cod', 'Contrareembolso'))
        return types
