# -*- coding: utf-8 -*-

import jinja2
import json
import logging
import os
# import sys
import odoo
import odoo.modules.registry
from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, Response

_logger = logging.getLogger(__name__)

# if hasattr(sys, 'frozen'):
#     # When running on compiled windows binary, we don't have access to package loader.
#     path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
#     loader = jinja2.FileSystemLoader(path)
# else:
#     loader = jinja2.PackageLoader('odoo.addons.web', "views")
#
# env = jinja2.Environment(loader=loader, autoescape=True)
# env.filters["json"] = json.dumps

path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
loader = jinja2.FileSystemLoader(path)
env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

db_monodb = http.db_monodb


class Database(http.Controller):

    def _render_template(self, **d):
        d.setdefault('manage',True)
        d['insecure'] = odoo.tools.config.verify_admin_password('admin')
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        d['pattern'] = DBNAME_PATTERN
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = odoo.service.db.list_db_incompatible(d['databases'])
        except odoo.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]
        return env.get_template("database_manager.html").render(d)

    @http.route('/web/database/administration', type='http', auth="none")
    def manager(self, **kw):
        print("*" * 50)
        request._cr = None
        return self._render_template()
