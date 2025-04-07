# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import http
from odoo.tools.translate import _
from odoo.http import request
from odoo.addons.point_of_sale.controllers.main import PosController
import logging
_logger = logging.getLogger(__name__)

class PosControllerInherit(PosController):
    @http.route(['/cache/notify'], type='json', auth="none")
    def CacheNotifyPos(self, **kwargs):
        try:
            pos_mongo_config = kwargs.get('mongo_cache_last_update_time')
            mongo_conf = request.env['common.cache.notification'].sudo().get_active_mongo_config
            common_changes = request.env['common.cache.notification'].sudo().search([('state', '!=', 'done'), ('config_id', '=', kwargs.get('config_id', False))])
        
            if mongo_conf and not common_changes and mongo_conf.is_updated:
                if (mongo_conf.cache_last_update_time and pos_mongo_config == mongo_conf.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S")) \
                 or not mongo_conf.cache_last_update_time or not pos_mongo_config:
                    return {'is_data_updated': True}
            
            if mongo_conf.pos_live_sync == 'notify':
                return {'is_data_updated': False, 'sync_method': mongo_conf.pos_live_sync}
            elif mongo_conf.pos_live_sync == 'realtime':
                data = request.env['mongo.server.config'].sudo().get_data_on_sync(**kwargs)
                return {'is_data_updated': False, 'data': data, 'sync_method': mongo_conf.pos_live_sync}
            else:
                return {'is_data_updated': False, 'sync_method': mongo_conf.pos_live_sync}
        except Exception as e:
            _logger.info("<<Exception in Cache notify controller>>: %r", e)
            return False