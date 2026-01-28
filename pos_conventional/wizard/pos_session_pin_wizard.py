from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosSessionPinWizard(models.TransientModel):
    _name = "pos.session.pin.wizard"
    _description = "Wizard para validar PIN de apertura POS"

    session_id = fields.Many2one("pos.session", required=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", required=True, readonly=True, default=lambda self: self.env.user
    )
    employee_pin = fields.Char(string="PIN del empleado")

    def action_validate_pin(self):
        self.ensure_one()

        # Lógica común: Buscar empleado por PIN
        employee = False
        if self.session_id.config_id.module_pos_hr and "hr.employee" in self.env:
            employee = self.env["hr.employee"].search(
                [
                    ("pin", "=", self.employee_pin),
                    "|",
                    ("company_id", "=", self.session_id.company_id.id),
                    ("company_id", "=", False),
                ],
                limit=1,
            )

            if not employee:
                raise ValidationError(
                    _(
                        "PIN incorrecto. Por favor, verifique su PIN e intente nuevamente."
                    )
                )

        # Si encontramos un usuario vinculado, actualizamos la sesión
        # Esto aplica tanto para "switch_user_after_sale" como para apertura normal
        if employee and employee.user_id:
            self.session_id.sudo().write({"user_id": employee.user_id.id})

        # --- FLOW 1: Cambio de usuario tras venta ---
        if self.env.context.get("switch_user_after_sale"):
            if employee and employee.user_id:
                # Retornar acción cliente para limpiar breadcrumbs via JS
                return {
                    "type": "ir.actions.client",
                    "tag": "pos_conventional_new_order",
                    "params": {
                        "default_session_id": self.session_id.id,
                        "default_user_id": employee.user_id.id,
                    },
                }
            elif not employee and not self.session_id.config_id.module_pos_hr:
                # Retornar acción cliente
                return {
                    "type": "ir.actions.client",
                    "tag": "pos_conventional_new_order",
                    "params": {
                        "default_session_id": self.session_id.id,
                    },
                }

        target_user_id = (
            employee.user_id.id if (employee and employee.user_id) else self.user_id.id
        )

        self.env["pos.session.opening.wizard"]._validate_employee_pin(
            {
                "session_id": self.session_id,
                "user_id": self.env["res.users"].browse(target_user_id),
                "employee_pin": self.employee_pin,
            }
        )

        # Al validar, abrir el segundo wizard de control de efectivo
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.session.opening.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.session_id.id,
                "default_user_id": target_user_id,
            },
        }
