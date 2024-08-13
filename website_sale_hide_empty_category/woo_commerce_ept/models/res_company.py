# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
""" Usage : Inherit the model res company and added and manage the functionality of Onboarding Panel"""
from odoo import fields, models, api

WOO_ONBOARDING_STATES = [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"), ('closed', "Closed")]


class ResCompany(models.Model):
    """
    Inherit Class and added and manage the functionality of Onboarding (Banner) Panel
    """
    _inherit = 'res.company'

    # Woo Onboarding Panel
    woo_onboarding_state = fields.Selection(selection=WOO_ONBOARDING_STATES,
                                            string="State of the Woo onboarding panel", default='not_done')
    woo_instance_onboarding_state = fields.Selection(selection=WOO_ONBOARDING_STATES,
                                                     string="State of the woo instance onboarding panel",
                                                     default='not_done')
    woo_basic_configuration_onboarding_state = fields.Selection(WOO_ONBOARDING_STATES,
                                                                string="State of the woo basic configuration "
                                                                       "onboarding step",
                                                                default='not_done')
    woo_financial_status_onboarding_state = fields.Selection(WOO_ONBOARDING_STATES,
                                                             string="State of the onboarding woo financial status step",
                                                             default='not_done')
    woo_cron_configuration_onboarding_state = fields.Selection(WOO_ONBOARDING_STATES,
                                                               string="State of the onboarding woo cron "
                                                                      "configurations step",
                                                               default='not_done')
    is_create_woo_more_instance = fields.Boolean(string='Is create woo more instance?', default=False)
    woo_onboarding_toggle_state = fields.Selection(selection=[('open', "Open"), ('closed', "Closed")],
                                                   default='open')

    @api.model
    def action_close_woo_instances_onboarding_panel(self):
        """ Mark the onboarding panel as closed. """
        self.env.company.woo_onboarding_state = 'closed'

    def get_and_update_woo_instances_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        steps = [
            'woo_instance_onboarding_state',
            'woo_basic_configuration_onboarding_state',
            'woo_financial_status_onboarding_state',
            'woo_cron_configuration_onboarding_state',
        ]
        return self._get_and_update_onboarding_state('woo_onboarding_state', steps)

    def action_toggle_woo_instances_onboarding_panel(self):
        """
        Use: To change and pass the value of selection of current company to hide / show panel.
        :return Selection Value
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 07/10/2020
        """
        self.woo_onboarding_toggle_state = 'closed' if self.woo_onboarding_toggle_state == 'open' else 'open'
        return self.woo_onboarding_toggle_state
