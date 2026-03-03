# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    see_all_companies = fields.Boolean(
        string="See All Companies",
        compute="_compute_see_all_companies",
        store=True,
        readonly=False,
        help="If checked, this user will bypass the strict company encapsulation rules.",
    )

    @api.depends('company_ids', 'groups_id')
    def _compute_see_all_companies(self):
        all_companies = self.env['res.company'].sudo().search([])
        all_company_ids = set(all_companies.ids)
        for user in self:
            if user._is_admin() or user.has_group('base.group_system'):
                user.see_all_companies = True
            elif all_company_ids and set(user.company_ids.ids) >= all_company_ids:
                user.see_all_companies = True
            else:
                user.see_all_companies = False

