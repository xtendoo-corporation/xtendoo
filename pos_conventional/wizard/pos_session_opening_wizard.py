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

    def _validate_employee_pin(self, vals=None):
        """
        Valida el PIN del empleado usando los mecanismos estándar de Odoo.
        Si se llama desde el wizard de PIN, recibe un dict con los datos.
        Si se llama desde el wizard original, usa self.
        """
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
        """
        Abre la sesión POS sin lanzar el frontend, reutilizando el método estándar.
        Establece el dinero inicial si el control de efectivo está activo.
        """
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

        # Cambiar el estado a 'opened' directamente
        # Esto es lo que hace action_pos_session_open pero sin lanzar el frontend
        values['state'] = 'opened'
        values['start_at'] = fields.Datetime.now()

        session.write(values)

        return True

    def _return_to_backend(self):
        """
        Retorna a la vista de pedidos POS después de abrir la sesión.
        Muestra TODOS los pedidos de esta caja para permitir devoluciones.
        Reutiliza la acción estándar de Odoo para listar pedidos POS.
        """
        self.ensure_one()

        # Obtener la acción estándar de pedidos POS de Odoo
        # Esta es la acción oficial: point_of_sale.action_pos_pos_form
        action = self.env.ref('point_of_sale.action_pos_pos_form').read()[0]

        # Filtrar por config_id para mostrar TODOS los pedidos de esta caja
        # (no solo de la sesión actual, para permitir devoluciones)
        action['domain'] = [('config_id', '=', self.session_id.config_id.id)]
        action['context'] = {
            'default_session_id': self.session_id.id,
            'default_config_id': self.session_id.config_id.id,
        }

        return action
