from collections import defaultdict, namedtuple

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


XtdDummyAttendance = namedtuple(
    "XtdDummyAttendance",
    "hour_from, hour_to, dayofweek, day_period, week_type",
)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    xtd_calculation_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Horario usado para el cálculo",
        help=(
            "Horario laboral utilizado para calcular los días/horas de esta ausencia. "
            "Si el horario del empleado cambia posteriormente, puede actualizar "
            "este campo y recalcular la duración."
        ),
        copy=False,
    )

    @api.model
    def xtd_get_default_calculation_calendar(self, employee=False, request_date=False):
        employee = employee or self.env["hr.employee"]
        if employee:
            employee = employee[:1]
            if request_date and hasattr(employee, "_get_calendars"):
                calendar = employee._get_calendars(request_date).get(employee.id)
                if calendar:
                    return calendar
            if employee.resource_calendar_id:
                return employee.resource_calendar_id
        company = employee.company_id if employee else self.env.company
        return company.resource_calendar_id

    def xtd_get_effective_calendar(self):
        self.ensure_one()
        return self.xtd_calculation_calendar_id or self.resource_calendar_id

    def xtd_get_duration_values(self, check_leave_type=True):
        self.ensure_one()
        calendar = self.xtd_get_effective_calendar()
        parent_get_durations = getattr(super(HrLeave, self), "_get_durations", None)
        if parent_get_durations:
            return parent_get_durations(
                check_leave_type=check_leave_type,
                resource_calendar=calendar,
            )[self.id]

        parent_get_duration = getattr(super(HrLeave, self), "_get_duration", None)
        if parent_get_duration:
            return parent_get_duration(
                check_leave_type=check_leave_type,
                resource_calendar=calendar,
            )
        return (0, 0)

    def xtd_get_allowed_recompute_states(self):
        return {"draft", "confirm", "validate1", "validate"}

    def xtd_check_recompute_access(self):
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):
            raise AccessError(
                _("Only Time Off administrators can recalculate leave durations.")
            )

    def xtd_check_recompute_states(self):
        invalid_leaves = self.filtered(
            lambda leave: leave.state not in leave.xtd_get_allowed_recompute_states()
        )
        if invalid_leaves:
            raise ValidationError(
                _(
                    "Only leaves in Draft, To Approve, Second Approval or Approved state can be recalculated."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        employee_ids = {
            values["employee_id"]
            for values in vals_list
            if values.get("employee_id")
        }
        employees = self.env["hr.employee"].browse(employee_ids)
        employees_by_id = {employee.id: employee for employee in employees}
        for values in vals_list:
            if "xtd_calculation_calendar_id" in values:
                continue
            employee = employees_by_id.get(values.get("employee_id"))
            calendar = self.xtd_get_default_calculation_calendar(
                employee,
                request_date=values.get("request_date_from"),
            )
            if calendar:
                values["xtd_calculation_calendar_id"] = calendar.id
        return super().create(vals_list)

    @api.onchange("employee_id", "request_date_from", "request_date_to")
    def _onchange_xtd_calculation_calendar_id(self):
        for leave in self:
            previous_employee = leave._origin.employee_id
            previous_calendar = (
                leave._origin.xtd_calculation_calendar_id
                or leave.xtd_get_default_calculation_calendar(
                    previous_employee,
                    request_date=leave._origin.request_date_from,
                )
            )
            new_calendar = leave.xtd_get_default_calculation_calendar(
                leave.employee_id,
                request_date=leave.request_date_from,
            )
            if (
                not leave.xtd_calculation_calendar_id
                or leave.xtd_calculation_calendar_id == previous_calendar
            ):
                leave.xtd_calculation_calendar_id = new_calendar

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        parent_get_durations = getattr(super(), "_get_durations", None)
        if not parent_get_durations:
            return {
                leave.id: super(HrLeave, leave)._get_duration(
                    check_leave_type=check_leave_type,
                    resource_calendar=(
                        resource_calendar or leave.xtd_get_effective_calendar()
                    ),
                )
                for leave in self
            }

        if resource_calendar:
            return parent_get_durations(
                check_leave_type=check_leave_type,
                resource_calendar=resource_calendar,
            )

        grouped_leaves = defaultdict(lambda: self.env["hr.leave"])
        for leave in self:
            calendar = leave.xtd_get_effective_calendar()
            grouped_leaves[calendar.id or 0] |= leave

        durations = {}
        for leaves in grouped_leaves.values():
            calendar = leaves[:1].xtd_get_effective_calendar()
            durations.update(
                super(HrLeave, leaves)._get_durations(
                    check_leave_type=check_leave_type,
                    resource_calendar=calendar,
                )
            )
        return durations

    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        parent_get_duration = getattr(super(), "_get_duration", None)
        calendar = resource_calendar or self.xtd_get_effective_calendar()
        if parent_get_duration:
            return parent_get_duration(
                check_leave_type=check_leave_type,
                resource_calendar=calendar,
            )
        return super()._get_durations(
            check_leave_type=check_leave_type,
            resource_calendar=calendar,
        )[self.id]

    def _get_hour_from_to(self, request_date_from, request_date_to, day_period=None):
        parent_get_hour_from_to = getattr(super(), "_get_hour_from_to", None)
        calendar = self.xtd_get_effective_calendar()
        if not calendar:
            if parent_get_hour_from_to:
                return parent_get_hour_from_to(
                    request_date_from,
                    request_date_to,
                    day_period=day_period,
                )
            return (0, 24)

        hour_from, _ = calendar._get_hours_for_date(request_date_from, day_period)
        _, hour_to = calendar._get_hours_for_date(request_date_to, day_period)
        return (hour_from, hour_to)

    def _get_attendances(self, request_date_from, request_date_to, day_period=None):
        parent_get_attendances = getattr(super(), "_get_attendances", None)
        calendar = self.xtd_get_effective_calendar()
        if not parent_get_attendances:
            return None, None
        if not calendar:
            return super()._get_attendances(
                request_date_from,
                request_date_to,
                day_period=day_period,
            )

        domain = [
            ("calendar_id", "=", calendar.id),
            ("display_type", "=", False),
            ("day_period", "!=", "lunch"),
        ]
        if day_period:
            domain.append(("day_period", "=", day_period))
        attendances = self.env["resource.calendar.attendance"]._read_group(
            domain,
            ["week_type", "dayofweek", "day_period"],
            ["hour_from:min", "hour_to:max"],
        )
        attendances = sorted(
            [
                XtdDummyAttendance(
                    hour_from,
                    hour_to,
                    dayofweek,
                    day_period_value,
                    week_type,
                )
                for week_type, dayofweek, day_period_value, hour_from, hour_to in attendances
            ],
            key=lambda att: (att.dayofweek, att.day_period != "morning"),
        )
        default_value = XtdDummyAttendance(0, 0, 0, "morning", False)

        if calendar.two_weeks_calendar:
            attendance_model = self.env["resource.calendar.attendance"]
            start_week_type = attendance_model.get_week_type(request_date_from)
            attendance_actual_week = [
                att
                for att in attendances
                if att.week_type is False or int(att.week_type) == start_week_type
            ]
            attendance_actual_next_week = [
                att
                for att in attendances
                if att.week_type is False or int(att.week_type) != start_week_type
            ]
            attendance_filtered = [
                att
                for att in attendance_actual_week
                if int(att.dayofweek) >= request_date_from.weekday()
            ]
            attendance_filtered += list(attendance_actual_next_week)
            attendance_filtered += list(attendance_actual_week)

            end_week_type = attendance_model.get_week_type(request_date_to)
            attendance_actual_week = [
                att
                for att in attendances
                if att.week_type is False or int(att.week_type) == end_week_type
            ]
            attendance_actual_next_week = [
                att
                for att in attendances
                if att.week_type is False or int(att.week_type) != end_week_type
            ]
            attendance_filtered_reversed = list(
                reversed(
                    [
                        att
                        for att in attendance_actual_week
                        if int(att.dayofweek) <= request_date_to.weekday()
                    ]
                )
            )
            attendance_filtered_reversed += list(reversed(attendance_actual_next_week))
            attendance_filtered_reversed += list(reversed(attendance_actual_week))
            attendance_from = attendance_filtered[0] if attendance_filtered else default_value
            attendance_to = (
                attendance_filtered_reversed[0]
                if attendance_filtered_reversed
                else default_value
            )
        else:
            attendance_from = next(
                (
                    att
                    for att in attendances
                    if int(att.dayofweek) >= request_date_from.weekday()
                ),
                attendances[0] if attendances else default_value,
            )
            attendance_to = next(
                (
                    att
                    for att in reversed(attendances)
                    if int(att.dayofweek) <= request_date_to.weekday()
                ),
                attendances[-1] if attendances else default_value,
            )
        return attendance_from, attendance_to

    @api.depends("resource_calendar_id.tz", "xtd_calculation_calendar_id.tz")
    def _compute_tz(self):
        for leave in self:
            calendar = leave.xtd_calculation_calendar_id or leave.resource_calendar_id
            leave.tz = (
                calendar.tz
                or self.env.company.resource_calendar_id.tz
                or self.env.user.tz
                or "UTC"
            )

    def xtd_force_duration_recompute(self):
        fnames = [
            fname
            for fname in (
                "request_hour_from",
                "request_hour_to",
                "date_from",
                "date_to",
                "number_of_hours",
                "number_of_days",
                "duration_display",
            )
            if fname in self._fields
            and self._fields[fname].store
            and self._fields[fname].compute
        ]
        for fname in fnames:
            self.env.add_to_compute(self._fields[fname], self)
        self._recompute_recordset(fnames=fnames)
        self.invalidate_recordset(fnames)
        return fnames

    def xtd_write_calculation_calendar(self, calendar=False):
        values = {"xtd_calculation_calendar_id": calendar.id if calendar else False}
        try:
            self.write(values)
            return self
        except (AccessError, UserError):
            if self.state not in {"validate", "validate1"}:
                raise
            # Validated leaves can be locked by standard access rules. We only
            # elevate here to keep the explicit manager-driven recompute flow.
            self.sudo().write(values)
            return self.sudo()

    def xtd_format_duration(self, days, hours):
        self.ensure_one()
        if self.leave_type_request_unit == "hour":
            return _("%(hours).2f hours", hours=hours)
        return _("%(days).2f days", days=days)

    def xtd_action_recompute_duration_with_calendar(
        self,
        xtd_calendar_mode="keep",
        xtd_calendar=False,
        xtd_post_message=False,
    ):
        self.xtd_check_recompute_access()
        self.xtd_check_recompute_states()
        results = []
        for leave in self:
            previous_days = leave.number_of_days
            previous_hours = leave.number_of_hours
            previous_display = leave.duration_display

            if xtd_calendar_mode == "manual":
                target_calendar = xtd_calendar
            elif xtd_calendar_mode == "employee":
                target_calendar = leave.resource_calendar_id or leave.xtd_get_default_calculation_calendar(
                    leave.employee_id,
                    request_date=leave.request_date_from,
                )
            else:
                target_calendar = (
                    leave.xtd_calculation_calendar_id
                    or leave.resource_calendar_id
                    or leave.xtd_get_default_calculation_calendar(
                        leave.employee_id,
                        request_date=leave.request_date_from,
                    )
                )

            target_leave = leave
            if target_calendar != leave.xtd_calculation_calendar_id:
                target_leave = leave.xtd_write_calculation_calendar(target_calendar)
            elif not leave.xtd_calculation_calendar_id and target_calendar:
                target_leave = leave.xtd_write_calculation_calendar(target_calendar)

            target_leave.xtd_force_duration_recompute()
            target_leave._check_validity()
            self.env["hr.leave.allocation"].invalidate_model(
                ["leaves_taken", "max_leaves"]
            )
            leave.invalidate_recordset(
                [
                    fname
                    for fname in (
                        "xtd_calculation_calendar_id",
                        "number_of_days",
                        "number_of_hours",
                        "duration_display",
                    )
                    if fname in self._fields
                ]
            )

            result = {
                "leave_id": leave.id,
                "calendar_id": leave.xtd_calculation_calendar_id.id,
                "calendar_name": leave.xtd_calculation_calendar_id.display_name,
                "previous_days": previous_days,
                "previous_hours": previous_hours,
                "previous_display": previous_display,
                "new_days": leave.number_of_days,
                "new_hours": leave.number_of_hours,
                "new_display": leave.duration_display,
            }
            results.append(result)

            if xtd_post_message:
                leave.message_post(
                    body=_(
                        "Duration recalculated using schedule '%(calendar)s'. "
                        "Previous duration: %(old)s. New duration: %(new)s.",
                        calendar=leave.xtd_calculation_calendar_id.display_name
                        or _("Undefined"),
                        old=previous_display
                        or leave.xtd_format_duration(previous_days, previous_hours),
                        new=leave.duration_display
                        or leave.xtd_format_duration(
                            leave.number_of_days,
                            leave.number_of_hours,
                        ),
                    ),
                    subtype_xmlid="mail.mt_note",
                )
        return results

    def xtd_get_recompute_notification_action(self, recomputed_count):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Recalculation completed"),
                "message": _(
                    "%(count)s leave(s) have been recalculated.",
                    count=recomputed_count,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def xtd_action_recompute_duration_with_calendar_form(self):
        self.ensure_one()
        results = self.xtd_action_recompute_duration_with_calendar(
            xtd_calendar_mode="keep",
            xtd_post_message=True,
        )
        return self.xtd_get_recompute_notification_action(len(results))

    def xtd_action_recompute_duration_with_calendar_mass(
        self,
        xtd_calendar_mode="keep",
        xtd_calendar=False,
    ):
        results = self.with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        ).xtd_action_recompute_duration_with_calendar(
            xtd_calendar_mode=xtd_calendar_mode,
            xtd_calendar=xtd_calendar,
            xtd_post_message=False,
        )
        return self.xtd_get_recompute_notification_action(len(results))

    def xtd_action_open_recompute_wizard(self):
        self.xtd_check_recompute_access()
        action = self.env.ref(
            "xtendoo_hr_leave_calendar_recompute.xtd_hr_leave_recompute_wizard_action"
        ).read()[0]
        action["context"] = {
            "default_xtd_leave_ids": [(6, 0, self.ids)],
            "active_model": "hr.leave",
            "active_ids": self.ids,
        }
        return action
