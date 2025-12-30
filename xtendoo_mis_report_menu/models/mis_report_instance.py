# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from datetime import date


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _open_report_list(self, template_xml_id, report_name):
        """
        Generic method to open a list view of Spanish reports.
        If no report exists for the current year, creates one automatically.

        :param template_xml_id: XML ID of the report template
        :param report_name: Name prefix for the report
        :return: Action dictionary to open the list view
        """
        report_template = self.env.ref(template_xml_id, raise_if_not_found=False)
        if not report_template:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Report template not found: %s. Please install l10n_es_mis_report module.") % template_xml_id,
                    "sticky": True,
                },
            }

        # Parameters for current year
        today = date.today()
        date_from = date(today.year, 1, 1)
        date_to = date(today.year, 12, 31)

        # Check if a report exists for this year
        current_year_instance = self.search(
            [
                ("report_id", "=", report_template.id),
                ("date_from", "=", date_from),
                ("date_to", "=", date_to),
                ("company_id", "=", self.env.company.id),
                ("temporary", "=", False),
            ],
            limit=1,
        )

        # If no report exists for current year, create it automatically
        if not current_year_instance:
            current_year_instance = self.create(
                {
                    "name": _("%s %s") % (report_name, today.year),
                    "report_id": report_template.id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "company_id": self.env.company.id,
                    "target_move": "posted",
                    "temporary": False,
                }
            )
            # Ensure the instance is persisted
            self.env.cr.flush()

            # Add a default period
            self.env["mis.report.instance.period"].create(
                {
                    "name": _("Current Year"),
                    "report_instance_id": current_year_instance.id,
                    "mode": "fix",
                    "manual_date_from": date_from,
                    "manual_date_to": date_to,
                }
            )
            # Ensure the period is persisted
            self.env.cr.flush()

        # Open list view of all reports filtered by type
        return {
            "type": "ir.actions.act_window",
            "name": _(report_name),
            "res_model": "mis.report.instance",
            "view_mode": "list,form",
            "domain": [
                ("report_id", "=", report_template.id),
                ("temporary", "=", False),
            ],
            "context": {
                "default_report_id": report_template.id,
                "default_target_move": "posted",
            },
            "target": "current",
        }

    @api.model
    def action_open_es_balance_abreviado(self):
        """Opens Balance Abreviado reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_balance_abreviado",
            "Balance Abreviado"
        )

    @api.model
    def action_open_es_balance_normal(self):
        """Opens Balance Normal reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_balance_normal",
            "Balance Completo"
        )

    @api.model
    def action_open_es_balance_pymes(self):
        """Opens Balance PYMES reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_balance_pymes",
            "Balance PYMES"
        )

    @api.model
    def action_open_es_balance_pymes_sfl(self):
        """Opens Balance PYMES SFL reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_balance_pymes_sfl",
            "Balance PYMESFL"
        )

    @api.model
    def action_open_es_pyg_abreviado(self):
        """Opens PyG Abreviado reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_pyg_abreviado",
            "PyG Abreviado"
        )

    @api.model
    def action_open_es_pyg_normal(self):
        """Opens PyG Normal reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_pyg_normal",
            "PyG Completo"
        )

    @api.model
    def action_open_es_pyg_pymes(self):
        """Opens PyG PYMES reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_pyg_pymes",
            "PyG PYMES"
        )

    @api.model
    def action_open_es_pyg_pyme_sfl(self):
        """Opens PyG PYME SFL reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_pyg_pyme_sfl",
            "PyG PYMESFL"
        )

    @api.model
    def action_open_es_eiyg_normal(self):
        """Opens Estado de Ingresos y Gastos Reconocidos reports list"""
        return self._open_report_list(
            "l10n_es_mis_report.mis_report_es_eiyg_normal",
            "Estado de Ingresos y Gastos Reconocidos"
        )

