# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from odoo import models, fields, api, _
import json
import base64
import logging
_logger = logging.getLogger(__name__)

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        _logger.info("**************context*****:%r",self._context)
        try:
            if (self._context.get('sync_from_mongo')):
                context = self._context.copy()
                del context['sync_from_mongo']
                self.with_context(context)
                mongo_server_rec = self.env['mongo.server.config'].sudo().search([('active_record','=',True)],limit=1)
                is_indexed_updated = self._context.get('is_indexed_updated')
                if mongo_server_rec and is_indexed_updated and is_indexed_updated[0] and not is_indexed_updated[0].get('time') and mongo_server_rec.is_ordinary_loading and mongo_server_rec.is_updated :
                    return []
                if mongo_server_rec and mongo_server_rec.cache_last_update_time and mongo_server_rec.is_pos_data_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    load_pos_data_type = mongo_server_rec.load_pos_data_from
                    pricelist_item_ids = []
                    if domain:
                        items = self.env['product.pricelist.item'].search(domain)
                        _logger.info("************items*************:%r",len(items))
                        pricelist_item_ids = items.ids
                    if load_pos_data_type == 'mongo':
                        client = mongo_server_rec.get_client()
                        info = client.server_info()
                        data = self.env['mongo.server.config'].sudo().get_pricelist_items_from_mongo(fields=fields,client=client,pricelist_item_ids=pricelist_item_ids)
                        if data:
                            for record in data:
                                if record.get('date_start'):
                                    record['date_start'] = record.get('date_start').date()
                                if record.get('date_end'):
                                    record['date_end'] = record.get('date_end').date()
                            return data
                    else:
                        # ****************decode data************************
                        binary_data = mongo_server_rec.pos_pricelist_cache
                        data_to_send = []
                        json_data = json.loads(base64.decodebytes(binary_data).decode('utf-8'))
                        for obj in pricelist_item_ids:
                            data_to_send.append(json_data[str(obj)])
                        _logger.info("Data*************:%r",data_to_send)
                        return data_to_send
                else:
                    mongo_server_rec.is_ordinary_loading = True
                    return super(PricelistItem, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

        except Exception as e:
            _logger.info("e*******************Exception***********:%r",e)
            if self._context.get('sync_from_mongo'):
                context = self._context.copy()
                del context['sync_from_mongo']
                self.with_context(context)
            return super(PricelistItem, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super(PricelistItem, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
   
    def write(self, vals):
        vals_keys = vals.keys()     
        change_vals = ','.join(vals_keys)   
        if len(vals_keys):
            for record in self:
                record.create_price_operations(record.id,'UPDATE',change_vals)
        res = super(PricelistItem,self).write(vals)
        return res

    def create_price_operations(self,pl_item_id,operation,change_vals):
        if operation == 'UPDATE':
            for record in self:
                price_operations = self.env['common.cache.notification'].search([('record_id','=', pl_item_id),('state','=','draft')],order="id desc")
                if not (price_operations and price_operations[0].operation == 'UPDATE'):
                    self.env['common.cache.notification'].create_pos_based_cache({
                        'record_id': pl_item_id,
                        'model_name': 'product.pricelist.item',
                        'operation': "UPDATE",
                        'state': "draft",
                        'change_vals':change_vals
                    })
        else:
            for record in self:
                price_operations = self.env['common.cache.notification'].search([('model_name','=',"product.pricelist.item"),('record_id','=', pl_item_id),('state','=','draft')],order="id desc")
                if not (price_operations and price_operations[0].operation == 'DELETE'):
                    self.env['common.cache.notification'].create_pos_based_cache({
                        'record_id': pl_item_id,
                        'model_name': 'product.pricelist.item',
                        'operation': "DELETE",
                        'state': "draft",
                        'change_vals':change_vals
                    })

    @api.model
    def create(self, vals):
        record = super(PricelistItem,self).create(vals)
        for rec in record:
            self.env['common.cache.notification'].create_pos_based_cache({
                'record_id': rec.id,
                'model_name': 'product.pricelist.item',
                'operation': "CREATE",
                'state': "draft",
                'change_vals':'New Pricelist Item Created'
            })
        return record

    def unlink(self):
        for record in self:
            self.env['common.cache.notification'].create_pos_based_cache({
                    'operation': "DELETE",
                    'state': "draft",
                    'model_name': 'product.pricelist.item',
                    'record_id':record.id or False,
                    'change_vals':'Pricelist Item Deleted'
                })

        return super(PricelistItem,self).unlink()