import math

import pytz

from odoo import api, models
from odoo.exceptions import UserError, ValidationError

GEO_STATUSES = {"ok", "denied", "unavailable", "timeout", "unsupported"}
MAX_ACCURACY_M = 1_000_000


class PortalPunch(models.AbstractModel):
    """Punch logic for the mobile portal. It receives an already authenticated
    employee: it never looks at sessions or tokens. All the real work is
    delegated to the standard ``hr.employee._attendance_action_change``."""

    _name = "hr.attendance.portal.punch"
    _description = "Mobile punch portal logic"

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    @api.model
    def _parse_location(self, company, geo_status, latitude, longitude, accuracy):
        """Validate the browser-supplied location (never trusted as authentic).

        Returns a dict of ``hr.attendance`` geo values, without the ``in_`` /
        ``out_`` prefix. Raises UserError on invalid data or when the company
        policy requires a valid location.
        """
        if geo_status not in GEO_STATUSES:
            raise UserError(self.env._("Invalid location data."))
        required = company.portal_attendance_location_policy == "required"
        no_location = {
            "location_status": "denied" if geo_status == "denied" else "unavailable"
        }

        if geo_status != "ok":
            if required:
                raise UserError(
                    self.env._(
                        "The location is required to punch, but it could not be "
                        "obtained. Allow location access in your browser and try again."
                    )
                )
            return no_location

        try:
            lat, lon, acc = float(latitude), float(longitude), float(accuracy)
        except (TypeError, ValueError):
            raise UserError(self.env._("Invalid location data."))
        if (
            not all(math.isfinite(v) for v in (lat, lon, acc))
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
            or not 0 <= acc <= MAX_ACCURACY_M
            or (lat == 0 and lon == 0)
        ):
            raise UserError(self.env._("Invalid location data."))

        low_accuracy = acc > company.portal_attendance_max_accuracy
        if low_accuracy and required:
            raise UserError(
                self.env._(
                    "The location accuracy (%(acc)d m) is not enough. Move to an "
                    "open area, enable GPS and try again.",
                    acc=round(acc),
                )
            )
        return {
            "latitude": round(lat, 7),
            "longitude": round(lon, 7),
            "accuracy": round(acc, 1),
            "location_status": "low_accuracy" if low_accuracy else "ok",
        }

    # ------------------------------------------------------------------
    # State & punching
    # ------------------------------------------------------------------
    @api.model
    def get_state(self, employee):
        """Read-only summary for the home page."""
        employee = employee.sudo()
        last = self.env["hr.attendance"].sudo().search(
            [("employee_id", "=", employee.id)], order="check_in desc", limit=1
        )
        checked_in = bool(last and not last.check_out)
        moment = last and (last.check_out or last.check_in)
        return {
            "checked_in": checked_in,
            "last_dt": moment,
            "last_label": self.format_dt(employee, moment) if moment else False,
            "last_kind": last and ("in" if checked_in else "out"),
        }

    @api.model
    def format_dt(self, employee, dt, fmt="%d/%m/%Y %H:%M"):
        if not dt:
            return ""
        tz = pytz.timezone(employee.sudo()._get_tz())
        return pytz.utc.localize(dt).astimezone(tz).strftime(fmt)

    @api.model
    def punch(self, employee, action, geo_status, latitude=None, longitude=None,
              accuracy=None, ip_address=None, browser=None):
        """Check in/out ``employee`` (already authenticated by the caller).

        ``action`` is what the employee *saw* on screen ('check_in' or
        'check_out'); if the real state changed meanwhile (double tap, other
        device) nothing is written, so a punch can never flip by mistake.
        """
        if action not in ("check_in", "check_out"):
            raise UserError(self.env._("Invalid action."))
        employee = employee.sudo()
        company = employee.company_id
        geo = self._parse_location(company, geo_status, latitude, longitude, accuracy)
        geo["mode"] = "mobile_portal"
        if company.attendance_device_tracking:
            geo.update(ip_address=ip_address or False, browser=browser or False)

        # Serialise concurrent punches of the same employee.
        self.env.cr.execute(
            "SELECT id FROM hr_employee WHERE id = %s FOR UPDATE", [employee.id]
        )
        employee.invalidate_recordset(["attendance_state"])
        checked_in = employee.attendance_state == "checked_in"
        if (action == "check_out") != checked_in:
            raise UserError(
                self.env._(
                    "Your status has changed in the meantime. Please check the "
                    "screen and try again."
                )
            )
        try:
            with self.env.cr.savepoint():
                attendance = employee._attendance_action_change(geo)
        except ValidationError as exc:
            # Standard hr.attendance constraints (overlaps, duplicates...)
            raise UserError(exc.args[0]) from exc
        return attendance

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    @api.model
    def get_history(self, employee, page=1, page_size=20):
        """Own attendances only: the employee is fixed by the caller."""
        employee = employee.sudo()
        Attendance = self.env["hr.attendance"].sudo()
        domain = [("employee_id", "=", employee.id)]
        total = Attendance.search_count(domain)
        pages = max(math.ceil(total / page_size), 1)
        page = min(max(page, 1), pages)
        rows = []
        for att in Attendance.search(
            domain, order="check_in desc", limit=page_size, offset=(page - 1) * page_size
        ):
            rows.append(
                {
                    "date": self.format_dt(employee, att.check_in, "%d/%m/%Y"),
                    "check_in": self.format_dt(employee, att.check_in, "%H:%M"),
                    "check_out": self.format_dt(employee, att.check_out, "%H:%M"),
                    "open": not att.check_out,
                    "worked": att.worked_hours,
                    "in_status": att.in_location_status,
                    "out_status": att.out_location_status,
                }
            )
        return {"rows": rows, "page": page, "pages": pages, "total": total}
