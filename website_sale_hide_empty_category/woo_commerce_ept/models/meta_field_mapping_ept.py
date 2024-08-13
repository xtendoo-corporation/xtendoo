# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger("WooCommerce")


class WooMetaFieldMappingEpt(models.Model):
    _name = "woo.meta.mapping.ept"
    _description = "WooCommerce Meta Field Mapping"

    # @api.model
    # def _default_date(self):
    #     instance_lang_id = self.env["woo.instance.ept"].browse(self._context.get('params').get('id')).woo_lang_id
    #     return instance_lang_id.date_format
    #
    # @api.model
    # def _default_time(self):
    #     instance_lang_id = self.env["woo.instance.ept"].browse(self._context.get('params').get('id')).woo_lang_id
    #     return instance_lang_id.time_format

    woo_meta_key = fields.Char('WooCommerce Meta Key')
    woo_operation = fields.Selection([
        ('import_product', 'Import Products'),
        ('import_customer', 'Import Customers'),
        ('import_unshipped_orders', 'Import Unshipped Orders'),
        ('import_completed_orders', 'Import Shipped Orders'),
        ('is_update_order_status', "Export Shippment Infomation / Update Order Status")], 'WooCommerce Operation')
    model_id = fields.Many2one('ir.model')
    field_id = fields.Many2one('ir.model.fields')
    instance_id = fields.Many2one("woo.instance.ept", copy=False, ondelete="cascade")
    field_type = fields.Char(compute="_compute_field_type")
    date_format = fields.Char(string='Date Format')
    time_format = fields.Char(string='Time Format')

    _sql_constraints = [
        ('_meta_mapping_unique_constraint', 'unique(woo_meta_key,instance_id,woo_operation,model_id)',
         'WooCommerce Meta Key, WooCommerce Operation and Model must be unique in the Meta Mapping '
         'as per WooCommerce Instance.')]

    @api.depends('field_id')
    def _compute_field_type(self):
        for meta_mapping_line in self:
            meta_mapping_line.field_type = meta_mapping_line.field_id.ttype

    def get_model_domain(self):
        model_name_list = ['res.partner', 'sale.order', 'stock.picking']
        data_dict = {
            'import_product': ['product.template', 'product.product'],
            'import_customer': model_name_list[:1],
            'import_unshipped_orders': model_name_list,
            'import_completed_orders': model_name_list,
            'is_update_order_status': model_name_list[1:],
        }
        return data_dict

    @api.onchange('woo_operation')
    def _onchange_operation(self):
        model_list = self.get_model_domain().get(self.woo_operation)
        return {'domain': {'model_id': [('model', 'in', model_list)]}}

    @api.onchange('field_id')
    def _onchange_field(self):
        if self.field_id.ttype in ['datetime', 'date']:
            if self.field_id.ttype == 'datetime':
                self.time_format = self.instance_id.woo_lang_id.time_format
            self.date_format = self.instance_id.woo_lang_id.date_format
