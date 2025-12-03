from odoo import fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_non_touch = fields.Boolean(
        string='POS no táctil',
        default=False,
        help='Activa un modo de punto de venta optimizado para equipos sin pantalla táctil.'
    )

    def open_ui(self):
        """
        Override del método open_ui para interceptar la apertura
        cuando pos_non_touch está activo.
        """
        self.ensure_one()

        # Si es modo no táctil, abrir wizard en lugar de la UI
        if self.pos_non_touch:
            # Si no hay sesión actual, crear una
            if not self.current_session_id:
                # Verificar antes de crear
                res = self._check_before_creating_new_session()
                if res:
                    return res

                # Crear la sesión con contexto especial para evitar que se abra automáticamente
                session = self.env['pos.session'].with_context(skip_auto_open=True).create({
                    'user_id': self.env.uid,
                    'config_id': self.id
                })
            else:
                session = self.current_session_id

            # Verificar que session sea un recordset, no un dict
            if isinstance(session, dict):
                # Si es un dict, es una acción que debemos retornar
                return session

            # Si la sesión está en opening_control, abrir el wizard
            if session.state == 'opening_control':
                return session._open_non_touch_wizard()

            # Si la sesión ya está abierta, mostrar una notificación
            # y retornar a la vista del POS config
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sesión ya abierta'),
                    'message': _('La sesión ya está abierta en modo no táctil. Puede gestionarla desde el backend.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Para modo táctil normal, usar el comportamiento estándar
        return super(PosConfig, self).open_ui()

