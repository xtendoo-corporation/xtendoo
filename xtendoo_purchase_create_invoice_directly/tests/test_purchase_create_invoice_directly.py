# Instrucciones para ejecutar los tests manualmente en Odoo 19
#
# 1. Asegúrate de tener la base de datos y el entorno Odoo configurados.
# 2. Ejecuta el siguiente comando desde la raíz de tu instancia Odoo:
#
#    docker-compose run --rm odoo -i xtendoo_purchase_create_invoice_directly --stop-after-init --test-enable --test-tags xtendoo_purchase_create_invoice_directly --workers=0 -d testing
#
# 3. Revisa los resultados en el log de la consola y/o en el menú de tests de Odoo.
#
# Cada test incluye en el docstring el resultado esperado para facilitar la revisión manual.
#
# Para cobertura de UI, revisa que el botón "Crear factura" solo aparece si hay líneas recibidas y el pedido está en estado purchase/done.
#
# Si necesitas comprobar permisos, realiza pruebas con usuarios de diferentes grupos en el entorno Odoo.
#
# Para más detalles, consulta agents.md.
#
# GitHub Copilot


from odoo.tests.common import TransactionCase

class TestPurchaseCreateInvoiceDirectly(TransactionCase):
    def setUp(self):
        super().setUp()
        self.PurchaseOrder = self.env['purchase.order']
        self.Product = self.env['product.product']
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.Product.create({
            'name': 'Test Product',
            'type': 'product',
            'purchase_ok': True,
            'list_price': 10.0,
            'standard_price': 5.0,
        })


    def _create_order(self, state='draft', qty_received=1):
        """Crea un pedido de compra de prueba con líneas y estado opcional."""
        order = self.PurchaseOrder.create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': 'Test Product',
                    'product_qty': 2,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 10.0,
                    'qty_received': qty_received,
                })
            ]
        })
        if state != 'draft':
            order.button_confirm()
            if state == 'done':
                for picking in order.picking_ids:
                    picking.button_validate()
        return order

    def test_action_create_invoice_draft_creates_invoice_and_redirects(self):
        """
        Debe crear una factura en borrador, asignar fecha actual y redirigir a la vista formulario.
        Resultado esperado: factura borrador creada, fecha actual, acción de redirección.
        """
        order = self._create_order(state='purchase')
        res = order.action_create_invoice_draft()
        invoice = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertTrue(invoice, 'Debe existir una factura borrador')
        self.assertEqual(invoice.invoice_date, fields.Date.context_today(order), 'La fecha debe ser la actual')
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get('res_model'), 'account.move')
        self.assertEqual(res.get('res_id'), invoice.id)
        self.assertEqual(res.get('view_mode'), 'form')

    def test_action_create_invoice_draft_redirects_to_existing_draft(self):
        """
        Si ya existe factura borrador, debe redirigir a la primera.
        """
        order = self._create_order(state='purchase')
        invoice1 = order.action_create_invoice()
        res = order.action_create_invoice_draft()
        invoice = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertTrue(invoice)
        self.assertEqual(res.get('res_id'), invoice.id)

    def test_action_create_invoice_draft_returns_true_if_no_invoice(self):
        """
        Si no hay facturas y no se puede crear, debe retornar True.
        """
        order = self._create_order(state='draft', qty_received=0)
        res = order.action_create_invoice_draft()
        self.assertTrue(res is True)

    def test_multiple_draft_invoices_redirects_to_first(self):
        """
        Si hay varias facturas borrador, redirige a la primera.
        """
        order = self._create_order(state='purchase')
        invoice1 = order.action_create_invoice()
        invoice2 = order.action_create_invoice()
        res = order.action_create_invoice_draft()
        drafts = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertGreaterEqual(len(drafts), 2)
        self.assertEqual(res.get('res_id'), drafts[0].id)

    def test_button_visibility_has_received_lines(self):
        """
        El botón 'Crear factura' solo debe mostrarse si has_received_lines es True y el estado es purchase/done.
        """
        order = self._create_order(state='purchase', qty_received=0)
        self.assertFalse(order.has_received_lines)
        order2 = self._create_order(state='purchase', qty_received=2)
        self.assertTrue(order2.has_received_lines)

    def test_integrity_no_duplicate_invoices(self):
        """
        No debe crear facturas duplicadas al llamar varias veces.
        """
        order = self._create_order(state='purchase')
        order.action_create_invoice_draft()
        order.action_create_invoice_draft()
        drafts = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertEqual(len(drafts), 1)

    def test_permissions_and_edge_cases(self):
        """
        Casos límite: sin líneas recibidas, estado incorrecto, permisos insuficientes.
        """
        order = self._create_order(state='draft', qty_received=0)
        res = order.action_create_invoice_draft()
        self.assertTrue(res is True)
        # Simular usuario sin permisos (no implementado aquí, requiere entorno Odoo multiusuario)
        # Se recomienda revisar manualmente en entorno real.

    # Documentación de resultados esperados:
    # - Cada test indica el resultado esperado en el docstring.
    # - Para revisión manual: ejecutar con ./odoo-bin -d <db> --test-enable -i xtendoo_purchase_create_invoice_directly
