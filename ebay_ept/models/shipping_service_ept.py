#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay shipping service
"""
import importlib
import sys
from odoo import models, fields, api

importlib.reload(sys)
PYTHONIOENCODING = "UTF-8"


class ShippingServiceEpt(models.Model):
    """
    Describes Shipping Services
    """
    _name = "shipping.service.ept"
    _description = "eBay Shipping Service"

    service_id = fields.Many2one('ebay.shipping.service', string='Shipping service', required=True)
    cost = fields.Char('Cost($)', size=20)
    additional_cost = fields.Char('Each Additional($)', size=20)
    is_free_shipping = fields.Boolean('Free Shipping')
    domestic_template_id = fields.Many2one('ebay.template.ept', string='Domestic Template')
    inter_template_id = fields.Many2one('ebay.template.ept', string='International Template')
    custom_loc = fields.Selection([
        ('Worldwide', 'Worldwide'), ('customloc', 'Choose Custom Location'), ('Canada', 'Canada')], string='Ship to')
    loc_ids = fields.Many2many(
        'ebay.shipping.locations', 'shp_temp_rel', 'locad_nm', 'locad_id', string='Additional shipping locations')
    ship_type = fields.Char(compute="_compute_get_ship_type", store=True, string='Shipping Type')
    int_ship_type = fields.Char(
        compute="_compute_get_ship_type", store=True, string='International Shipping Type')
    priority = fields.Integer("ShippingServicePriority", default=1, required=True)

    @api.depends('domestic_template_id.ship_type', 'inter_template_id.int_ship_type')
    def _compute_get_ship_type(self):
        """
        Calculate shipping type
        """
        self.ship_type = self.domestic_template_id.ship_type
        self.int_ship_type = self.inter_template_id.int_ship_type

    @api.onchange("is_free_shipping")
    def onchange_shipping(self):
        """
        Set cost to zero if free shipping is enabled
        """
        if self.is_free_shipping:
            self.cost = 0.0
            self.additional_cost = 0.0
