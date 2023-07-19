#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Retrieves eBay Policies, Feedback score, Max item count,
minimum feedback score, unpaid item strike and duration.
"""
from odoo import models, fields


class EbayFeedbackScore(models.Model):
    """
    Creates Buyer Requirement & saves feedback score from eBay to Odoo.
    """
    _name = "ebay.feedback.score"
    _description = "eBay Feedback Score"

    name = fields.Char(string="Feedback Score", help="This field relocate eBay feedback score name.", required=True)
    site_ids = fields.Many2many(
        "ebay.site.details", 'ebay_feed_back_score_rel', 'feedback_id', 'site_id',
        help="This field relocate eBay Site Ids.", required=True)

    def create_buyer_requirement(self, instance, details):
        """
        Create Buyer Requirement Details of eBay
        :param instance: instance of eBay
        :param details: ebay details received from ebay API
        """
        site_id = instance.site_id.id
        self.create_or_update_ebay_feedback_score(details, site_id)
        self.create_or_update_ebay_item_feedback_score(details, site_id)
        self.create_or_update_ebay_max_item_count(details, site_id)
        self.create_or_update_ebay_unpaid_item_strike_count(details, site_id)
        self.create_or_update_ebay_unpaid_item_strike_duration(details, site_id)

    def create_or_update_ebay_feedback_score(self, details, site_id):
        """
        Create or update eBay Feedback Score.
        :param details: Response received from eBay.
        :param site_id: eBay site id
        """
        feedback_score = details.get('MinimumFeedbackScore', {}).get('FeedbackScore', [])
        self.create_or_update_buyer_requirements_values(feedback_score, site_id)

    def create_or_update_ebay_item_feedback_score(self, details, site_id):
        """
        Create or update eBay Item Feedback Score.
        :param details: Response received from eBay.
        :param site_id: eBay site id
        """
        item_feed_score_obj = self.env['item.feedback.score']
        item_feed_score = details.get('MaximumItemRequirements', {}).get('MinimumFeedbackScore', [])
        self.create_or_update_buyer_requirements_values(item_feed_score, site_id, item_feed_score_obj)

    def create_or_update_ebay_max_item_count(self, details, site_id):
        """
        Create or update eBay max item count.
        :param details: Response received from eBay.
        :param site_id: eBay site id
        """
        max_item_count_obj = self.env['ebay.max.item.counts']
        max_item_count = details.get('MaximumUnpaidItemStrikesInfo', {}).get('MaximumItemCount', [])
        self.create_or_update_buyer_requirements_values(max_item_count, site_id, max_item_count_obj)

    def create_or_update_ebay_unpaid_item_strike_count(self, details, site_id):
        """
        Create or update eBay unpaid item strike count.
        :param details: Response received from eBay.
        :param site_id: eBay site id
        """
        unpaid_strike_obj = self.env['ebay.unpaid.item.strike.count']
        max_unpaid_item_info = details.get('MaximumUnpaidItemStrikesInfo', {})
        max_unpaid_item_count = max_unpaid_item_info.get('MaximumUnpaidItemStrikesCount', {})
        unpaid_strike_count = max_unpaid_item_count.get('Count', '[]')
        self.create_or_update_buyer_requirements_values(unpaid_strike_count, site_id, unpaid_strike_obj)

    def create_or_update_buyer_requirements_values(self, buyer_requirements, site_id, buyer_requirement_obj=''):
        """
        Create or update buyer requirement values
        e.g. feedback score, item feedback score, max item count, unpaid item strike count
        :param buyer_requirements: Details received from eBay
        :param site_id: eBay site id
        :param buyer_requirement_obj: eBay Buyer requirement object
        """
        if buyer_requirement_obj == '':
            buyer_requirement_obj = self
        for value in buyer_requirements:
            exist_score = buyer_requirement_obj.search([('name', '=', value), ('site_ids', 'in', [site_id])])
            if not exist_score:
                exist_score = buyer_requirement_obj.search([('name', '=', value)])
                if not exist_score:
                    buyer_requirement_obj.create({'name': value, 'site_ids': [(6, 0, [site_id])]})
                else:
                    site_ids = list(set(exist_score.site_ids.ids + [site_id]))
                    exist_score.write({'site_ids': [(6, 0, site_ids)]})

    def create_or_update_ebay_unpaid_item_strike_duration(self, details, site_id):
        """
        Create or update eBay unpaid item strike duration.
        :param details: Response received from eBay.
        :param site_id: eBay site id
        """
        max_unpaid_item_info = details.get('MaximumUnpaidItemStrikesInfo', {})
        unpaid_strike_duration_obj = self.env['ebay.unpaid.item.strike.duration']
        unpaid_strike_duration = max_unpaid_item_info.get('MaximumUnpaidItemStrikesDuration', [])
        for record in unpaid_strike_duration:
            exist_record = unpaid_strike_duration_obj.search([
                ('name', '=', record.get('Period')), ('description', '=', record.get('Description')),
                ('site_ids', 'in', [site_id])])
            if not exist_record:
                exist_record = unpaid_strike_duration_obj.search([('name', '=', record.get('Period'))])
                if not exist_record:
                    unpaid_strike_duration_obj.create({'name': record.get('Period'), 'site_ids': [(6, 0, [site_id])]})
                else:
                    site_ids = list(set(exist_record.site_ids.ids + [site_id]))
                    exist_record.write({'site_ids': [(6, 0, site_ids)]})
