# -*- coding: utf-8 -*-
"""
Onboarding Controller.
"""
from odoo import http
from odoo.http import request


class WooCommerceOnboarding(http.Controller):
    """
    Controller for Onboarding (Banner).
    @author: Dipak Gogiya on Date 17-Sep-2020.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """

    @http.route('/woo_instances/woo_instances_onboarding_panel', auth='user', type='json')
    def woo_instances_onboarding_panel(self):
        """
        Returns the `banner` for the Woo onboarding panel.
        It can be empty if the user has closed it or if he doesn't have the permission to see it.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """

        current_company_id = request.httprequest.cookies.get('cids') and \
                             request.httprequest.cookies.get('cids').split(',') or []
        company = False
        if len(current_company_id) > 0 and current_company_id[0] and current_company_id[0].isdigit():
            company = request.env['res.company'].sudo().search([('id', '=', int(current_company_id[0]))])
        if not company:
            company = request.env.company
        if not request.env.is_admin() or \
                company.woo_onboarding_state == 'closed':
            return {}
        hide_panel = company.woo_onboarding_toggle_state != 'open'
        btn_value = 'Create more woo instance' if hide_panel else 'Hide On boarding Panel'

        return {
            "html": request.env['ir.qweb']._render("woo_commerce_ept.woo_instances_onboarding_panel_ept", {
                "company": company,
                "toggle_company_id": company.id,
                "hide_panel": hide_panel,
                "btn_value": btn_value,
                "state": company.get_and_update_woo_instances_onboarding_state(),
                "is_button_active": company.is_create_woo_more_instance
            })
        }
