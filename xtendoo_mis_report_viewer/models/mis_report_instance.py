from odoo import api, fields, models, _
from odoo.tools import date_utils
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import json


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def get_enterprise_viewer_metadata(self):
        """Returns metadata for the Enhanced viewer."""
        self.ensure_one()
        return {
            "name": self.name,
            "report_id": self.report_id.id,
            "company_id": self.company_id.id,
            "multi_company": self.multi_company,
            "company_ids": self.company_ids.ids,
            "currency_id": self.currency_id.id or self.company_id.currency_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "comparison_mode": self.comparison_mode,
        }

    def compute_for_enterprise_viewer(self, options=None):
        """
        Computes the report for the Enhanced viewer based on provided options.
        Uses temporary modification of actual record to avoid NewId issues.
        """
        self.ensure_one()

        if not options:
            options = self._get_default_enterprise_options()

        # Handle predefined date filters
        date_options = options.get("date", {})
        date_filter = date_options.get("filter", "custom")
        # Priority 1: Date Range ID
        if date_range_id := date_options.get("date_range_id"):
            if self.env.get("date.range"):
                dr = self.env["date.range"].browse(date_range_id)
                if dr.exists():
                    date_options["date_from"] = fields.Date.to_string(dr.date_start)
                    date_options["date_to"] = fields.Date.to_string(dr.date_end)
                    date_options["string"] = dr.name

        # Priority 2: Standard Filter (if no date range or custom dates set)
        elif date_filter != "custom":
            date_from, date_to = self._get_dates_from_filter(date_filter)
            if date_from and date_to:
                date_options["date_from"] = fields.Date.to_string(date_from)
                date_options["date_to"] = fields.Date.to_string(date_to)

        # Store original values to restore later
        original_vals = {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "comparison_mode": self.comparison_mode,
        }
        if "date_range_id" in self._fields:
            original_vals["date_range_id"] = (
                self.date_range_id.id if self.date_range_id else False
            )
        original_periods = self.period_ids.ids if self.period_ids else []

        # Handle Journals filter via context
        context = dict(self.env.context)
        if journals := options.get("journals"):
            selected_ids = [
                j["id"]
                for j in journals
                if j.get("selected") and j.get("model") == "account.journal"
            ]
            if selected_ids:
                context["mis_report_journal_ids"] = selected_ids

        try:
            # Temporarily update the record for computation
            update_vals = {
                "date_from": date_options.get("date_from"),
                "date_to": date_options.get("date_to"),
            }

            # Handle Comparison
            comparison_options = options.get("comparison", {})
            comp_filter = comparison_options.get("filter", "no_comparison")
            num_periods = comparison_options.get("number_period", 1)

            if comp_filter != "no_comparison":
                update_vals["comparison_mode"] = True
                # Update record first, then create periods
                self.with_context(context).write(update_vals)

                # Delete existing periods and create new ones
                self.period_ids.unlink()

                # Main period
                self.env["mis.report.instance.period"].create(
                    {
                        "name": date_options.get("string", _("Current Period")),
                        "report_instance_id": self.id,
                        "mode": "fix",
                        "manual_date_from": date_options.get("date_from"),
                        "manual_date_to": date_options.get("date_to"),
                        "sequence": 10,
                    }
                )

                # Comparison periods
                main_from = fields.Date.from_string(date_options.get("date_from"))
                main_to = fields.Date.from_string(date_options.get("date_to"))

                for i in range(1, num_periods + 1):
                    comp_from, comp_to = None, None
                    if comp_filter == "previous_period":
                        delta = (main_to - main_from).days + 1
                        comp_from = main_from - timedelta(days=delta * i)
                        comp_to = main_to - timedelta(days=delta * i)
                    elif comp_filter == "same_last_year":
                        comp_from = main_from - relativedelta(years=i)
                        comp_to = main_to - relativedelta(years=i)

                    if comp_from and comp_to:
                        name_suffix = f" {i}" if num_periods > 1 else ""
                        if comp_filter == "previous_period":
                            period_name = _("Previous Period") + name_suffix
                        else:
                            period_name = _("Same Period Last Year") + name_suffix

                        self.env["mis.report.instance.period"].create(
                            {
                                "name": period_name,
                                "report_instance_id": self.id,
                                "mode": "fix",
                                "manual_date_from": fields.Date.to_string(comp_from),
                                "manual_date_to": fields.Date.to_string(comp_to),
                                "sequence": 10 + i,
                            }
                        )
            else:
                # No comparison - just update dates
                update_vals["comparison_mode"] = False
                self.with_context(context).write(update_vals)

            # Compute the report using the actual record
            report_data = self.with_context(context).compute()

        finally:
            # Restore original values
            self.write(original_vals)
            # Restore original periods if they were deleted
            if comp_filter != "no_comparison" and original_periods:
                self.period_ids.unlink()
                # Cannot restore period_ids easily, just leave as is for temporary instances

        # Transform report_data to a structure suitable for the OWL viewer
        transformed_data = self._transform_for_enterprise_viewer(report_data, options)

        return transformed_data

    def _get_dates_from_filter(self, date_filter):
        today = fields.Date.context_today(self)
        if date_filter == "today":
            return today, today
        if date_filter == "this_month":
            return date_utils.get_month(today)
        if date_filter == "this_quarter":
            return date_utils.get_quarter(today)
        if date_filter == "this_year":
            return date_utils.get_fiscal_year(today)
        if date_filter == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        if date_filter == "last_month":
            last_month = today - date_utils.relativedelta(months=1)
            return date_utils.get_month(last_month)
        if date_filter == "last_quarter":
            last_quarter = today - date_utils.relativedelta(months=3)
            return date_utils.get_quarter(last_quarter)
        if date_filter == "last_year":
            last_year = today - date_utils.relativedelta(years=1)
            return date_utils.get_fiscal_year(last_year)
        return False, False

    def _get_filter_domain(self, source_aml_model_name):
        domain = super()._get_filter_domain(source_aml_model_name)
        if source_aml_model_name == "account.move.line":
            if journal_ids := self.env.context.get("mis_report_journal_ids"):
                domain.append(("journal_id", "in", journal_ids))
        return domain

    def _get_default_enterprise_options(self):
        # Prepare journals
        all_journals = self.env["account.journal"].search(
            [("company_id", "=", self.company_id.id)]
        )
        journals_list = []
        for j in all_journals:
            journals_list.append(
                {
                    "id": j.id,
                    "name": j.name,
                    "model": "account.journal",
                    "selected": False,
                }
            )

        # Prepare Date Ranges
        date_ranges = []
        if self.env.get("date.range"):
            ranges = self.env["date.range"].search([], order="date_start desc")
            for r in ranges:
                date_ranges.append(
                    {
                        "id": r.id,
                        "name": r.name,
                        "date_start": fields.Date.to_string(r.date_start),
                        "date_end": fields.Date.to_string(r.date_end),
                        "type_id": r.type_id.id,
                        "type_name": r.type_id.name,
                    }
                )

        return {
            "date": {
                "date_from": (
                    fields.Date.to_string(self.date_from) if self.date_from else False
                ),
                "date_to": (
                    fields.Date.to_string(self.date_to) if self.date_to else False
                ),
                "filter": "custom" if self.date_from else "this_year",
                "string": _("Current Period"),
                "date_range_id": (
                    self.date_range_id.id
                    if hasattr(self, "date_range_id") and self.date_range_id
                    else False
                ),
            },
            "date_ranges": date_ranges,
            "comparison": {
                "filter": "no_comparison",
                "number_period": 1,
            },
            "journals": journals_list,
            "hide_zero_lines": False,
            "company_ids": self.env.companies.ids,
            "unfolded_lines": [],
            "unfold_all": False,
        }

    def _transform_for_enterprise_viewer(self, report_data, options):
        """
        Transform MIS Builder report data (header, body) to Enhanced format.
        """
        # report_data['header'] is usually [{"cols": [...]}, {"cols": [...]}] in MIS Builder
        transformed_headers = []
        for row in report_data.get("header", []):
            transformed_row = []
            for col in row.get("cols", []):
                transformed_row.append(
                    {
                        "name": col.get("label", ""),
                        "colspan": col.get("colspan", 1),
                        "description": col.get("description", ""),
                    }
                )
            transformed_headers.append(transformed_row)

        hide_zero = options.get("hide_zero_lines", False)
        lines = []
        for i, row in enumerate(report_data.get("body", [])):
            columns = []
            all_zero = True
            for cell in row.get("cells", []):
                val = cell.get("val", 0)
                if val and val != 0:
                    all_zero = False

                columns.append(
                    {
                        "name": cell.get("val_r", ""),  # Use rendered value for display
                        "no_format": val,
                        "class": cell.get("style", ""),
                        "drilldown": cell.get("drilldown_arg"),
                    }
                )

            if hide_zero and all_zero:
                continue

            line = {
                "id": f"line_{i}",
                "name": row.get("label", ""),
                "level": row.get("level", 0),
                "class": "; ".join(
                    [
                        s.strip()
                        for s in row.get("style", "").split(";")
                        if "background-color" not in s
                    ]
                ),
                "unfoldable": True,
                "unfolded": row.get("id") in options.get("unfolded_lines", [])
                or options.get("unfold_all"),
                "columns": columns,
            }
            lines.append(line)

        return {
            "header": transformed_headers,
            "lines": lines,
            "options": options,
        }

    def action_open_enterprise_viewer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_mis_report_viewer",
            "name": self.name,
            "context": {
                "active_id": self.id,
                "active_model": "mis.report.instance",
            },
            "params": {
                "report_instance_id": self.id,
            },
        }
