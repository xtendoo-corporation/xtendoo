# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestXtendooDecaController(HttpCase):
    """Tests del controlador público /deca/<token>: debe permitir la
    descarga directa del PDF sin autenticación ni interacción manual
    (apartado Tercero.3 y 4 de la Resolución BOE-A-2026-12784)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cargador = cls.env['res.partner'].create({
            'name': 'Cargador HTTP Test', 'vat': 'ES00000001T',
            'street': 'Calle HTTP Test 1', 'city': 'Sevilla', 'zip': '41001'})
        transportista = cls.env['res.partner'].create({
            'name': 'Transportista HTTP Test', 'vat': 'ES00000002T',
            'is_transportista': True})
        customer = cls.env['res.partner'].create({'name': 'Cliente HTTP Test'})
        product = cls.env['product.product'].create({
            'name': 'Producto HTTP DeCA', 'is_storable': True, 'weight': 1.0})
        picking_type_out = cls.env.ref('stock.picking_type_out')
        cls.picking = cls.env['stock.picking'].create({
            'partner_id': customer.id,
            'picking_type_id': picking_type_out.id,
            'location_id': picking_type_out.default_location_src_id.id,
            'location_dest_id': picking_type_out.default_location_dest_id.id,
            'deca_cargador_partner_id': cargador.id,
            'deca_transportista_partner_id': transportista.id,
            'deca_matricula_vehiculo': '0000HTT',
        })
        cls.env['stock.move'].create({
            'name': product.name,
            'picking_id': cls.picking.id,
            'product_id': product.id,
            'product_uom_qty': 3,
            'product_uom': product.uom_id.id,
            'location_id': cls.picking.location_id.id,
            'location_dest_id': cls.picking.location_dest_id.id,
        })
        cls.picking.action_generar_deca()
        cls.doc = cls.picking.deca_document_ids

    def test_download_valid_token_returns_pdf_without_login(self):
        # HttpCase.url_open no inicia sesión: comprueba el acceso público.
        response = self.url_open('/deca/%s' % self.doc.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_download_invalid_token_returns_404(self):
        response = self.url_open('/deca/token-que-no-existe')
        self.assertEqual(response.status_code, 404)

    def test_download_disabled_returns_404(self):
        self.doc.action_disable_download()
        response = self.url_open('/deca/%s' % self.doc.token)
        self.assertEqual(response.status_code, 404)
        # El archivo se conserva (no se borra), solo se deshabilita la descarga.
        self.assertTrue(self.doc.pdf_file)
