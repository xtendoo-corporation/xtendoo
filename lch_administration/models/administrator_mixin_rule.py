# -- coding: utf-8 --

from odoo import api, models, fields


class AdministratorMixinRule(models.Model):
    _name = 'administrator.mixin.rule'

    is_admin = fields.Boolean(
        compute='_is_admin',
        string="isAdmin",
        default=lambda self: self._get_default_admin()
    )
    @api.one
    def _is_admin(self):
        self.is_admin=self.env["res.users"].has_group(
                "lch_administration.administration_group"
            )

    @api.model
    def _get_default_admin(self):
        return self.env.self.env["res.users"].has_group(
                "lch_administration.administration_group"
            )


    can_edit_tax = fields.Boolean(
        compute='_can_edit_tax',
        string="Can edit Tax",
        default=lambda self: self._get_can_edit_tax()
    )

    @api.one
    def _can_edit_tax(self):
        self.can_edit_tax = self.env["res.users"].has_group(
                "lch_administration.edit_tax"
            )

    @api.model
    def _get_can_edit_tax(self):
        return self.env["res.users"].has_group(
                "lch_administration.edit_tax"
            )

    can_edit_discounts = fields.Boolean(
        compute='_can_edit_discounts',
        string="Can edit discounts",
        default=lambda self: self._get_can_edit_discounts()
    )

    @api.one
    def _can_edit_discounts(self):
        self.can_edit_discounts = self.env["res.users"].has_group(
                "lch_administration.edit_discounts"
            )

    @api.model
    def _get_can_edit_discounts(self):
        return self.env["res.users"].has_group(
                "lch_administration.edit_discounts"
            )

    can_edit_price = fields.Boolean(
        compute='_can_edit_price',
        string="Can edit price",
        default=lambda self: self._get_can_edit_price()
    )

    @api.one
    def _can_edit_price(self):
        self.can_edit_price = self.env["res.users"].has_group(
                "lch_administration.edit_sale_price"
            )

    @api.model
    def _get_can_edit_price(self):
        return self.env["res.users"].has_group(
                "lch_administration.edit_sale_price"
            )



    

