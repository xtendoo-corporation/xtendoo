from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PosSessionOpeningWizard(models.TransientModel):
    _name = 'pos.session.opening.wizard'
    _description = 'Wizard para apertura de sesión POS no táctil'

    session_id = fields.Many2one('pos.session', string='Sesión', required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Usuario', required=True, readonly=True,
                              default=lambda self: self.env.user)
    cash_register_balance_start = fields.Monetary(
        string='Dinero inicial',
        currency_field='currency_id',
        help='Cantidad de dinero en efectivo al abrir la caja',
        default=0.0
    )
    currency_id = fields.Many2one('res.currency', related='session_id.currency_id', readonly=True)
    cash_control = fields.Boolean(related='session_id.cash_control', readonly=True)
    opening_notes = fields.Text(string="Nota de apertura")

    def action_validate_and_open(self):

        self.ensure_one()

        # Abrir la sesión usando el método estándar de Odoo
        self._open_session_backend()

        # Retornar a la vista del POS config o sesión
        return self._return_to_backend()

    def action_open_cash_calculator(self):
        self.ensure_one()

        # Crear el wizard de calculadora
        calculator_wizard = self.env["pos.cash.calculator.wizard"].create(
            {
                "opening_wizard_id": self.id,
                "currency_id": self.currency_id.id,
            }
        )

        return {
            "name": _("Calculadora de Efectivo"),
            "type": "ir.actions.act_window",
            "res_model": "pos.cash.calculator.wizard",
            "view_mode": "form",
            "res_id": calculator_wizard.id,
            "target": "new",
            "context": self.env.context,
        }

    def _validate_employee_pin(self, vals=None):

        if vals:
            session_id = vals['session_id']
            user_id = vals['user_id']
            employee_pin = vals['employee_pin']
        else:
            self.ensure_one()
            session_id = self.session_id
            user_id = self.user_id
            employee_pin = getattr(self, 'employee_pin', None)

        # Verificar permisos básicos primero
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise UserError(_(
                'No tiene permisos para abrir una sesión de Punto de Venta.'
            ))

        # Si el módulo pos_hr está instalado y configurado, validar el PIN del empleado
        if session_id.config_id.module_pos_hr and 'hr.employee' in self.env:
            employee = self.env['hr.employee'].search([
                ('user_id', '=', user_id.id),
                ('pin', '=', employee_pin)
            ], limit=1)

            if not employee:
                raise ValidationError(_(
                    'PIN incorrecto. Por favor, verifique su PIN e intente nuevamente.'
                ))

            return employee

        # Si no hay módulo HR o no está configurado, aceptar cualquier PIN no vacío
        # (esto es para compatibilidad con configuraciones básicas)
        if not employee_pin:
            raise ValidationError(_(
                'Debe ingresar un PIN para abrir la sesión.'
            ))

        return None

    def _open_session_backend(self):

        self.ensure_one()
        session = self.session_id

        # Validar que la sesión esté en estado opening_control
        if session.state != 'opening_control':
            raise UserError(_(
                'Esta sesión ya no está en estado de apertura.'
            ))

        # Si hay control de efectivo, establecer el balance inicial
        values = {}
        if session.cash_control:
            values['cash_register_balance_start'] = self.cash_register_balance_start
        
        # Guardar notas de apertura si las hay
        if self.opening_notes:
            values['opening_notes'] = self.opening_notes

        # Cambiar el estado a 'opened' directamente
        # Esto es lo que hace action_pos_session_open pero sin lanzar el frontend
        values['state'] = 'opened'
        values['start_at'] = fields.Datetime.now()

        session.write(values)

        return True

    def _return_to_backend(self):

        self.ensure_one()

        # Obtener todas las sesiones de este config
        config_sessions = self.env['pos.session'].search([
            ('config_id', '=', self.session_id.config_id.id)
        ])

        # Obtener la acción estándar de pedidos POS de Odoo
        action = self.env.ref('point_of_sale.action_pos_pos_form').read()[0]

        # Filtrar por session_id para mostrar solo pedidos de sesiones de esta caja
        action['domain'] = [('session_id', 'in', config_sessions.ids)]

        # IMPORTANTE: NO incluir default_config_id en el contexto
        # porque el config_id es un campo computed con readonly=False y store=True
        # Si se pasa default_config_id, puede sobrescribir el valor calculado
        # y causar que pedidos de otras cajas (táctiles) se creen con config_id incorrecto
        action['context'] = {
            'default_session_id': self.session_id.id,
        }

        return action
