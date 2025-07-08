from odoo import fields, models, api
from odoo.http import request
import datetime
import logging

_logger = logging.getLogger(__name__)

class EmployeePortalSession(models.Model):
    _name = "employee.portal.session"
    _description = "Sesión del Portal de Empleados"

    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    session_token = fields.Char(string="Token de sesión", required=True)
    create_date = fields.Datetime(string="Fecha de inicio", default=fields.Datetime.now)
    expiration_date = fields.Datetime(string="Fecha de expiración", compute="_compute_expiration_date", store=True)
    is_valid = fields.Boolean(string="Válida", compute="_compute_is_valid")

    @api.depends("create_date")
    def _compute_expiration_date(self):
        """Calcula la fecha de expiración de la sesión (8 horas desde la creación)"""
        for session in self:
            if session.create_date:
                session.expiration_date = session.create_date + datetime.timedelta(hours=8)
            else:
                session.expiration_date = False

    @api.depends("expiration_date")
    def _compute_is_valid(self):
        """Determina si la sesión sigue siendo válida"""
        now = fields.Datetime.now()
        for session in self:
            session.is_valid = session.expiration_date and session.expiration_date > now

    def clean_expired_sessions(self):
        """Elimina las sesiones expiradas"""
        expired_sessions = self.search([
            ('is_valid', '=', False),
        ])
        if expired_sessions:
            _logger.info(f"Limpiando {len(expired_sessions)} sesiones expiradas")
            expired_sessions.unlink()

    @api.model
    def validate_session(self, session_token):
        """Valida si una sesión es válida y devuelve el empleado asociado"""
        if not session_token:
            return False

        session = self.search([
            ('session_token', '=', session_token),
            ('is_valid', '=', True)
        ], limit=1)

        if not session or not session.employee_id:
            return False

        return session.employee_id
