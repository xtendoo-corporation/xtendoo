# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import http
from odoo.http import request


class MisViewerController(http.Controller):

    @http.route("/xtendoo_mis_report_viewer/get_report_data", type="json", auth="user")
    def get_report_data(self, instance_id, options=None):
        instance = request.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            return {"error": "Instance not found"}

        return instance.compute_for_enterprise_viewer(options)

    @http.route("/xtendoo_mis_report_viewer/get_metadata", type="json", auth="user")
    def get_metadata(self, instance_id):
        instance = request.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            return {"error": "Instance not found"}

        return instance.get_enterprise_viewer_metadata()

    @http.route("/xtendoo_mis_report_viewer/export_report", type="json", auth="user")
    def export_report(self, instance_id, format, options=None):
        instance = request.env["mis.report.instance"].browse(instance_id)
        # Placeholder for export logic
        if format == "pdf":
            return instance.print_pdf()
        elif format == "xlsx":
            return instance.export_xls()
        return {"error": "Unsupported format"}

    @http.route("/xtendoo_mis_report_viewer/drilldown", type="json", auth="user")
    def drilldown(self, instance_id, drilldown_arg):
        instance = request.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            return {"error": "Instance not found"}
        return instance.drilldown(drilldown_arg)
