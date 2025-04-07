# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
import logging
import json
import base64
from datetime import datetime
_logger = logging.getLogger(__name__)
from odoo import models, fields, api, _
from odoo.tools import json_default

try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")


OPERATION = [('DELETE', 'DELETE'), ('UPDATE', 'UPDATE'), ('CREATE', 'CREATE')]
STATE = [('draft', 'Draft'), ('done', 'Done'), ('failed', 'Failed')]
PARTNERFIELD = ['name', 'street', 'city', 'state_id', 'country_id', 'vat', 'color', 'phone', 'zip', 'mobile', 'email', 'barcode', 'write_date', 'property_account_position_id', 'property_product_pricelist', 'company_name', 'property_supplier_payment_term_id', 'state_id', 'active']
PRODUCTFIELD = ['name', 'display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'product_tmpl_id', 'tracking', 'active', 'available_in_pos','optional_product_ids', 'attribute_line_ids','combo_ids', 'image_128']
PRICELSITFIELD = ['write_date', 'active', 'applied_on', 'base', 'base_pricelist_id', 'categ_id', 'company_id', 'compute_price', 'create_date', 'create_uid', 'currency_id', 'date_end', 'date_start', 'display_name', 'fixed_price', 'id', 'min_quantity', 'name', 'percent_price', 'price', 'price_discount', 'price_max_margin', 'price_min_margin', 'price_round', 'price_surcharge', 'pricelist_id', 'product_id', 'product_tmpl_id', 'write_date', 'write_uid']
IMAGEFIELDS = ['image_1024', 'image_1920', 'image_256', 'image_512', 'image_variant_1024', 'image_variant_128', 'image_variant_1920', 'image_variant_256', 'image_variant_512']

class CommonCacheNotification(models.Model):
    _name = 'common.cache.notification'
    _description = "Common Cache Notification"

    model_name = fields.Char('Model Name')
    record_id = fields.Integer('Record Id')
    operation = fields.Selection(selection= OPERATION)
    change_vals = fields.Text(string="Fields Changed")
    config_id = fields.Many2one("pos.config", string="Pos")
    state = fields.Selection(string='State', selection= STATE, default='draft')

    @property
    def get_active_mongo_config(self) -> object:
        return self.env['mongo.server.config'].search([('active_record', '=', True)], limit=1)
    
    @property
    def get_partner_fields(self) -> list:
        return PARTNERFIELD
    
    @property
    def get_product_fields(self) -> list:
        return PRODUCTFIELD
    
    def get_product_add_fields(self, vals):
        return list(set(PRODUCTFIELD + [str(data.name) for data in vals]))
    
    def get_partner_add_fields(self, vals):
        return list(set(PARTNERFIELD + [str(data.name) for data in vals]))

    @api.model_create_multi
    def create(self, vals):
        res = super(CommonCacheNotification, self).create(vals)
        try:
            mongo_server_rec = self.get_active_mongo_config
            mongo_server_rec.write({'is_updated':False})
        except Exception as e:
            _logger.info("<<      Exception in CommonCacheNotification      >>:%r", e)
        return res
    
    def create_pos_based_cache(self, data):
        active_configs = self.env['pos.config'].search([('active', '=', True)])
        for config in active_configs:
            data['config_id'] = config.id
            self.create(data)

    def _update_cache_file(self, bin_file, Updated_conv_data):
        json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8'))
        for data in Updated_conv_data:
            json_data[str(data.get("id"))] = data
        updated_data = base64.encodebytes(json.dumps(json_data, default=json_default).encode('utf-8'))
        bin_file.write({'server_data_cache': updated_data})
    
    def _sync_partner_cache(self, record, mongo_server_rec, partner_fields, product_fields, pricelist_json_data):
        partner = self.env[record.model_name].browse(record.record_id)
        if partner:
            if record.operation == "DELETE":
                bin_file = mongo_server_rec.find_related_partner_file(partner.id)
                if bin_file:
                    partner_json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8')) if bin_file.server_data_cache else False
                    if partner_json_data.get(str(record.record_id)):
                        del partner_json_data[str(record.record_id)]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
            else:
                if self._context.get('company_id') and self._context.get('uid'):
                    pro_data = partner.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read(partner_fields)
                else:
                    pro_data = partner.sudo().read(partner_fields)
                if len(pro_data):
                    partner_data = pro_data[0]
                    bin_file = mongo_server_rec.find_related_partner_file(partner_data['id'], create= record.operation == 'CREATE')
                    if bin_file and bin_file.server_data_cache:
                        self._update_cache_file(bin_file, pro_data)

    def _sync_product_cache(self, record, mongo_server_rec, partner_fields:list, product_fields:list, pricelist_json_data) ->None:
        product = self.env[record.model_name].browse(record.record_id)
        if product:
            if record.operation == 'delete':
                bin_file = mongo_server_rec.find_related_product_file(product.id)
                if bin_file:
                    product_json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8')) if bin_file.server_data_cache else False
                    if product_json_data.get(str(record.record_id)):
                        del product_json_data[str(record.record_id)]
            else:
                if self._context.get('company_id') and self._context.get('uid'):
                    pro_data = product.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read(product_fields)
                else:
                    pro_data = product.sudo().with_user(self.env.context['uid']).read(product_fields, load=False)
                if len(pro_data):
                    product_conv_data = pro_data[0]
                    image_fields = IMAGEFIELDS.copy()
                    new_field_list = set(image_fields).intersection(set(product_conv_data.keys()))
                    product_conv_data = [{k: v for k, v in product_conv_data.items() if k not in new_field_list}]
                    if len(product_conv_data):
                        bin_file = mongo_server_rec.find_related_product_file(product_conv_data[0]['id'], create = record.operation == 'CREATE' )
                        if bin_file and bin_file.server_data_cache:
                            self._update_cache_file(bin_file, product_conv_data)
                        
    def _sync_pricelist_cache(self, record, mongo_server_rec, partner_fields:list, product_fields:list, pricelist_json_data) ->None:
        pricelist_item = self.env[record.model_name].browse(
                            record.record_id)
        if pricelist_item:
            if record.operation == 'delete':
                if pricelist_json_data.get(str(record.record_id)):
                    del pricelist_json_data[str(record.record_id)]
            else:
                if self._context.get('company_id'):
                    pro_data = pricelist_item.sudo().with_company(self._context['company_id']).read()
                else:
                    pro_data = pricelist_item.sudo().read()
                if len(pro_data):
                    pricelist_conv_data = pro_data[0]
                    pricelist_data = pricelist_conv_data
            if len(pricelist_data) and pricelist_json_data:
                pricelist_json_data[pricelist_data.get("id")] = pricelist_data

    # Calling from get_data_on_sync(mongo config)
    @api.model
    def get_common_changes(self, config_id=None):
        if config_id: config_id = config_id.id
        records = self.sudo().search([('state', '!=', 'done'), ('config_id', '=', config_id)])
        mongo_server_rec = self.get_active_mongo_config
        load_pos_data_type = mongo_server_rec.load_pos_data_from

        if mongo_server_rec:
            # Getting static fields data
            partner_fields = self.get_partner_fields
            product_fields = self.get_product_fields
            pricelist_fields = PRICELSITFIELD

            # Append additional fields
            if mongo_server_rec.partner_field_ids:
                partner_fields = self.get_partner_add_fields(mongo_server_rec.partner_field_ids)

            if mongo_server_rec.product_field_ids:
                product_fields = self.get_product_add_fields(mongo_server_rec.product_field_ids)
            
            # include all fields
            if mongo_server_rec.partner_all_fields:
                if load_pos_data_type == 'postgres':
                    self._cr.execute(""" SELECT name FROM ir_model_fields WHERE model = 'res.partner' AND ttype NOT IN  ('binary', 'properties','properties_definition')""")
                    partner_fields = list(set(partner_fields).union(set([field[0] for field in self._cr.fetchall()])))
                else:
                    partner_fields = []

            if mongo_server_rec.product_all_fields:
                if load_pos_data_type == 'postgres':
                    self._cr.execute(""" SELECT name FROM ir_model_fields WHERE model = 'product.product' AND ttype NOT IN  ('binary', 'properties','properties_definition')""")
                    product_fields = list(set(product_fields).union(set([ field[0] for field in self._cr.fetchall()])))
                else:
                    product_fields = []

            # Loading pos cache
            if load_pos_data_type == 'postgres':
                self.sync_pos_cache(mongo_server_rec, records, partner_fields, product_fields)
            else:
                self.sync_mongo_cache(mongo_server_rec, records, partner_fields, product_fields, pricelist_fields)
                
            updated_records = self.search([('state', '=', 'done')], order="id desc")
            records_to_delete = []

            if len(updated_records): records_to_delete = updated_records[500:]
            if len(records_to_delete): records_to_delete.unlink()

            if not mongo_server_rec.is_ordinary_loading and mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                mongo_server_rec.cache_last_update_time = datetime.now()

    def sync_pos_cache(self, mongo_server_rec, records, partner_fields, product_fields):
        models_dict = {'res.partner':'partner','product.product':'product', 'product.pricelist.item': 'pricelist'}

        if not(len(records) and mongo_server_rec):
            mongo_server_rec.is_updated = True
        else:
            pricelist_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_pricelist_cache).decode('utf-8')) if mongo_server_rec.pos_pricelist_cache else False
            for record in records:
                model_name = models_dict.get(record.model_name,'')
                if hasattr(self, '_sync_%s_cache'%(model_name)):
                    getattr(self, '_sync_%s_cache'%(model_name))(record, mongo_server_rec, partner_fields, product_fields, pricelist_json_data)
                    
            if not mongo_server_rec.is_ordinary_loading:
                mongo_server_rec.cache_last_update_time = datetime.now()

            mongo_server_rec.is_updated = True
            if pricelist_json_data:
                updated_data = base64.encodebytes(json.dumps(pricelist_json_data, default=json_default).encode('utf-8'))
                if updated_data:
                    data_to_add = {'pos_pricelist_cache': updated_data}
                    mongo_server_rec.write(data_to_add)
                mongo_server_rec.price_last_update_time = datetime.now()

    def sync_mongo_cache(self, mongo_server_rec, records, partner_fields, product_fields, pricelist_fields):
        _logger.info("**************mongo working***********")
        client = mongo_server_rec.get_client()
        if client:
            database = self._cr.dbname
            if database in client.list_database_names():
                db = client[database]
                products_col = db.products
                partners_col = db.partners
                pricelist_items_col = db.pricelist_items
                if(len(records)):
                    for record in records:
                        try:
                            if record.operation == "UPDATE":
                                query = {"id": record.record_id}
                                values = []
                                change_vals = record.change_vals
                                record_fields_list = []
                                if change_vals:
                                    record_fields_list = change_vals.split(',')
                                if 'name' in record_fields_list or 'default_code' in record_fields_list:
                                    record_fields_list.append('display_name')
                                    if 'name' in record_fields_list:
                                        record_fields_list.remove('name')
                                if record.model_name == 'res.partner':
                                    partner = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if partner:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = partner.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = partner.sudo().read()
                                    if len(values):
                                        newvalues = {"$set":  values[0]}
                                        partners_col.update_one(
                                            query, newvalues, upsert=True)
                                    mongo_server_rec.partner_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.product':
                                    product = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if product:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = product.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = product.sudo().read()
                                    if len(values):
                                        newvalues = {"$set":  values[0]}
                                        products_col.update_one(
                                            query, newvalues, upsert=True)
                                    mongo_server_rec.product_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.pricelist.item':
                                    records = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    for data in records:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            field_data = data.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            field_data = data.sudo().read()
                                        if(field_data):
                                            date_start, date_end = (
                                                False, False)
                                            if data.date_start:
                                                date_start = datetime(
                                                    data.date_start.year, data.date_start.month, data.date_start.day) or False
                                            if data.date_end:
                                                date_end = datetime(
                                                    data.date_end.year, data.date_end.month, data.date_end.day) or False
                                            if date_start:
                                                field_data[0]['date_start'] = date_start
                                            if date_end:
                                                field_data[0]['date_end'] = date_end
                                            values.extend(field_data)
                                    if len(values):
                                        newvalues = {"$set":  values[0]}
                                        pricelist_items_col.update_one(
                                            query, newvalues, upsert=True)
                                    mongo_server_rec.price_last_update_time = datetime.now()
                                    record.state = 'done'
                            elif record.operation == "CREATE":
                                values = []
                                if record.model_name == 'res.partner':
                                    partner = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if partner:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = partner.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = partner.sudo().read()
                                    if len(values):
                                        partners_col.insert_one(values[0])
                                    mongo_server_rec.partner_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.product':
                                    product = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if product:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = product.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = product.sudo().read()
                                    if len(values):
                                        products_col.insert_one(values[0])
                                    mongo_server_rec.product_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.pricelist.item':
                                    records = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    for data in records:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            field_data = data.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            field_data = data.sudo().read()
                                        if(field_data):
                                            date_start, date_end = (
                                                False, False)
                                            if data.date_start:
                                                date_start = datetime(
                                                    data.date_start.year, data.date_start.month, data.date_start.day) or False
                                            if data.date_end:
                                                date_end = datetime(
                                                    data.date_end.year, data.date_end.month, data.date_end.day) or False
                                            if date_start:
                                                field_data[0]['date_start'] = date_start
                                            if date_end:
                                                field_data[0]['date_end'] = date_end
                                            values.extend(field_data)
                                    if len(values):
                                        pricelist_items_col.insert_one(
                                            values[0])
                                    mongo_server_rec.price_last_update_time = datetime.now()
                                    record.state = 'done'
                            elif record.operation == "DELETE":
                                query = {"id": record.record_id}
                                if record.model_name == 'res.partner':
                                    partners_col.delete_many(query)
                                elif record.model_name == 'product.product':
                                    products_col.delete_many(query)
                                elif record.model_name == 'product.pricelist.item':
                                    pricelist_items_col.delete_many(query)
                                record.state = 'done'
                        except Exception as e:
                            _logger.info(
                                "**************Exception*************:%r", e)
                            record.state = 'failed'
                    if not mongo_server_rec.is_ordinary_loading:
                        mongo_server_rec.cache_last_update_time = datetime.now()
                    mongo_server_rec.is_updated = True
                else:
                    mongo_server_rec.is_updated = True
