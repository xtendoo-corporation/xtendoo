# Tests para xtendoo_purchase_create_invoice_directly
#
# Ejecutar con:
#   docker-compose run --rm odoo -i xtendoo_purchase_create_invoice_directly \
#     --stop-after-init --test-enable \
#     --test-tags xtendoo_purchase_create_invoice_directly \
#     --workers=0 -d testing

from datetime import datetime

from odoo import fields
from odoo.tests.common import TransactionCase


class TestPurchaseCreateInvoiceDirectly(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref('base.res_partner_1')
        # Producto de tipo consumible para que genere pickings
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'purchase_ok': True,
            'list_price': 10.0,
            'standard_price': 5.0,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_draft_order(self, qty=2, price_unit=10.0):
        """Crea un pedido en estado draft."""
        return self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': qty,
                'product_uom_id': self.product.uom_id.id,
                'price_unit': price_unit,
            })],
        })

    def _confirm_order(self, order):
        """Confirma el pedido (draft → purchase)."""
        order.button_confirm()
        return order

    def _validate_pickings(self, order):
        """Valida todos los pickings pendientes del pedido."""
        for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            for move in picking.move_ids:
                if not move.move_line_ids:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'quantity': move.product_uom_qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'picking_id': picking.id,
                        'company_id': move.company_id.id,
                    })
                else:
                    for ml in move.move_line_ids:
                        ml.quantity = move.product_uom_qty
            picking.button_validate()

    # ------------------------------------------------------------------
    # _compute_has_received_lines
    # ------------------------------------------------------------------

    def test_has_received_lines_false_when_no_lines_received(self):
        """has_received_lines es False cuando qty_received == 0 en todas las líneas."""
        order = self._create_draft_order()
        self.assertFalse(order.has_received_lines)

    def test_has_received_lines_true_when_at_least_one_line_received(self):
        """has_received_lines es True cuando al menos una línea tiene qty_received > 0."""
        order = self._create_draft_order()
        self._confirm_order(order)
        self._validate_pickings(order)
        order.invalidate_recordset(['has_received_lines'])
        self.assertTrue(
            any(l.qty_received > 0 for l in order.order_line),
            "Las líneas deben tener qty_received > 0 tras validar el picking",
        )
        self.assertTrue(order.has_received_lines)

    # ------------------------------------------------------------------
    # action_confirm_receive_invoice — desde draft
    # ------------------------------------------------------------------

    def test_action_confirm_receive_invoice_from_draft_confirms_and_invoices(self):
        """Desde draft: confirma el pedido, valida el picking y crea la factura."""
        order = self._create_draft_order()
        self.assertEqual(order.state, 'draft')
        result = order.action_confirm_receive_invoice()
        self.assertTrue(result)
        self.assertNotEqual(order.state, 'draft', "El pedido debe haber sido confirmado")
        invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
        self.assertTrue(invoices, "Debe haberse creado al menos una factura")

    def test_action_confirm_receive_invoice_from_sent_confirms_and_invoices(self):
        """Desde sent: confirma el pedido, valida el picking y crea la factura."""
        order = self._create_draft_order()
        order.write({'state': 'sent'})
        self.assertEqual(order.state, 'sent')
        result = order.action_confirm_receive_invoice()
        self.assertTrue(result)
        self.assertNotEqual(order.state, 'sent', "El pedido debe haber sido confirmado")
        invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
        self.assertTrue(invoices, "Debe haberse creado al menos una factura desde sent")

    def test_action_confirm_receive_invoice_invoice_date_from_date_order(self):
        """La fecha de factura se toma de date_order cuando existe."""
        order = self._create_draft_order()
        order.action_confirm_receive_invoice()
        invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
        for invoice in invoices:
            expected = order.date_order.date() if order.date_order else datetime.today().date()
            self.assertEqual(invoice.invoice_date, expected)

    def test_action_confirm_receive_invoice_invoice_date_fallback_today(self):
        """La fecha de factura usa datetime.today() cuando date_order es False."""
        order = self._create_draft_order()
        order.date_order = False
        order.action_confirm_receive_invoice()
        invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
        today = datetime.today().date()
        for invoice in invoices:
            self.assertEqual(invoice.invoice_date, today)

    # ------------------------------------------------------------------
    # action_confirm_receive_invoice — desde purchase (pedido en firme)
    # ------------------------------------------------------------------

    def test_action_confirm_receive_invoice_from_purchase_skips_confirm(self):
        """Desde purchase: no llama a button_confirm, valida picking y crea factura."""
        order = self._create_draft_order()
        self._confirm_order(order)
        self.assertEqual(order.state, 'purchase')
        result = order.action_confirm_receive_invoice()
        self.assertTrue(result)
        invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
        self.assertTrue(invoices, "Debe haberse creado al menos una factura desde purchase")

    # ------------------------------------------------------------------
    # action_confirm_receive_invoice — picking con move_line_ids existentes
    # ------------------------------------------------------------------

    def test_action_confirm_receive_invoice_with_existing_move_lines(self):
        """Si el picking ya tiene move_line_ids, actualiza quantity sin crearlas de nuevo."""
        order = self._create_draft_order()
        self._confirm_order(order)
        # Crear manualmente move_line_ids para forzar la rama else del modelo
        for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            for move in picking.move_ids:
                if not move.move_line_ids:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'quantity': 1,  # cantidad parcial a propósito
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'picking_id': picking.id,
                        'company_id': move.company_id.id,
                    })
        result = order.action_confirm_receive_invoice()
        self.assertTrue(result)
        invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
        self.assertTrue(invoices)

    # ------------------------------------------------------------------
    # action_confirm_receive_invoice — sin pickings pendientes
    # ------------------------------------------------------------------

    def test_action_confirm_receive_invoice_no_pending_pickings(self):
        """Si no hay pickings pendientes, solo crea la factura sin intentar validar."""
        order = self._create_draft_order()
        self._confirm_order(order)
        self._validate_pickings(order)
        # Todos los pickings ya están done → no hay pendientes
        result = order.action_confirm_receive_invoice()
        self.assertTrue(result)

    # ------------------------------------------------------------------
    # action_create_invoice_draft — sin factura previa
    # ------------------------------------------------------------------

    def test_action_create_invoice_draft_creates_invoice_and_redirects(self):
        """Crea factura borrador, asigna fecha actual y retorna acción de redirección."""
        order = self._create_draft_order()
        self._confirm_order(order)
        self._validate_pickings(order)
        result = order.action_create_invoice_draft()
        invoice = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertTrue(invoice, "Debe existir una factura borrador")
        self.assertEqual(invoice.invoice_date, fields.Date.context_today(order))
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertEqual(result.get('res_model'), 'account.move')
        self.assertEqual(result.get('res_id'), invoice.id)
        self.assertEqual(result.get('view_mode'), 'form')
        self.assertEqual(result.get('target'), 'current')

    # ------------------------------------------------------------------
    # action_create_invoice_draft — factura borrador ya existente
    # ------------------------------------------------------------------

    def test_action_create_invoice_draft_redirects_to_existing_draft(self):
        """Si ya existe factura borrador, redirige a ella sin crear una nueva."""
        order = self._create_draft_order()
        self._confirm_order(order)
        self._validate_pickings(order)
        # Crear primera factura mediante el método estándar
        order.action_create_invoice()
        existing_draft = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertTrue(existing_draft)

        result = order.action_create_invoice_draft()
        drafts = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertEqual(len(drafts), 1, "No debe haber facturas duplicadas")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('res_id'), drafts[0].id)

    # ------------------------------------------------------------------
    # action_create_invoice_draft — sin facturas posibles → retorna True
    # ------------------------------------------------------------------

    def test_action_create_invoice_draft_returns_true_when_no_invoice_created(self):
        """
        Si action_create_invoice no genera ninguna factura borrador y no hay
        ninguna existente, el método retorna True.
        Simulamos esto mockeando action_create_invoice para que no cree nada.
        """
        order = self._create_draft_order()
        self._confirm_order(order)
        self._validate_pickings(order)

        # Parchear action_create_invoice para que no cree facturas
        original = order.__class__.action_create_invoice

        def mock_no_invoice(self_inner):
            return {}

        order.__class__.action_create_invoice = mock_no_invoice
        try:
            result = order.action_create_invoice_draft()
            self.assertTrue(result is True)
        finally:
            order.__class__.action_create_invoice = original

    # ------------------------------------------------------------------
    # Integridad: no duplicar facturas
    # ------------------------------------------------------------------

    def test_no_duplicate_invoices_on_multiple_calls(self):
        """Llamar a action_create_invoice_draft varias veces no crea facturas duplicadas."""
        order = self._create_draft_order()
        self._confirm_order(order)
        self._validate_pickings(order)
        order.action_create_invoice_draft()
        order.action_create_invoice_draft()
        drafts = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        self.assertEqual(len(drafts), 1, "Solo debe haber una factura borrador")
