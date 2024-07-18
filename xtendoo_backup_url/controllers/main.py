# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree, html
import odoo
import odoo.modules.registry
from odoo.addons.base.models.ir_qweb import render as qweb_render
from odoo.tools.misc import str2bool, xlsxwriter, file_open, file_path
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request

_logger = logging.getLogger(__name__)

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

db_list = http.db_list

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

        templates = {}

        with file_open("xtendoo_backup_url/static/src/public/database_manager.qweb.html", "r") as fd:
            template = fd.read()
        with file_open("web/static/src/public/database_manager.master_input.qweb.html", "r") as fd:
            templates['master_input'] = fd.read()
        with file_open("web/static/src/public/database_manager.create_form.qweb.html", "r") as fd:
            templates['create_form'] = fd.read()

        def load(template_name, options):
            return (html.fragment_fromstring(templates[template_name]), template_name)

        return qweb_render(html.document_fromstring(template), d, load=load)

    @http.route('/web/database/administration', type='http', auth="none")
    def manager(self, **kw):
        request._cr = None
        return self._render_template()
