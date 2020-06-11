from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_admin = fields.Boolean(
        comodel_name='product.template',
        compute='_is_admin',
        string="isAdmin",
        default=lambda self: self._get_default_admin()
    )

    @api.one
    def _is_admin(self):
        self.is_admin = self.env.user.administration
        return

    @api.model
    def _get_default_admin(self):
        return self.env.user.administration