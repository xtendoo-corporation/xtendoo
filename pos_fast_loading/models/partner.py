# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import json
import base64
import logging
from odoo.http import request
_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")
from datetime import datetime

class ResPartner(models.Model):
    _inherit = "res.partner"

    def mongo_server_validation(self, is_indexed_updated, mongo_server_rec_read, load_pos_data_type=''):
        if load_pos_data_type:
            return mongo_server_rec_read.get('is_updated') and is_indexed_updated and is_indexed_updated[0] and is_indexed_updated[0].get("time") and is_indexed_updated[0].get("time") >= mongo_server_rec_read.get('cache_last_update_time').strftime("%Y-%m-%d %H:%M:%S")

        return len(is_indexed_updated)  and not is_indexed_updated[0].get('time') and mongo_server_rec_read.get('is_ordinary_loading')  and mongo_server_rec_read.get('is_updated')
    
    def _fetch_data_from_db(self, load_pos_data_type, mongo_server_rec, mongo_server_rec_read, reloaded_flag):
        context = self._context
        
        match load_pos_data_type:
            case 'mongo':
                # Through MongoDB
                client = mongo_server_rec.get_client()
                info = client.server_info()
                data = self.env['mongo.server.config'].get_customer_data_from_mongo(fields=fields,client=client)
                if data:
                    return data
            case 'postgres':
                # Through MongoDB
                # ****************decode data************************
                if reloaded_flag is False and mongo_server_rec_read.get('pos_live_sync') == 'reload':
                    self.env['common.cache.notification'].get_common_changes()

                comp_id = int(context.get('allowed_company_ids')[0])
                binary_data_rec = mongo_server_rec.collection_data.filtered(lambda x: x.model_name == 'res.partner' and (x.company_id.id == False or x.company_id.id == comp_id))

                if binary_data_rec:
                    if not request.session['partner_loaded_details']:
                        request.session['partner_loaded_details'] = str(binary_data_rec[0].id)+','
                    json_data = json.loads(base64.decodebytes(binary_data_rec[0].server_data_cache).decode('utf-8'))
                    return list(json_data.values())

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        try:
            reloaded_flag = False # To avoid unnecessay common changes sync
            mongo_server_rec = self.env['common.cache.notification'].get_active_mongo_config
            # Read require data
            mongo_server_rec_read = mongo_server_rec.read(['collection_data', 'load_pos_data_from','cache_last_update_time', 'is_pos_data_synced', 'pos_live_sync', 'is_updated'])
            mongo_server_rec_read=mongo_server_rec_read[0] if mongo_server_rec_read else mongo_server_rec_read
            is_indexed_updated = self._context.get('is_indexed_updated', [])
            sync_from_mongo = self._context.get('sync_from_mongo', False)
            if sync_from_mongo and mongo_server_rec:
                request.session['partner_loaded_details'] = ''
                load_pos_data_type = mongo_server_rec_read.get('load_pos_data_from')

                # Validation Flow
                if self.mongo_server_validation(is_indexed_updated, mongo_server_rec_read):
                    return []
                
                if mongo_server_rec_read.get('cache_last_update_time') and mongo_server_rec_read.get('is_pos_data_synced'):
                    mongo_server_rec.is_ordinary_loading = False
                    if mongo_server_rec_read.get('pos_live_sync') == 'reload' and not mongo_server_rec_read.get('is_ordinary_loading'):
                        # Need to fetch all changes on reload
                        # 1. Reload
                        # 2. Real-time
                        # 3. Through Button
                        self.env['common.cache.notification'].get_common_changes()
                        reloaded_flag = True
                    
                    if self.mongo_server_validation(is_indexed_updated, mongo_server_rec_read, load_pos_data_type):
                        return []

                    return self._fetch_data_from_db(load_pos_data_type, mongo_server_rec, mongo_server_rec_read, reloaded_flag)
                        
                else:
                    mongo_server_rec.is_ordinary_loading = True
                    return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
                
        except Exception as e:
            _logger.info("*****************Exception******************:%r",e)
            return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def write(self, vals):
        res = super(ResPartner,self).write(vals)
        vals_keys = set(vals.keys())
        change_vals = ','.join(vals_keys)
        fields = set(['name','street','city','state_id','country_id','vat','phone','zip','mobile','email','barcode','write_date','property_account_position_id', 'active'])
        common_fields = fields.intersection(vals_keys)
        if len(common_fields):
            for record in self:
                active_configs = self.env['pos.config'].search([('active', '=', True)])
                for config in active_configs:
                    partner_operations = self.env['common.cache.notification'].search([
                        ('model_name','=',"res.partner"),
                        ('config_id', '=', config.id),
                        ('record_id','=',record.id),
                        ('state','in',['error','draft']
                    )],order="id desc")
                    
                    if not (partner_operations and partner_operations[0].operation == 'UPDATE'):
                        self.env['common.cache.notification'].create_pos_based_cache({
                            'record_id': record.id,
                            'operation': 'UPDATE',
                            'model_name': "res.partner",
                            'change_vals': change_vals,
                            'state':'draft'
                        })
        return res

    @api.model_create_multi
    def create(self, vals):
        res = super(ResPartner,self).create(vals)
        for rec in res:
            if rec:
                self.env['common.cache.notification'].create_pos_based_cache({
                    'record_id': rec.id,
                    'operation': 'CREATE',
                    'model_name': "res.partner",
                    'change_vals': 'New Partner Created',
                    'state':'draft'
                })
        return res

    def unlink(self):
        for record in self:
            self.env['common.cache.notification'].create_pos_based_cache({
                'record_id': record.id,
                'operation': 'DELETE',
                'model_name': "res.partner",
                'change_vals': 'Partner Deleted',
                'state':'draft'
            })
        return super(ResPartner,self).unlink()