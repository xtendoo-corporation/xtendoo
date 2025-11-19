# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged("post_install", "-at_install")
class TestPosOrderBackend(TransactionCase):
    """Tests para el módulo xtendoo_pos_order"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear un punto de venta de prueba
        cls.pos_config_backend = cls.env["pos.config"].create({
            "name": "Test POS Backend",
            "interface_type": "backend",
        })

        cls.pos_config_frontend = cls.env["pos.config"].create({
            "name": "Test POS Frontend",
            "interface_type": "frontend",
        })

        # Crear un producto de prueba
        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "type": "product",
            "list_price": 100.0,
            "available_in_pos": True,
        })

        # Crear un cliente de prueba
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
        })

        # Crear sesiones abiertas
        cls.session_backend = cls.env["pos.session"].create({
            "config_id": cls.pos_config_backend.id,
        })
        cls.session_backend.action_pos_session_open()

        cls.session_frontend = cls.env["pos.session"].create({
            "config_id": cls.pos_config_frontend.id,
        })
        cls.session_frontend.action_pos_session_open()

    def test_01_create_order_backend_mode_success(self):
        """
        Test: Crear orden POS cuando el config está en modo backend.
        Resultado esperado: La orden se crea correctamente.
        """
        order = self.env["pos.order"].create({
            "config_id": self.pos_config_backend.id,
            "session_id": self.session_backend.id,
            "partner_id": self.partner.id,
        })

        self.assertTrue(order, "La orden debería crearse en modo backend")
        self.assertEqual(order.config_id.interface_type, "backend")

    def test_02_create_order_frontend_mode_fail(self):
        """
        Test: Intentar crear orden POS manualmente cuando el config está en modo frontend.
        Resultado esperado: Debe lanzar un UserError.
        """
        with self.assertRaises(UserError) as context:
            self.env["pos.order"].create({
                "config_id": self.pos_config_frontend.id,
                "session_id": self.session_frontend.id,
                "partner_id": self.partner.id,
            })

        self.assertIn("Backend Orders Interface", str(context.exception))

    def test_03_create_order_from_ui_frontend_success(self):
        """
        Test: Crear orden desde el frontend JS (simulado con contexto).
        Resultado esperado: La orden se crea aunque esté en modo frontend.
        """
        order = self.env["pos.order"].with_context(from_pos_ui=True).create({
            "config_id": self.pos_config_frontend.id,
            "session_id": self.session_frontend.id,
            "partner_id": self.partner.id,
        })

        self.assertTrue(order, "La orden desde UI debe crearse siempre")

    def test_04_create_order_with_lines_backend(self):
        """
        Test: Crear orden con líneas de productos en modo backend.
        Resultado esperado: La orden se crea con líneas y totales correctos.
        """
        order = self.env["pos.order"].create({
            "config_id": self.pos_config_backend.id,
            "session_id": self.session_backend.id,
            "partner_id": self.partner.id,
            "lines": [(0, 0, {
                "product_id": self.product.id,
                "qty": 2,
                "price_unit": 100.0,
                "discount": 0.0,
            })],
        })

        self.assertEqual(len(order.lines), 1, "Debe haber una línea")
        self.assertEqual(order.lines[0].qty, 2, "Cantidad debe ser 2")
        self.assertGreater(order.amount_total, 0, "El total debe ser mayor a 0")

    def test_05_open_ui_backend_mode(self):
        """
        Test: Abrir el POS en modo backend.
        Resultado esperado: Debe devolver una acción hacia pos.order.
        """
        action = self.pos_config_backend.open_ui()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "pos.order")
        self.assertIn(("config_id", "=", self.pos_config_backend.id), action["domain"])

    def test_06_open_ui_frontend_mode(self):
        """
        Test: Abrir el POS en modo frontend.
        Resultado esperado: Debe devolver una acción hacia el cliente JS del POS.
        """
        action = self.pos_config_frontend.open_ui()

        # En modo frontend, devuelve la acción estándar del POS
        # que suele ser un ir.actions.client
        self.assertIsNotNone(action)

    def test_07_create_order_without_session_fail(self):
        """
        Test: Intentar crear orden sin sesión abierta.
        Resultado esperado: Debe lanzar un UserError o asignar sesión automáticamente.
        """
        # Cerrar la sesión
        self.session_backend.action_pos_session_closing_control()

        with self.assertRaises(UserError) as context:
            self.env["pos.order"].create({
                "config_id": self.pos_config_backend.id,
                "partner_id": self.partner.id,
            })

        self.assertIn("sesión", str(context.exception).lower())

    def test_08_auto_assign_session(self):
        """
        Test: Crear orden sin especificar session_id pero con sesión abierta.
        Resultado esperado: Debe asignar automáticamente la sesión abierta.
        """
        # Reabrir sesión
        new_session = self.env["pos.session"].create({
            "config_id": self.pos_config_backend.id,
        })
        new_session.action_pos_session_open()

        order = self.env["pos.order"].create({
            "config_id": self.pos_config_backend.id,
            "partner_id": self.partner.id,
        })

        self.assertEqual(order.session_id, new_session)

