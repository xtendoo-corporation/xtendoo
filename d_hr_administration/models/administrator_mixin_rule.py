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
                "d_hr_administration.administration"
            )

    @api.model
    def _get_default_admin(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.administration"
            )


    can_edit_tax = fields.Boolean(
        compute='_can_edit_tax',
        string="Can edit Tax",
        default=lambda self: self._get_can_edit_tax()
    )

    @api.one
    def _can_edit_tax(self):
        self.can_edit_tax = self.env["res.users"].has_group(
                "d_hr_administration.edit_tax"
            )

    @api.model
    def _get_can_edit_tax(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_tax"
            )

    can_edit_discounts = fields.Boolean(
        compute='_can_edit_discounts',
        string="Can edit discounts",
        default=lambda self: self._get_can_edit_discounts()
    )

    @api.one
    def _can_edit_discounts(self):
        self.can_edit_discounts = self.env["res.users"].has_group(
                "d_hr_administration.edit_discounts"
            )

    @api.model
    def _get_can_edit_discounts(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_discounts"
            )

    can_edit_price = fields.Boolean(
        compute='_can_edit_price',
        string="Can edit price",
        default=lambda self: self._get_can_edit_price()
    )

    @api.one
    def _can_edit_price(self):
        self.can_edit_price = self.env["res.users"].has_group(
                "d_hr_administration.edit_sale_price"
            )

    @api.model
    def _get_can_edit_price(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_sale_price"
            )

    can_edit_account = fields.Boolean(
        compute='_can_edit_account',
        string="Can edit account",
        default=lambda self: self._get_can_edit_account()
    )

    @api.one
    def _can_edit_account(self):
        self.can_edit_account = self.env["res.users"].has_group(
                "d_hr_administration.edit_account"
            )

    @api.model
    def _get_can_edit_account(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_account"
            )

    can_edit_quantity = fields.Boolean(
        compute='_can_edit_quantity',
        string="Can edit quantity",
        default=lambda self: self._get_can_edit_quantity()
    )

    @api.one
    def _can_edit_quantity(self):
        self.can_edit_quantity = self.env["res.users"].has_group(
                "d_hr_administration.edit_quantity"
            )

    @api.model
    def _get_can_edit_quantity(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_quantity"
            )

    can_edit_product_desc = fields.Boolean(
        compute='_can_edit_product_desc',
        string="Can edit product_desc",
        default=lambda self: self._get_can_edit_product_desc()
    )

    @api.one
    def _can_edit_product_desc(self):
        self.can_edit_product_desc = self.env["res.users"].has_group(
                "d_hr_administration.edit_product_desc"
            )

    @api.model
    def _get_can_edit_product_desc(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_product_desc"
            )

    can_edit_product_id = fields.Boolean(
        compute='_can_edit_product_id',
        string="Can edit product_id",
        default=lambda self: self._get_can_edit_product_desc()
    )

    @api.one
    def _can_edit_product_id(self):
        self.can_edit_product_id = self.env["res.users"].has_group(
                "d_hr_administration.edit_product_id"
            )

    @api.model
    def _get_can_edit_product_desc(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.edit_product_id"
            )
    can_cancel_invoice = fields.Boolean(
        compute='_can_cancel_invoice',
        string="Can cancel Invoice",
        default=lambda self: self._get_can_cancel_invoice()
    )

    @api.one
    def _can_cancel_invoice(self):
        self.can_cancel_invoice = self.env["res.users"].has_group(
                "d_hr_administration.cancel_invoice"
            )

    @api.model
    def _get_can_cancel_invoice(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.cancel_invoice"
            )
    can_create_refund_invoice = fields.Boolean(
        compute='_can_create_refund_invoice',
        string="Can create refund Invoice",
        default=lambda self: self._get_can_create_refund_invoice()
    )

    @api.one
    def _can_create_refund_invoice(self):
        self.can_create_refund_invoice = self.env["res.users"].has_group(
                "d_hr_administration.create_refund_invoice"
            )

    @api.model
    def _get_can_create_refund_invoice(self):
        return self.env["res.users"].has_group(
                "d_hr_administration.create_refund_invoice"
            )


    

