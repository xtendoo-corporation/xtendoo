# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _get_partner_delivery_zone(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('selected.partner.delivery.zone', 0))

    delivery_zone_id = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string="Delivery Zone",
        ondelete='restrict',
        index=True,
        default=_get_partner_delivery_zone,
    )
