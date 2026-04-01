from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Command


SKIP_PARTNER_VISIBILITY_SYNC_CTX_KEY = 'xt_skip_partner_visibility_sync'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    xt_visibility_company_ids = fields.Many2many(
        'res.company',
        'xt_res_partner_visibility_company_rel',
        'partner_id',
        'company_id',
        string='Visible en compañías',
        copy=False,
        readonly=True,
        help='Compañías en las que este contacto debe ser visible según la encapsulación multiempresa.',
    )
    xt_is_global_visibility = fields.Boolean(
        string='Visible en todas las compañías',
        copy=False,
        help='Permite que este contacto sea visible en todas las compañías. Solo disponible para administradores con acceso a todas las compañías.',
    )
    xt_can_edit_global_visibility = fields.Boolean(
        compute='_compute_xt_can_edit_global_visibility',
        help='Campo técnico para controlar si el usuario actual puede marcar la visibilidad global.',
    )

    @api.depends_context('uid')
    def _compute_xt_can_edit_global_visibility(self):
        can_edit = self.env.user._xt_has_all_companies_access()
        for partner in self:
            partner.xt_can_edit_global_visibility = can_edit

    def _xt_check_visibility_management_rights(self, vals_list):
        if self.env.context.get(SKIP_PARTNER_VISIBILITY_SYNC_CTX_KEY):
            return

        for vals in vals_list:
            if 'xt_visibility_company_ids' in vals:
                raise AccessError(
                    self.env._('La visibilidad por compañías de los contactos se calcula automáticamente y no se puede editar manualmente.')
                )
            if 'xt_is_global_visibility' in vals and not self.env.user._xt_has_all_companies_access():
                raise AccessError(
                    self.env._('Solo los usuarios con acceso a todas las compañías pueden marcar un contacto como global.')
                )

    def _xt_get_visibility_sync_scope(self):
        if not self:
            return self
        return self.sudo().with_context(active_test=False).search([('id', 'child_of', self.ids)])

    def _xt_get_computed_visibility_company_ids(self):
        self.ensure_one()
        if self.xt_is_global_visibility:
            return []

        company_ids = set()
        users = self.user_ids.with_context(active_test=False)
        if users:
            company_ids.update(users.mapped('company_ids').ids)

        linked_companies = self.env['res.company'].sudo().with_context(active_test=False).search([
            ('partner_id', '=', self.id),
        ])
        if linked_companies:
            company_ids.update(linked_companies.ids)

        if not company_ids and self.parent_id:
            company_ids.update(self.parent_id.xt_visibility_company_ids.ids)
            if self.parent_id.xt_is_global_visibility:
                return []

        commercial_partner = self.commercial_partner_id
        if not company_ids and commercial_partner and commercial_partner != self:
            company_ids.update(commercial_partner.xt_visibility_company_ids.ids)
            if commercial_partner.xt_is_global_visibility:
                return []

        if not company_ids and self.company_id:
            company_ids.add(self.company_id.id)

        return sorted(company_ids)

    def _xt_sync_visibility_companies(self):
        if self.env.context.get(SKIP_PARTNER_VISIBILITY_SYNC_CTX_KEY):
            return

        for partner in self.sudo().with_context(active_test=False):
            target_company_ids = set(partner._xt_get_computed_visibility_company_ids())
            current_company_ids = set(partner.xt_visibility_company_ids.ids)
            if current_company_ids == target_company_ids:
                continue
            super(ResPartner, partner.with_context(**{SKIP_PARTNER_VISIBILITY_SYNC_CTX_KEY: True})).write({
                'xt_visibility_company_ids': [Command.set(sorted(target_company_ids))],
            })

    @api.model
    def _xt_mark_default_global_partners(self):
        xmlids = ('base.partner_root', 'base.public_partner')
        for xmlid in xmlids:
            partner = self.env.ref(xmlid, raise_if_not_found=False)
            if partner and not partner.xt_is_global_visibility:
                super(ResPartner, partner.with_context(**{SKIP_PARTNER_VISIBILITY_SYNC_CTX_KEY: True})).write({
                    'xt_is_global_visibility': True,
                })

    @api.model_create_multi
    def create(self, vals_list):
        self._xt_check_visibility_management_rights(vals_list)
        partners = super().create(vals_list)
        partners._xt_get_visibility_sync_scope()._xt_sync_visibility_companies()
        return partners

    def write(self, vals):
        self._xt_check_visibility_management_rights([vals])
        partners_to_sync = self._xt_get_visibility_sync_scope()
        res = super().write(vals)
        if not self.env.context.get(SKIP_PARTNER_VISIBILITY_SYNC_CTX_KEY):
            partners_to_sync._xt_sync_visibility_companies()
        return res

