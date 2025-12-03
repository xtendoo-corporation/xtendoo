from odoo import api, models, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override del create para interceptar la apertura automática
        de sesiones en modo no táctil.
        """
        # Si estamos en contexto skip_auto_open, solo crear sin abrir wizard
        if self.env.context.get('skip_auto_open'):
            return super(PosSession, self).create(vals_list)

        # Si no hay skip_auto_open, usar el comportamiento estándar
        # (el wizard se abrirá desde open_ui si es necesario)
        return super(PosSession, self).create(vals_list)

    def action_pos_session_open(self):
        """
        Override del método estándar de apertura de sesión.
        Si pos_non_touch está activo, NO abre nada automáticamente
        (el wizard ya se habrá mostrado desde create).
        De lo contrario, ejecuta el comportamiento estándar.
        """
        # Si estamos en modo de skip (desde create), no hacer nada
        if self.env.context.get('skip_auto_open'):
            return True

        # Filtrar sesiones que usan modo no táctil
        non_touch_sessions = self.filtered(
            lambda s: s.config_id.pos_non_touch and s.state == 'opening_control'
        )

        # Sesiones normales (modo táctil)
        normal_sessions = self - non_touch_sessions

        # Para sesiones normales, ejecutar el comportamiento estándar
        if normal_sessions:
            super(PosSession, normal_sessions).action_pos_session_open()

        # Para sesiones no táctiles llamadas directamente (no desde create),
        # abrir el wizard
        if non_touch_sessions and not self.env.context.get('skip_auto_open'):
            return non_touch_sessions._open_non_touch_wizard()

        return True

    def _open_non_touch_wizard(self):
        """
        Abre el wizard de apertura de sesión para modo no táctil.
        """
        self.ensure_one()

        # Crear el wizard
        wizard = self.env['pos.session.opening.wizard'].create({
            'session_id': self.id,
            'user_id': self.env.user.id,
        })

        # Retornar la acción para mostrar el wizard
        return {
            'name': _('Abrir sesión POS - Modo no táctil'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.session.opening.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

