# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_partner_delivery_zone(self):
        if 'partner_delivery_zone_id' in request.session:
            return request.session['partner_delivery_zone_id']
        return 0

    def _get_default_partner(self):
        zone_id = self._get_partner_delivery_zone()
        visit_ids = self.env['partner.delivery.zone.visit'].get_partner_visit_today(zone_id)
        partner_zones_ids = self.env['partner.delivery.zone'].search(
            [('id', '=', zone_id)]).partner_zones_ids.sorted(
            lambda p: p.sequence)

        for partner_zone in partner_zones_ids:
            if partner_zone.partner_id not in visit_ids:
                return partner_zone.partner_id

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

        # get visits
        visit_ids = self.env['partner.delivery.zone.visit'].get_partner_visit_today(self.delivery_zone_id.id)

        for partner in self.delivery_zone_id.partner_zones_ids.sorted(lambda p: p.sequence):
            if partner.partner_id.id not in visit_ids:
                self.partner_id = partner.partner_id
                return

        raise ValidationError(_("No more partners in this delivery zone"))

    @api.model
    def create(self, vals):
        self.env['partner.delivery.zone.visit'].create_if_not_exist(vals['delivery_zone_id'], vals['partner_id'])
        return super(SaleOrder, self).create(vals)

