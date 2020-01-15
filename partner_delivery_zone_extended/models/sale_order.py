# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date

import logging


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_default_partner(self):
        zone_id = self._get_partner_delivery_zone()
        visit_ids = self.env['partner.delivery.zone.visit'].get_partner_visit_today(zone_id)
        for partner in self.env['partner.delivery.zone'].search(
            [('id', '=', zone_id)]).partner_ids.sorted(lambda p: p.sequence):
            if partner.id not in visit_ids:
                return partner

    def _get_partner_delivery_zone(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('selected.partner.delivery.zone', 0))

    delivery_zone_id = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string="Delivery Zone",
        ondelete='restrict',
        index=True,
        default=_get_partner_delivery_zone,
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True,
        change_default=True,
        index=True,
        track_visibility='always',
        track_sequence=1,
        help="You can find a customer by its Name, TIN, Email or Internal Reference.",
        default=_get_default_partner)

    # @api.onchange('partner_shipping_id')
    # def onchange_partner_shipping_id_delivery_zone(self):
    #     if self.partner_shipping_id.delivery_zone_ids:
    #         self.delivery_zone_id = self.partner_shipping_id.delivery_zone_id

    @api.multi
    def get_next_partner(self):
        if not self.delivery_zone_id:
            return

        # register the visit
        if self.partner_id.id:
            self.env['partner.delivery.zone.visit'].create_if_not_exist(self.delivery_zone_id.id, self.partner_id.id)

        # get next partner or error
        visit_ids = self.env['partner.delivery.zone.visit'].get_partner_visit_today(self.delivery_zone_id.id)

        for partner in self.delivery_zone_id.partner_ids.sorted(lambda p: p.sequence):
            if partner.id not in visit_ids:
                return partner

    @api.multi
    def button_next_partner(self):
        if not self.delivery_zone_id:
            return

        # register the visit
        if self.partner_id.id:
            self.env['partner.delivery.zone.visit'].create_if_not_exist(self.delivery_zone_id.id, self.partner_id.id)

        # get next partner or error
        visit_ids = self.env['partner.delivery.zone.visit'].get_partner_visit_today(self.delivery_zone_id.id)

        for partner in self.delivery_zone_id.partner_ids.sorted(lambda p: p.sequence):
            if partner.id not in visit_ids:
                self.partner_id = partner
                return

        raise ValidationError(_("No more partners in this delivery zone"))

    @api.model
    def create(self, vals):
        logging.info("create***************************************************")
        logging.info(vals)
        logging.info(self.partner_id.id)
        self.env['partner.delivery.zone.visit'].create_if_not_exist(vals['delivery_zone_id'], vals['partner_id'])
        return super(SaleOrder, self).create(vals)

{'require_payment': True, 'picking_policy': 'direct', 'warehouse_id': 1, 'opportunity_id': False, 'note': '', 'campaign_id': False, 'analytic_account_id': False, 'delivery_zone_id': 10, 'fiscal_position_id': False, 'client_order_ref': False, 'incoterm': False, 'medium_id': False, 'sale_order_template_id': False, 'source_id': False, 'partner_invoice_id': 19, 'validity_date': False, 'pricelist_id': 1, 'message_attachment_count': 0, 'user_id': 1, 'require_signature': True, 'company_id': 1, 'team_id': 1, 'commitment_date': False, 'payment_term_id': 3, 'origin': False, 'partner_id': 19, 'tag_ids': [[6, False, []]], 'partner_shipping_id': 19, 'date_order': '2020-01-15 12:06:21'}
