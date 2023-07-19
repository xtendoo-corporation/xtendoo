#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay Feedbacks
"""
import logging
from datetime import date, timedelta
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
_EBAY_PRODUCT_LISTING_EPT = 'ebay.product.listing.ept'


class EbayFeedbackEpt(models.Model):
    """
    Describes eBay Feedback details
    """
    _name = "ebay.feedback.ept"
    _inherit = ['mail.thread']
    _rec_name = 'ebay_feedback_id'
    _description = "eBay Feedback"

    ebay_product_id = fields.Many2one(
        'ebay.product.product.ept', string="eBay Product", help="This field relocate ebay product.")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order", help="This field relocate sale order.")
    listing_id = fields.Many2one(
        _EBAY_PRODUCT_LISTING_EPT, string="eBay Listing", help="This field relocate eBay Product listing.")
    feedback_user_id = fields.Char(string="Ebay Feedback User Id", help="This field relocate Feedback user.")
    comment_time = fields.Date(
        string="Feedback Comment Time", required=False, help="This field relocate Display Date and Time of Comment.")
    comment_type = fields.Selection([
        ('Positive', 'Positive'), ('Negative', 'Negative'), ('Neutral', 'Neutral')
    ], string="Feedback Comment Type", default="Neutral", help="This field relocate eBay Comment type.")
    commenting_user_score = fields.Char(
        string="Feedback Commenting User Score", help="This field relocate eBay Commenting score.")
    comment_text = fields.Text(string="Comment", help="This field relocate eBay Comment Text.")
    ebay_feedback_id = fields.Char(string="FeedBack Id", required=True, help="This field relocate eBay Feedback.")
    instance_id = fields.Many2one('ebay.instance.ept', string="Instance", help="This field relocate eBay Site.")
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string="sale order line", help="This field relocate Sale Order line.")
    is_feedback = fields.Boolean(string="Is Feedback Given?", help="This field relocate Check is feedback.")

    def get_feedback(self, instances):
        """
        This method is use to get the feedback for the listing and order.
        Migration done by Haresh Mori @ Emipro on date 13 January 2022 .
        """
        process_import_export_obj = self.env["ebay.process.import.export"]
        ebay_product_listing_obj = self.env[_EBAY_PRODUCT_LISTING_EPT]
        feedback_ids = []
        for instance in instances:
            date_n_days_ago = date.today() - timedelta(days=10)
            product_listings = ebay_product_listing_obj.search(
                [('instance_id', '=', instance.id), '|', ('state', '=', 'Active'), ('end_time', '>=', date_n_days_ago)])
            for product_listing in product_listings:
                _logger.info("Processing product listing: %s for Feedback" % product_listing.name)
                feedback_ids = self.get_feedback_from_ebay_ept(instance, product_listing, feedback_ids)
        if feedback_ids and not self.env.context.get('is_auto_process', False):
            action_name = "ebay_ept.action_ebay_feedback"
            form_view_name = "ebay_ept.ebay_feedback_form"
            return process_import_export_obj.redirect_to_view(action_name, form_view_name, feedback_ids)
        return True

    def get_feedback_from_ebay_ept(self, instance, product_listing, feedback_ids):
        """
        This method is used to get the feed from the eBay store to Odoo and according to the response it will
        create/update the feedback in odoo.
        Migration done by Haresh Mori @ Emipro on date 13 January 2022 .
        """
        try:
            api = instance.get_trading_api_object()
            api.execute('GetFeedback', {'DetailLevel': 'ReturnAll', 'ItemID': product_listing.name})
            results = api.response.dict()
            feedback_results = results.get('FeedbackDetailArray', {}).get('FeedbackDetail', {})
            if isinstance(feedback_results, dict):
                feedback_results = [feedback_results]
            if any(feedback_results):
                feedback_ids = self.create_or_update_feedback_ept(feedback_results, instance, product_listing,
                                                                  feedback_ids)
        except Exception as error:
            raise UserError(str(error))
        return feedback_ids

    def create_or_update_feedback_ept(self, feedback_results, instance, product_listing, feedback_ids):
        """
        Creates Feedback for particular sale order in odoo.
        :param feedback_results: feedback received from ebay
        :param instance: instance of ebay
        :param product_listing: ebay product listing object
        :param feedback_ids: dictionary of eBay feedback ids
        :return : dictionary of eBay feedback ids
        """
        sale_order_line_obj = self.env['sale.order.line']
        for feedback_result in feedback_results:
            sale_order_lines = sale_order_line_obj.search(
                [('ebay_order_line_item_id', '=', feedback_result.get('OrderLineItemID', []))])
            for sale_order_line in sale_order_lines:
                sale_order = sale_order_line.order_id
                ebay_feedback = self.search_ebay_feedback(sale_order.id, feedback_result.get('FeedbackID', False))
                vals = self.prepare_feedback_vals_ept(sale_order.id, product_listing.id, feedback_result,
                                                      instance.id,
                                                      sale_order_line)
                if ebay_feedback:
                    ebay_feedback.write(vals)
                else:
                    ebay_feedback = self.create(vals)
                _logger.info("Create/update feedback name: %s" % ebay_feedback.ebay_feedback_id)
                feedback_ids.append(ebay_feedback.id)
        return feedback_ids

    def search_ebay_feedback(self, sale_order_id, ebay_feedback_id):
        """
        Search if feedback is exist or not.
        :param sale_order_id: Sale order id
        :param ebay_feedback_id: eBay feedback id received from eBay
        :return: eBay feedback ept object
        """
        return self.env['ebay.feedback.ept'].search([
            ('sale_order_id', '=', sale_order_id), ('ebay_feedback_id', '=', ebay_feedback_id)], limit=1)

    def prepare_feedback_vals_ept(self, sale_order_id, product_listing_id, feedback_result, instance_id,
                                  sale_order_line):
        """
        Create a new eBay Feedback.
        :param sale_order_id: Sale order id
        :param product_listing_id: product listing id
        :param feedback_result: Feedback results received from eBay.
        :param instance_id: eBay instance id
        :param sale_order_line: Sale order line object
        :return: Dictionary of eBay feedback ids
        """
        ebay_product_listing_obj = self.env[_EBAY_PRODUCT_LISTING_EPT]
        ebay_product = ebay_product_listing_obj.search_ebay_product_by_product_id(
            sale_order_line.product_id.id, instance_id)
        feedback_values = {
            'ebay_product_id': ebay_product.id,
            'sale_order_id': sale_order_id,
            'listing_id': product_listing_id,
            'feedback_user_id': feedback_result.get('CommentingUser', False),
            'comment_time': feedback_result.get('CommentTime', False),
            'comment_type': feedback_result.get('CommentType', False),
            'commenting_user_score': feedback_result.get('CommentingUserScore', False),
            'comment_text': feedback_result.get('CommentText', False),
            'ebay_feedback_id': feedback_result.get('FeedbackID', False),
            'instance_id': instance_id,
            'sale_order_line_id': sale_order_line.id,
            'is_feedback': True
        }
        return feedback_values

    def get_feedback_replay(self):
        """
        This method is used to open a wizard to replay feedback.
        @return: action
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13 Jan 2022.
        """
        view = self.env.ref('ebay_ept.ebay_feedback_wizard_view')
        return {
            'name': _('FeedBack Replay Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebay.feedback.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': self._context,
        }

    def send_feedback_reply_ept(self, response_text, response_type):
        """
        Send reply to the specific feedback.
        :param response_text: Reply text for feedback
        :param response_type: Response Type
        Migration done by Haresh Mori @ Emipro on date 13 January 2022 .
        """
        for ebay_feedback in self:
            ebay_order_line_item_id = self.sale_order_line_id.ebay_order_line_item_id
            transaction_id = ebay_order_line_item_id.split("-")[1]
            feedback_parameters = {
                'ItemID': self.sale_order_line_id.item_id, 'TransactionID': transaction_id,
                'ResponseText': response_text, 'ResponseType': response_type, 'TargetUserID': self.feedback_user_id}
            try:
                api = ebay_feedback.instance_id.get_trading_api_object()
                api.execute('RespondToFeedback', feedback_parameters)
                results = api.response.dict()
                ack = results.get('Ack')
                if ack == 'Success':
                    ebay_feedback.message_post(
                        body=_('<b>The FeedBack Message sent</b><br/>%s.', response_text))
            except Exception as error:
                raise UserError(str(error))
