# -*- coding: utf-8 -*-

from odoo import api, fields, models


def _all_company_ids(env):
    return set(env['res.company'].sudo().with_context(active_test=False).search([]).ids)


class ResUsers(models.Model):
    _inherit = "res.users"

    see_all_companies = fields.Boolean(
        string="See All Companies",
        compute="_compute_see_all_companies",
        readonly=True,
        help="If checked, this user will bypass the strict company encapsulation rules.",
    )

    def _xt_has_all_companies_access(self):
        all_company_ids = _all_company_ids(self.env)
        for user in self:
            if user._is_admin():
                return True
            if not all_company_ids:
                return True
            if all_company_ids.issubset(set(user.company_ids.ids)):
                return True
        return False

    def _xt_sync_partner_visibility(self):
        partners = self.mapped('partner_id')
        if partners:
            partners._xt_get_visibility_sync_scope()._xt_sync_visibility_companies()

    def _xt_sync_partner_company_ids(self):
        partners = self.mapped('partner_id').sudo().with_context(active_test=False)
        for partner in partners:
            users = partner.user_ids.with_context(active_test=False)
            target_company_id = False
            if users:
                default_company_ids = {user.company_id.id for user in users if user.company_id}
                if len(default_company_ids) == 1 and all(len(user.company_ids) == 1 for user in users):
                    target_company_id = next(iter(default_company_ids))
            if partner.company_id.id != target_company_id:
                partner.write({'company_id': target_company_id})

    @api.depends('company_ids')
    def _compute_see_all_companies(self):
        for user in self:
            user.see_all_companies = user._xt_has_all_companies_access()

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._xt_sync_partner_company_ids()
        users._xt_sync_partner_visibility()
        return users

    def write(self, vals):
        partners_to_sync = self.mapped('partner_id')
        res = super().write(vals)
        if {'company_id', 'company_ids', 'partner_id'} & set(vals):
            users_to_sync = self.with_context(active_test=False)
            users_to_sync._xt_sync_partner_company_ids()
            (partners_to_sync | self.mapped('partner_id'))._xt_get_visibility_sync_scope()._xt_sync_visibility_companies()
        return res

