# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    is_department_kiosk = fields.Boolean(
        string='Kiosco de Departamento',
        help='Marcar si este departamento tiene acceso al kiosco de departamento'
    )
    department_kiosk_url = fields.Char(
        string='URL Kiosco de Departamento',
        compute='_compute_department_kiosk_url',
        help='URL única para acceder al kiosco de este departamento'
    )

    def _compute_department_kiosk_url(self):
        """Genera la URL del kiosco oficial con un parámetro de departamento"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for department in self:
            token = department.company_id.attendance_kiosk_key
            if token and department.id:
                # Usamos el parámetro department_id para no romper las rutas relativas de los RPC
                department.department_kiosk_url = f"{base_url}/hr_attendance/{token}?department_id={department.id}"
            else:
                department.department_kiosk_url = False
