#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay template
"""
import importlib
import sys
from odoo import models, fields, api

importlib.reload(sys)
PYTHONIOENCODING = "UTF-8"
PRODUCT_PRICELIST = 'product.pricelist'
EBAY_SITE_POLICY = 'ebay.site.policy.ept'


class EbayTemplateEpt(models.Model):
    """
    Describes eBay Templates
    """
    _name = "ebay.template.ept"
    _description = "eBay Template"

    name = fields.Char('Template name', size=64, required=True, help="Name of Template")
    instance_id = fields.Many2one('ebay.instance.ept', 'eBay Instance', required=True, help="eBay Site")
    seller_id = fields.Many2one(
        'ebay.seller.ept', related='instance_id.seller_id', string='eBay sellers', help="eBay Seller")
    payment_option_ids = fields.Many2many(
        'ebay.payment.options', 'ebay_template_payment_rel', 'tmpl_id', 'option_id',
        "Payments", help="eBay Payment Options")
    hand_time = fields.Selection([
        ('0', 'Same Business Day'), ('1', '1 Business Day'), ('2', '2 Business Days'), ('3', '3 Business Days'),
        ('4', '4 Business Days'), ('5', '5 Business Days'), ('10', '10 Business Days'), ('15', '15 Business Days'),
        ('20', '20 Business Days'), ('30', '30 Business Days')
    ], string='Handling Tme', required=True, default="1", help="Business days in which order will be delivered")
    is_primary_shipping_address = fields.Boolean(
        'ShipToRegistrationCountry', default=False, help="If checked, Order will Ship to registration country")
    is_ebay_seller_policy = fields.Boolean(
        'Is eBay Seller Policy? ', default=False,
        help="If checked, eBay seller have Payment, shipping and return policies")
    unpaid_strike_id = fields.Many2one(
        "ebay.unpaid.item.strike.count", string="UnpaidItemStrikesCount",
        help="The number of the maximum unpaid item strikes.")
    unpaid_strike_duration_id = fields.Many2one(
        "ebay.unpaid.item.strike.duration", string="UnpaidItemStrikesDuration",
        help="The range of the maximum unpaid item strikes count.")
    item_count_id = fields.Many2one(
        "ebay.max.item.counts", string="MaximumItemCount", help="Maximum quantity for an order buyer can purchase")
    item_feedback_score_id = fields.Many2one(
        "item.feedback.score", string="MaxItemFeedbackScore", help="Returns values for minimum feedback score")
    return_policy = fields.Selection([
        ('ReturnsAccepted', 'Returns Accepted'), ('ReturnsNotAccepted', 'Returns Not Accepted')
    ], string='eBay Return Policy', default="ReturnsNotAccepted", required=True, help="Specifies Return Policy")
    return_days_id = fields.Many2one(
        "ebay.return.days", "ReturnsWithin", help="Values for no. of days in which buyer can return order")
    refund_option_id = fields.Many2one("ebay.refund.options", "RefundOption", help="Options for return order")
    extended_holiday_returns = fields.Boolean(
        "Is Extended Holiday Returns?", default=False, help="Is Extended Holiday Returns?")
    payment_instructions = fields.Text("Order Payment Instructions", help="Instructions for Order Payments")
    refund_shipping_cost_id = fields.Many2one(
        "ebay.refund.shipping.cost.options", "ShippingCostPaidBy",
        help="Options for shipping cost paid by when return order")
    restock_fee_id = fields.Many2one(
        "ebay.restock.fee.options", "RestockingFeeValue", help="Options for restock fee")
    return_policy_description = fields.Text('Additional return policy details', help="Descriptions for return policies")
    ship_type = fields.Selection([
        ('Flat', 'Flat:same cost to all buyers'), ('Calculated', 'Calculated:Cost varies to buyer location')
    ], default='Flat', string='Shipping Type', required=True, help="Type of shipping order")
    domestic_shipping_ids = fields.One2many(
        'shipping.service.ept', 'domestic_template_id', string='loc_idsShipping Services',
        help="Domestic Shipping locations")
    # ####International shipping fields#########
    int_ship_type = fields.Selection([
        ('Flat', 'Flat:same cost to all buyers'), ('Calculated', 'Calculated:Cost varies to buyer location')
    ], string='International Shipping Type', help="Types of international shipping order")
    inter_shipping_ids = fields.One2many(
        'shipping.service.ept', 'inter_template_id', string='International Shipping Services',
        help="Options for international shipping services")
    handling_cost = fields.Char(string='Handling Cost($)', default='0.00', size=20, help="Order handling costs")
    pack_type = fields.Selection([
        ('Letter', 'Letter'), ('LargeEnvelope', 'Large Envelope'),
        ('PackageThickEnvelope', 'Package(or thick package)'), ('LargePackage', 'Large Package')
    ], default='Letter', string='Package Type', help="Types of shipping packages")
    irreg_pack = fields.Boolean('Domestic Irregular Package', help="Domestic Irregular Package")
    min_weight = fields.Char('WeightMinor', size=5, help="Minimum weight of package")
    max_weight = fields.Char('WeightMajor', size=5, help="Maximum weight of package")
    inter_handling_cost = fields.Char(
        string='International Handling Cost($)', default='0.00', size=20, help="International Shipping Handling Costs")
    inter_pack_type = fields.Selection([
        ('BulkyGoods', 'Bulky goods'), ('Caravan', 'Caravan'), ('Cars', 'Cars'),
        ('CustomCode', 'Reserved for internal or future use.'), ('Europallet', 'Europallet'),
        ('ExpandableToughBags', 'Expandable Tough Bags'), ('ExtraLargePack', 'Extra Large Package/Oversize 3'),
        ('Furniture', 'Furniture'), ('IndustryVehicles', 'Industry vehicles'),
        ('LargeCanadaPostBox', 'Large Canada Post Box'),
        ('LargeCanadaPostBubbleMailer', 'Large Canada Post Bubble Mailer'), ('LargeEnvelope', 'LargeEnvelope'),
        ('Letter', 'Letter'), ('MailingBoxes', 'Mailing Boxes'), ('MediumCanadaPostBox', 'Medium Canada Post Box'),
        ('MediumCanadaPostBubbleMailer', 'Medium Canada Post Bubble Mailer'), ('Motorbikes', 'Motorbikes'),
        ('None', 'None'), ('OneWayPallet', 'Onewaypallet'), ('PackageThickEnvelope', 'Package/thick envelope'),
        ('PaddedBags', 'Padded Bags'), ('ParcelOrPaddedEnvelope', 'Parcel or padded Envelope'),
        ('Roll', 'Roll'), ('SmallCanadaPostBox', 'Small Canada Post Box'),
        ('SmallCanadaPostBubbleMailer', 'Small Canada Post Bubble Mailer'), ('ToughBags', 'Tough Bags'),
        ('UPSLetter', 'UPS Letter'), ('USPSFlatRateEnvelope', 'USPS Flat Rate Envelope'),
        ('USPSLargePack', 'USPS Large Package/Oversize 1'), ('VeryLargePack', 'Very Large Package/Oversize 2'),
        ('Winepak', 'Winepak')
    ], default=False, string='International Package Type', help="The nature of the package used to ship the item(s).")
    inter_irreg_pack = fields.Boolean('Irregular Package', help="Irregular Package")
    inter_min_weight = fields.Char(
        'WeightMinor (oz)', size=5,
        help="WeightMinor are used to specify the weight of a shipping package. "
             "i.e Here is how you would represent a package weight of 2 "
             "oz:\n <WeightMinor unit='oz'>2</WeightMinor>")
    inter_max_weight = fields.Char(
        'WeightMajor (lbs)', size=5,
        help="WeightMajor are used to specify the weight of a shipping package. "
             "i.e Here is how you would represent a package weight of 5 lbs"
             ":\n <WeightMajor unit='lbs'>5</WeightMajor>")
    additional_locations = fields.Selection([
        ('unitedstates', 'Will ship to United States and the Following'), ('Worldwide', 'Will ship worldwide')
    ], string='Additional ship to locations', help="Additional ship to locations")
    exclude_ship_location_ids = fields.Many2many(
        'ebay.exclude.shipping.locations', 'ebay_exclude_loc_rel', 'tmpl_id', 'ex_loc_id',
        string="Exclude Shipping Locations", help="Locations in which shipping will not be provided by seller")
    loc_ids = fields.Many2many(
        'ebay.shipping.locations', 'shp_temp_rel_add', 'locad_nm_add', 'locad_id_add',
        string='Additional shipping locations', help="Locations for additional shipping")
    site_id = fields.Many2one("ebay.site.details", "eBay Site", readonly=True)
    # Listing Configuration fields
    listing_type = fields.Selection([('FixedPriceItem', 'Fixed Price')], 'Type', default='FixedPriceItem',
                                    required=True, help="Type in which Products to be listed")
    duration_id = fields.Many2one('duration.time', 'Duration', help="Duration Of the Product on eBay")
    start_price_id = fields.Many2one(
        PRODUCT_PRICELIST, 'Start Price', required=False,
        help="Selected Pricelist will be applied to the Listing Products and set start price")
    reserve_price_id = fields.Many2one(
        PRODUCT_PRICELIST, 'Reserve Price', required=False,
        help="Selected Pricelist will be applied to the Listing Products and set reserve price")
    buy_it_nw_price_id = fields.Many2one(
        PRODUCT_PRICELIST, 'Buy It Now Price', required=False,
        help="Selected Pricelist will be applied to the Listing Products and set buy it now price")
    # eBay Seller Policy
    ebay_seller_payment_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="Seller Payment Policy", help="Options for Seller Payment Policy")
    ebay_seller_return_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="eBay Seller Return Policy", help="Options for Seller Return Policy")
    ebay_seller_shipping_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="Seller Shipping Policy", help="Options for Seller Shipping Policy")
    related_dynamic_desc = fields.Boolean(
        "Related Dynamic Description", related="instance_id.seller_id.use_dynamic_desc",
        store=False, help="Dynamic Description")
    desc_template_id = fields.Many2one(
        "ebay.description.template", string="Description Template", help="Set Custom Description Template")
    ebay_package_depth = fields.Char(string="Package Depth", help="Add Package Depth in inch(in.)")
    ebay_package_length = fields.Char(string="Package Length", help="Add Package Length in inch(in.)")
    ebay_package_width = fields.Char(string="Package Width", help="Add Package Width in inch(in.)")

    @api.onchange('instance_id')
    def onchange_instance(self):
        """
        Update site id,price and primary shipping address when instance is changed.
        """
        if self.instance_id:
            self.site_id = self.instance_id.site_id.id
            self.is_primary_shipping_address = self.instance_id.is_primary_shipping_address
            self.start_price_id = self.instance_id.pricelist_id.id
            self.buy_it_nw_price_id = self.instance_id.pricelist_id.id
            self.reserve_price_id = self.instance_id.pricelist_id.id
