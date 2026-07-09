from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class XtdHrLeaveRecomputeWizard(models.TransientModel):
    _name = "xtd.hr.leave.recompute.wizard"
    _description = "Wizard to recompute leave durations with a selected calendar"

    xtd_calendar_mode = fields.Selection(
        selection=[
            ("keep", "Usar el horario guardado en cada ausencia"),
            ("employee", "Actualizar al horario actual del empleado"),
            ("manual", "Usar un horario concreto"),
        ],
        string="Modo de horario",
        required=True,
        default="keep",
    )
    xtd_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Horario",
    )
    xtd_leave_ids = fields.Many2many(
        "hr.leave",
        string="Ausencias",
    )

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        active_ids = self.env.context.get("active_ids", [])
        if "xtd_leave_ids" in field_list and active_ids and not values.get("xtd_leave_ids"):
            values["xtd_leave_ids"] = [fields.Command.set(active_ids)]
        return values

    def xtd_action_recompute(self):
        self.ensure_one()
        if self.xtd_calendar_mode == "manual" and not self.xtd_calendar_id:
            raise ValidationError(_("Please select a calendar when using manual mode."))
        leaves = self.xtd_leave_ids
        action = leaves.xtd_action_recompute_duration_with_calendar_mass(
            xtd_calendar_mode=self.xtd_calendar_mode,
            xtd_calendar=self.xtd_calendar_id,
        )
        return action
