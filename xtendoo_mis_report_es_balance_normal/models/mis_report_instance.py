# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from datetime import date


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    @api.model
    def action_open_es_balance_normal(self):
        """
        Creates or finds a MIS Report Instance for the Spanish Balance Normal report
        and opens it with the enterprise viewer.
        """
        report_template = self.env.ref(
            "l10n_es_mis_report.mis_report_es_balance_normal", raise_if_not_found=False
        )
        if not report_template:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Spanish Balance Normal report template not found."),
                    "sticky": False,
                },
            }

        # Parameters
        today = date.today()
        date_from = date(today.year, 1, 1)
        date_to = date(today.year, 12, 31)

        # Check if an instance already exists for this user/company/report/dates or create a temporary one
        # To avoid clutter, we search for one first
        instance = self.search(
            [
                ("report_id", "=", report_template.id),
                ("date_from", "=", date_from),
                ("date_to", "=", date_to),
                ("company_id", "=", self.env.company.id),
                ("temporary", "=", True),
            ],
            limit=1,
        )

        if not instance:
            instance = self.create(
                {
                    "name": _("Spanish Balance Normal %s") % today.year,
                    "report_id": report_template.id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "company_id": self.env.company.id,
                    "target_move": "posted",
                    "temporary": True,
                }
            )
            # Add a default period if necessary (MIS Builder usually needs at least one)
            self.env["mis.report.instance.period"].create(
                {
                    "name": _("Current Year"),
                    "report_instance_id": instance.id,
                    "mode": "fix",
                    "manual_date_from": date_from,
                    "manual_date_to": date_to,
                }
            )

        return instance.action_open_enterprise_viewer()
