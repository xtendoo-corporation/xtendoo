# -*- coding: utf-8 -*-
"""Tests para el módulo login_user_detail (Odoo 18).

Cubre:
  - CRUD del modelo login.detail
  - Valor por defecto de date_time
  - Acceso de seguridad (usuarios internos)
  - Firma correcta de _check_credentials (Odoo 18: credential dict, env dict)
  - Creación de login.detail al autenticar
"""
import inspect
from unittest.mock import patch, MagicMock
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestLoginDetailModel(TransactionCase):
    """Tests del modelo login.detail."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = cls.env.ref('base.user_admin')

    # ------------------------------------------------------------------
    # Tests del modelo
    # ------------------------------------------------------------------

    def test_create_login_detail(self):
        """Crear registro login.detail con todos los campos."""
        detail = self.env['login.detail'].sudo().create({
            'name': 'Usuario Test',
            'ip_address': '192.168.1.100',
        })
        self.assertEqual(detail.name, 'Usuario Test')
        self.assertEqual(detail.ip_address, '192.168.1.100')
        self.assertTrue(detail.date_time, "date_time debe tener valor por defecto")

    def test_date_time_default(self):
        """date_time se establece automáticamente al crear el registro."""
        detail = self.env['login.detail'].sudo().create({'name': 'Test Auto Fecha'})
        self.assertIsNotNone(detail.date_time)

    def test_fields_exist(self):
        """El modelo login.detail tiene los campos name, date_time, ip_address."""
        fields = self.env['login.detail'].fields_get()
        self.assertIn('name', fields, "Campo 'name' no encontrado en login.detail")
        self.assertIn('date_time', fields, "Campo 'date_time' no encontrado en login.detail")
        self.assertIn('ip_address', fields, "Campo 'ip_address' no encontrado en login.detail")

    def test_model_registered(self):
        """El modelo login.detail está registrado en ir.model."""
        model = self.env['ir.model'].search([('model', '=', 'login.detail')])
        self.assertEqual(len(model), 1, "login.detail debe existir en ir.model")

    # ------------------------------------------------------------------
    # Tests de seguridad (ACL)
    # ------------------------------------------------------------------

    def test_internal_user_crud(self):
        """Un usuario interno puede crear, leer, escribir y eliminar login.detail."""
        internal = self.env['res.users'].search(
            [('share', '=', False), ('active', '=', True)], limit=1
        )
        self.assertTrue(internal, "Debe haber al menos un usuario interno activo")

        # Create
        detail = self.env['login.detail'].with_user(internal).create({
            'name': 'Test ACL',
            'ip_address': '10.0.0.1',
        })
        self.assertTrue(detail.id, "Fallo al crear login.detail como usuario interno")

        # Read
        record = self.env['login.detail'].with_user(internal).browse(detail.id)
        self.assertEqual(record.name, 'Test ACL')

        # Write
        record.write({'ip_address': '10.0.0.2'})
        self.assertEqual(record.ip_address, '10.0.0.2')

        # Delete
        record.unlink()
        self.assertFalse(
            self.env['login.detail'].browse(detail.id).exists(),
            "El registro no se eliminó correctamente",
        )

    # ------------------------------------------------------------------
    # Tests de firma y comportamiento de _check_credentials (Odoo 18)
    # ------------------------------------------------------------------

    def test_check_credentials_signature_odoo18(self):
        """La firma de _check_credentials es compatible con Odoo 18.

        Odoo 18 cambió la firma de (password, user_agent_env) a (credential, env)
        donde credential es un dict {'type', 'login', 'password'}.
        """
        from odoo.addons.login_user_detail.models.res_users import ResUsers

        sig = inspect.signature(ResUsers._check_credentials)
        params = list(sig.parameters.keys())

        self.assertNotIn(
            'password', params,
            "La firma antigua 'password' no es válida en Odoo 18. Debe usarse 'credential'.",
        )
        self.assertIn(
            'credential', params,
            "Odoo 18 requiere 'credential' (dict) como primer parámetro de _check_credentials",
        )
        self.assertIn(
            'env', params,
            "Odoo 18 requiere 'env' (dict) como segundo parámetro de _check_credentials",
        )
        # No debe tener @api.model (lo que haría que el primer param sea 'self' en @api.model form)
        self.assertNotIn(
            'user_agent_env', params,
            "Nombre antiguo 'user_agent_env' detectado; debe ser 'env'",
        )

    def test_check_credentials_creates_login_detail(self):
        """_check_credentials crea un registro login.detail con IP y nombre de usuario.

        Se mockea la petición HTTP (REMOTE_ADDR) y el super() de la cadena MRO
        para evitar la verificación real de contraseña en el test.
        La estrategia: encontrar en el MRO la clase 'Users' de base/models/res_users.py
        que es donde termina la cadena de super() calls en Odoo 18.
        """
        mock_req = MagicMock()
        mock_req.httprequest.environ = {'REMOTE_ADDR': '172.16.0.50'}

        count_before = self.env['login.detail'].search_count([])
        fake_auth = {
            'uid': self.admin_user.id,
            'auth_method': 'password',
            'mfa': 'default',
        }

        # Patch: (1) request HTTP en el módulo, (2) _check_credentials base de Odoo
        # La clase base 'Users' en base/models/res_users.py es el final de la cadena
        # de super() calls de todos los módulos que sobreescriben _check_credentials.
        res_users_module = 'odoo.addons.login_user_detail.models.res_users'
        base_check_path = 'odoo.addons.base.models.res_users.Users._check_credentials'

        with patch(f'{res_users_module}.request', mock_req):
            with patch(base_check_path, return_value=fake_auth):
                result = self.admin_user._check_credentials(
                    {
                        'login': self.admin_user.login,
                        'password': 'fake_password_for_test',
                        'type': 'password',
                    },
                    {'interactive': False},
                )

        # Verificar retorno
        self.assertEqual(result, fake_auth, "Debe retornar el auth_info del super()")

        # Verificar creación del registro login.detail
        count_after = self.env['login.detail'].search_count([])
        self.assertEqual(
            count_after,
            count_before + 1,
            "Se debe haber creado exactamente 1 registro login.detail",
        )

        record = self.env['login.detail'].search([], order='id desc', limit=1)
        self.assertEqual(record.name, self.admin_user.name,
                         "El nombre en login.detail debe ser el del usuario autenticado")
        self.assertEqual(record.ip_address, '172.16.0.50',
                         "La IP debe ser la del request mockeado")

