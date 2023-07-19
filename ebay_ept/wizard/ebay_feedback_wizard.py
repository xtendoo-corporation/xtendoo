#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay feedback wizard.
"""
from odoo import models, fields


class EbayFeedbackWizard(models.TransientModel):
    """
    Describes eBay Feedback wizard
    """
    _name = "ebay.feedback.wizard"
    _description = "eBay Feedback Wizard"
    response_text = fields.Text("Comment", required=True)
    response_type = fields.Selection(
        [
            ('CustomCode', 'CustomCode'), ('FollowUp', 'FollowUp'), ('Reply', 'Reply')
        ], string="eBay Response Type", default="Reply", required=True,
        help="CustomCode:-Reserved for future use.FollowUp:-This enumeration value is used"
             " in the ResponseType field of a RespondToFeedback call if the user is following"
             " up on a Feedback entry comment left by another user.Reply:-(in) This enumeration"
             " value is used in the ResponseType field of a RespondToFeedback call if the user"
             " is replying to a Feedback entry left by another user.")

    def feedback_replay_in_ebay(self):
        """
        This method is used to send feedback reply into eBay store.
        Migration done by Haresh Mori @ Emipro on date 13 January 2022 .
        """
        self.ensure_one()
        response_text = self.response_text
        response_type = self.response_type
        ebay_feedback_obj = self.env['ebay.feedback.ept']
        feedback_record = ebay_feedback_obj.browse(self._context.get('active_id', False))
        return feedback_record.send_feedback_reply_ept(response_text, response_type)
