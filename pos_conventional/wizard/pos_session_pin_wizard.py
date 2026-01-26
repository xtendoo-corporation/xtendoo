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
        if self.env.context.get("switch_user_after_sale"):
            # Si estamos en modo "cambio de usuario tras venta"
            employee = self.env["pos.session.opening.wizard"]._validate_employee_pin(
                {
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "employee_pin": self.employee_pin,
                }
            )

            if employee and employee.user_id:
                # Cambiar el usuario de la sesión
                self.session_id.sudo().write({"user_id": employee.user_id.id})

                # Redirigir a la lista de pedidos POS usando la acción estándar para corregir breadcrumbs
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "point_of_sale.action_pos_pos_form"
                )
                action["view_mode"] = "list,form"
                action["views"] = [(False, "list"), (False, "form")]
                action["target"] = (
                    "main"  # Forzar limpieza de breadcrumbs si es posible, o normal
                )
                action["context"] = {
                    "default_session_id": self.session_id.id,
                    "default_user_id": employee.user_id.id,
                }
                return action
            elif not employee and not self.session_id.config_id.module_pos_hr:
                # Si no hay módulo HR, asumimos que el usuario actual es válido o no cambia
                # Si no hay módulo HR, asumimos que el usuario actual es válido o no cambia
                # Simplemente abrimos la lista de pedidos
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "point_of_sale.action_pos_pos_form"
                )
                action["view_mode"] = "list,form"
                action["views"] = [(False, "list"), (False, "form")]
                action["target"] = "main"
                action["context"] = {
                    "default_session_id": self.session_id.id,
                }
                return action

        # Validar el PIN usando la lógica del wizard original (Flujo de apertura normal)
        self.env["pos.session.opening.wizard"]._validate_employee_pin(
            {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "employee_pin": self.employee_pin,
            }
        )
        # Al validar, abrir el segundo wizard
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.session.opening.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.session_id.id,
                "default_user_id": self.user_id.id,
            },
        }
