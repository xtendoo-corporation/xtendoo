from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosSessionOpeningWizard(models.TransientModel):
    _name = 'pos.session.opening.wizard'
    _description = 'Wizard para apertura de sesión POS no táctil'

    session_id = fields.Many2one('pos.session', string='Sesión', required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Usuario', required=True, readonly=True,
                              default=lambda self: self.env.user)
    cash_register_balance_start = fields.Float(
        string='Caja de apertura',
        digits=(16, 2),
        default=0.0
    )
    opening_notes = fields.Text(
        string='Nota de apertura',
    )
    currency_id = fields.Many2one('res.currency', related='session_id.currency_id', readonly=True)
    cash_control = fields.Boolean(related='session_id.cash_control', readonly=True)
    pending_order_count = fields.Integer(
        string='Pedidos pendientes',
        compute='_compute_pending_order_count'
    )

    @api.depends('session_id')
    def _compute_pending_order_count(self):
        """Calcula el número de pedidos en borrador con líneas para los próximos días."""
        for wizard in self:
            if wizard.session_id and wizard.session_id.config_id:
                # Contar pedidos en borrador con líneas (similar al POS táctil)
                orders = self.env['pos.order'].search([
                    ('config_id', '=', wizard.session_id.config_id.id),
                    ('state', '=', 'draft'),
                ])
                # Filtrar solo los que tienen líneas
                wizard.pending_order_count = len(orders.filtered(lambda o: o.lines))
            else:
                wizard.pending_order_count = 0

    def action_validate_and_open(self):
        """
        Valida el PIN del empleado y abre la sesión sin lanzar el frontend.
        Reutiliza completamente la lógica estándar de Odoo para validación y apertura.
        """
        self.ensure_one()

        # Abrir la sesión usando el método estándar de Odoo
        self._open_session_backend()

        # Retornar a la vista del POS config o sesión
        return self._return_to_backend()

    def action_open_cash_calculator(self):
        """Abre el wizard de calculadora de efectivo para calcular el saldo inicial"""
        self.ensure_one()

        # Crear el wizard de calculadora vinculado a este wizard de apertura
        calculator_wizard = self.env['pos.cash.calculator.wizard'].create({
            'opening_wizard_id': self.id,
        })

        return {
            'name': _('Cash Calculator'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.cash.calculator.wizard',
            'view_mode': 'form',
            'res_id': calculator_wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def _validate_employee_pin(self, vals=None):
        """
        Valida el PIN del empleado usando los mecanismos estándar de Odoo.
        Si se llama desde el wizard de PIN, recibe un dict con los datos.
        Si se llama desde el wizard original, usa self.
        """
        if vals:
            session_id = vals["session_id"]
            user_id = vals["user_id"]
            employee_pin = vals["employee_pin"]
        else:
            self.ensure_one()
            session_id = self.session_id
            user_id = self.user_id
            employee_pin = getattr(self, "employee_pin", None)

        # Verificar permisos básicos primero
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise UserError(
                _("No tiene permisos para abrir una sesión de Punto de Venta.")
            )

        # Si el módulo pos_hr está instalado y configurado, validar el PIN del empleado
        if (
            session_id.config_id.module_pos_hr
            and "hr.employee"
            and session_id.config_id.pos_force_employee_login_after_order in self.env
        ):
            employee = self.env["hr.employee"].search(
                [("user_id", "=", user_id.id), ("pin", "=", employee_pin)], limit=1
            )

            if (
                not employee
                and session_id.config_id.pos_force_employee_login_after_order
            ):
                raise ValidationError(
                    _(
                        "PIN incorrecto. Por favor, verifique su PIN e intente nuevamente."
                    )
                )

            return employee

        # Si no hay módulo HR o no está configurado, aceptar cualquier PIN no vacío
        # (esto es para compatibilidad con configuraciones básicas)
        if not employee_pin:
            raise ValidationError(_("Debe ingresar un PIN para abrir la sesión."))

        return None

    def _open_session_backend(self):
        """
        Abre la sesión POS sin lanzar el frontend, reutilizando el método estándar.
        Establece el dinero inicial si el control de efectivo está activo.
        """
        self.ensure_one()
        session = self.session_id

        # Validar que la sesión esté en estado opening_control
        if session.state != "opening_control":
            raise UserError(_("Esta sesión ya no está en estado de apertura."))

        # Preparar valores para la sesión
        values = {
            'state': 'opened',
            'start_at': fields.Datetime.now(),
        }

        # Si hay control de efectivo, establecer el balance inicial
        if session.cash_control:
            values['cash_register_balance_start'] = self.cash_register_balance_start

        # Guardar notas de apertura si las hay
        if self.opening_notes:
            values['opening_notes'] = self.opening_notes

        session.write(values)

        return True

    def _return_to_backend(self):
        """
        Retorna a la vista de pedidos POS después de abrir la sesión.
        Muestra todos los pedidos de esta caja para permitir devoluciones de sesiones anteriores.
        """
        self.ensure_one()

        # Obtener todas las sesiones de este config
        config_sessions = self.env["pos.session"].search(
            [("config_id", "=", self.session_id.config_id.id)]
        )

        # Obtener la acción estándar de pedidos POS de Odoo
        action = self.env.ref("point_of_sale.action_pos_pos_form").read()[0]

        # Filtrar por session_id para mostrar solo pedidos de sesiones de esta caja
        action["domain"] = [("session_id", "in", config_sessions.ids)]

        # IMPORTANTE: NO incluir default_config_id en el contexto
        # porque el config_id es un campo computed con readonly=False y store=True
        # Si se pasa default_config_id, puede sobrescribir el valor calculado
        # y causar que pedidos de otras cajas (táctiles) se creen con config_id incorrecto
        action["context"] = {
            "default_session_id": self.session_id.id,
        }

        return action
