# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo.exceptions import AccessError, UserError
from odoo.fields import Datetime
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestXtendooDecaDocument(TransactionCase):
    """Tests del modelo xtendoo.deca.document y de la generación del DeCA
    desde el albarán de salida (stock.picking), conforme a la Resolución de
    5 de junio de 2026 (BOE-A-2026-12784) y al art. 6 de la Orden
    FOM/2861/2012."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cargador = cls.env['res.partner'].create({
            'name': 'Cargador Contractual Test',
            'vat': 'ES00000000T',
        })
        cls.transportista = cls.env['res.partner'].create({
            'name': 'Transportista Efectivo Test',
            'vat': 'ES11111111H',
        })
        cls.customer = cls.env['res.partner'].create({'name': 'Cliente destino Test'})
        cls.product = cls.env['product.product'].create({
            'name': 'Producto de prueba DeCA',
            'is_storable': True,
            'weight': 2.5,
        })
        cls.picking_type_out = cls.env.ref('stock.picking_type_out')

    def _create_picking(self, qty=10.0, **picking_vals):
        vals = {
            'partner_id': self.customer.id,
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.picking_type_out.default_location_src_id.id,
            'location_dest_id': self.picking_type_out.default_location_dest_id.id,
            'deca_cargador_partner_id': self.cargador.id,
            'deca_transportista_partner_id': self.transportista.id,
            'deca_matricula_vehiculo': '1234ABC',
        }
        vals.update(picking_vals)
        picking = self.env['stock.picking'].create(vals)
        self.env['stock.move'].create({
            'name': self.product.name,
            'picking_id': picking.id,
            'product_id': self.product.id,
            'product_uom_qty': qty,
            'product_uom': self.product.uom_id.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        })
        return picking

    def setUp(self):
        super().setUp()
        self.picking = self._create_picking()

    # -- Generación del DeCA desde el albarán --------------------------

    def test_action_generar_deca_creates_document(self):
        action = self.picking.action_generar_deca()
        self.assertEqual(self.picking.deca_document_count, 1)
        doc = self.picking.deca_document_ids
        self.assertEqual(doc.state, 'generated')
        self.assertEqual(doc.cargador_nif, 'ES00000000T')
        self.assertEqual(doc.transportista_nif, 'ES11111111H')
        # 10 unidades x 2.5 kg/ud
        self.assertAlmostEqual(doc.mercancia_peso, 25.0)
        self.assertTrue(doc.pdf_file, 'El PDF del DeCA debe generarse')
        self.assertTrue(doc.token)
        self.assertTrue(doc.qr_url and doc.qr_url.startswith('https://'),
                         'La URL del DeCA debe ser siempre HTTPS (apartado Tercero.1)')
        self.assertIn(doc.token, doc.qr_url)
        self.assertEqual(action['res_model'], 'xtendoo.deca.document')
        self.assertEqual(action['res_id'], doc.id)

    def test_action_generar_deca_requires_transportista(self):
        self.picking.deca_transportista_partner_id = False
        with self.assertRaises(UserError):
            self.picking.action_generar_deca()

    def test_action_generar_deca_requires_cargador(self):
        self.picking.deca_cargador_partner_id = False
        with self.assertRaises(UserError):
            self.picking.action_generar_deca()

    def test_two_pickings_get_different_tokens(self):
        picking2 = self._create_picking(qty=3.0)
        self.picking.action_generar_deca()
        picking2.action_generar_deca()
        token1 = self.picking.deca_document_ids.token
        token2 = picking2.deca_document_ids.token
        self.assertNotEqual(token1, token2)

    # -- Ciclo de vida del documento ------------------------------------

    def test_action_generate_twice_raises(self):
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        with self.assertRaises(UserError):
            doc.action_generate()

    def test_regenerate_keeps_traceability(self):
        """Apartado Quinto.2: al generar un nuevo PDF con nueva URL/QR debe
        conservarse el documento (y el PDF) anterior."""
        self.picking.action_generar_deca()
        original = self.picking.deca_document_ids
        original_token = original.token
        original_pdf = original.pdf_file
        result = original.action_regenerate()
        new_doc = self.env['xtendoo.deca.document'].browse(result['res_id'])

        self.assertEqual(original.state, 'superseded')
        self.assertEqual(new_doc.state, 'generated')
        self.assertEqual(new_doc.previous_document_id, original)
        self.assertNotEqual(new_doc.token, original_token)
        self.assertNotEqual(new_doc.qr_url, original.qr_url)
        self.assertEqual(original.pdf_file, original_pdf,
                          'El PDF original no debe alterarse al regenerar')
        self.assertTrue(new_doc.pdf_file)

    def test_disable_download(self):
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        self.assertTrue(doc.download_enabled)
        doc.action_disable_download()
        self.assertFalse(doc.download_enabled)

    # -- Caducidad automática de la descarga (apartado Tercero.5) ------

    def test_cron_disables_after_seven_days(self):
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        doc.fecha_servicio = Datetime.now() - timedelta(days=10)
        self.env['xtendoo.deca.document']._cron_disable_expired_downloads()
        self.assertFalse(doc.download_enabled)

    def test_cron_keeps_recent_service_enabled(self):
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        doc.fecha_servicio = Datetime.now() - timedelta(days=2)
        self.env['xtendoo.deca.document']._cron_disable_expired_downloads()
        self.assertTrue(doc.download_enabled)

    # -- URL pública / QR -----------------------------------------------

    def test_public_url_uses_configured_protocol(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'http://odoo-interno.local:8069')
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        self.assertTrue(doc.qr_url.startswith('http://odoo-interno.local:8069/deca/'))

    def test_get_barcode_src_format(self):
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        src = doc.get_barcode_src()
        self.assertIn('type=QR', src)
        self.assertIn('value=', src)

    # -- Seguridad --------------------------------------------------------

    def test_stock_user_cannot_unlink_deca_document(self):
        stock_user_group = self.env.ref('stock.group_stock_user')
        test_user = self.env['res.users'].create({
            'name': 'Usuario Stock Test',
            'login': 'deca_stock_user_test',
            'groups_id': [(6, 0, [stock_user_group.id])],
        })
        self.picking.action_generar_deca()
        doc = self.picking.deca_document_ids
        with self.assertRaises(AccessError):
            doc.with_user(test_user).unlink()
