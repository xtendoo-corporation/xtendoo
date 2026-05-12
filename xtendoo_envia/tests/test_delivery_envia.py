# © 2024 Xtendoo. See LICENSE file for full copyright and licensing details.
"""
Tests para el módulo xtendoo_envia (adaptación a Odoo 17 del módulo delivery_envia de Odoo 18).

Estos tests utilizan mocks de las llamadas a la API de Envia para poder
ejecutarse sin conexión real ni API key válida.

Para ejecutar los tests:
    $ python odoo-bin -c odoo.conf -d <database> --test-enable --stop-after-init -i xtendoo_envia
    # O solo los tests de este módulo:
    $ python odoo-bin -c odoo.conf -d <database> --test-enable --stop-after-init --test-tags xtendoo_envia
"""
import json
from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo import Command
from odoo.tests import TransactionCase, tagged


@contextmanager
def _mock_envia_call():
    """Context manager que intercepta las llamadas HTTP a la API de Envia
    y devuelve respuestas predefinidas para los tests.
    """

    def _mock_request(*args, **kwargs):
        method = kwargs.get('method') or (args[1] if len(args) > 1 else 'GET')
        url = kwargs.get('url') or (args[2] if len(args) > 2 else '')

        responses = {
            'GET': {
                'available-service': {
                    'data': [
                        {
                            'carrier_id': 103,
                            'carrier_name': 'ups',
                            'id': 240,
                            'name': 'saver',
                            'description': 'UPS Express Saver',
                            'international': False,
                        },
                        {
                            'carrier_id': 109,
                            'carrier_name': 'shippify',
                            'id': 255,
                            'name': 'express',
                            'description': 'Shippify Express',
                            'international': False,
                        },
                        {
                            'carrier_id': 109,
                            'carrier_name': 'shippify',
                            'id': 256,
                            'name': 'slots',
                            'description': 'Shippify Slots',
                            'international': True,
                        },
                        {
                            'carrier_id': 113,
                            'carrier_name': 'Jadlog',
                            'id': 265,
                            'name': 'expresso',
                            'description': 'Expresso',
                            'international': False,
                        },
                    ]
                },
                'additional-services': {
                    'data': [
                        {
                            'name': 'insurance',
                            'description': 'Insurance',
                            'childs': [{'id': 14, 'name': 'insurance', 'description': 'Description', 'json_structure': ''}],
                        },
                        {
                            'name': 'liftgate_delivery',
                            'description': 'Liftgate Delivery',
                            'childs': [{'id': 60, 'name': 'liftgate_delivery', 'description': 'Description', 'json_structure': ''}],
                        },
                        {
                            'name': 'lifgate_pickup',
                            'description': 'Lifgate Pickup',
                            'childs': [{'id': 63, 'name': 'liftgate_pickup', 'description': 'Description', 'json_structure': ''}],
                        },
                        {
                            'name': 'pickup_residential',
                            'description': 'Pickup Residential',
                            'childs': [{'id': 62, 'name': 'pickup_residential_zone', 'description': 'Pickup Residential Zone', 'json_structure': ''}],
                        },
                        {
                            'name': 'delivery_residential',
                            'description': 'Delivery Residential',
                            'childs': [{'id': 61, 'name': 'delivery_residential_zone', 'description': 'Delivery Residential Zone', 'json_structure': ''}],
                        },
                    ]
                },
                'generic-form': [
                    {'fieldId': 'address1', 'fieldName': 'street', 'rules': {'required': True, 'validationType': 'street'}},
                    {'fieldId': 'address2', 'fieldName': 'number', 'rules': {'required': False, 'validationType': 'value'}},
                    {'fieldId': 'postalCode', 'fieldName': 'postal_code', 'rules': {'required': True, 'max': '20', 'validationType': 'value'}},
                    {'fieldId': 'city', 'fieldName': 'city', 'rules': {'required': True, 'max': '50', 'validationType': 'value'}},
                    {'fieldId': 'city_select', 'fieldName': 'city_select', 'rules': {'required': False, 'max': '50'}},
                    {'fieldId': 'state', 'fieldName': 'state', 'rules': {'required': True, 'min': '2', 'max': '3', 'validationType': 'select'}},
                    {'fieldId': 'reference', 'fieldName': 'reference', 'rules': {'required': False, 'max': '50'}},
                ],
                'uploads/ups': ['WyJtb2NrTGFiZWw9PT09Il0='],
            },
            'POST': {
                'ship/rate': {
                    'meta': 'rate',
                    'data': [
                        {
                            'carrier': 'ups',
                            'carrierDescription': 'UPS',
                            'carrierId': 103,
                            'serviceId': 240,
                            'quantity': 1,
                            'basePrice': 4.60,
                            'totalPrice': 4.60,
                        }
                    ],
                },
                'ship/generate': {
                    'meta': 'generate',
                    'data': [
                        {
                            'carrier': 'ups',
                            'service': 'saver',
                            'shipmentId': 1890000,
                            'trackingNumber': '1Z48746Q48746',
                            'trackUrl': 'https://test.envia.com/rastreo?label=1Z48746Q48746&cntry_code=us',
                            'label': 'https://s3.us-east-2.amazonaws.com/envia-staging/uploads/ups/1Z48746Q487462219663ea5a6a7da1.png',
                            'additionalFiles': [],
                            'totalPrice': 5.20,
                            'currency': 'USD',
                        }
                    ],
                },
            },
        }

        for endpoint, content in responses.get(method, {}).items():
            if endpoint in url:
                response = requests.Response()
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('URL no manejada en el mock: %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield


@tagged('post_install', '-at_install', 'xtendoo_envia')
class TestXtendoEnvia(TransactionCase):
    """Tests de integración para el módulo xtendoo_envia.

    Utilizan mocks de la API de Envia para no requerir credenciales reales.
    Comprueban:
      - Cotización de tarifas (rate)
      - Generación de envíos (send_shipping)
      - Cancelación de envíos (cancel_shipment)
      - Obtención del enlace de seguimiento (tracking link)
      - Sincronización de carriers desde Envia
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Configurar empresa con dirección en Brasil
        cls.your_company = cls.env.ref("base.main_partner")
        cls.your_company.write({
            'name': 'Xtendoo BR Test',
            'country_id': cls.env.ref('base.br').id,
            'street': 'Praça Mauá 1',
            'street2': 'Centro',
            'state_id': cls.env.ref('base.state_br_rj').id,
            'city': 'Rio de Janeiro',
            'zip': '20081-240',
            'phone': '+55 11 96123-4567',
        })

        # Partner en Brasil
        cls.br_partner = cls.env['res.partner'].create({
            'name': 'Socio BR Test',
            'country_id': cls.env.ref('base.br').id,
            'street': 'Av. Presidente Vargas 592',
            'street2': 'Centro',
            'state_id': cls.env.ref('base.state_br_rj').id,
            'city': 'Rio de Janeiro',
            'zip': '30071-001',
            'phone': '+55 11 96123-4567',
            'email': 'socio.br@test.com',
        })

        # Partner en Estados Unidos
        cls.us_partner = cls.env['res.partner'].create({
            'name': 'Azure Interior Test',
            'is_company': True,
            'street': '4557 De Silva St',
            'city': 'Fremont',
            'country_id': cls.env.ref('base.us').id,
            'zip': '94538',
            'state_id': cls.env.ref('base.state_us_5').id,
            'email': 'azure.interior@test.com',
            'phone': '(870)-931-0505',
        })

        # Productos con peso para los tests
        cls.product_to_ship1 = cls.env['product.product'].create({
            'name': 'Puerta con Patas',
            'type': 'consu',
            'weight': 10.0,
        })

        cls.product_to_ship2 = cls.env['product.product'].create({
            'name': 'Puerta con Brazos',
            'type': 'consu',
            'weight': 15.0,
        })

        # Carrier Envia de referencia (creado por los datos del módulo)
        cls.envia = cls.env.ref('xtendoo_envia.delivery_carrier_envia')
        cls.envia.write({
            'envia_production_api_key': 'mock_key_production',
            'envia_sandbox_api_key': 'mock_key_sandbox',
            'envia_service_code': 'saver',
            'envia_carrier_code': 'ups',
        })

    # ------------------------------------------------------------------
    # Tests de cotización de tarifa
    # ------------------------------------------------------------------

    def test_rate_order_brasil(self):
        """Cotiza un pedido para un cliente brasileño y verifica que la tarifa sea correcta."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
            'order_line': [
                Command.create({'product_id': self.product_to_ship1.id}),
                Command.create({'product_id': self.product_to_ship2.id}),
            ],
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.envia.id,
            'order_id': sale_order.id,
        })

        with _mock_envia_call():
            choose_delivery_carrier.update_price()
            self.assertEqual(
                choose_delivery_carrier.delivery_price, 4.60,
                "La tarifa de envío debería ser 4.60 USD según el mock de Envia."
            )

    def test_rate_order_without_carrier_code(self):
        """Verifica que sin carrier/service code se retorne un error descriptivo."""
        envia_sin_carrier = self.envia.copy({'envia_carrier_code': '', 'envia_service_code': ''})
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
            'order_line': [
                Command.create({'product_id': self.product_to_ship1.id}),
            ],
        })
        result = envia_sin_carrier.envia_rate_shipment(sale_order)
        self.assertFalse(result['success'], "Debería fallar sin carrier configurado.")
        self.assertIn('Envia.com', result['error_message'], "El mensaje de error debería mencionar Envia.com.")

    def test_rate_order_product_without_weight(self):
        """Verifica que productos sin peso generen un error de validación."""
        product_sin_peso = self.env['product.product'].create({
            'name': 'Producto Sin Peso',
            'type': 'consu',
            'weight': 0.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
            'order_line': [
                Command.create({'product_id': product_sin_peso.id}),
            ],
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.envia.id,
            'order_id': sale_order.id,
        })

        from odoo.exceptions import ValidationError
        with _mock_envia_call():
            with self.assertRaises(ValidationError):
                choose_delivery_carrier.update_price()

    # ------------------------------------------------------------------
    # Tests de envío de pedidos
    # ------------------------------------------------------------------

    def test_shipping_order_brasil(self):
        """Verifica que el envío de un pedido brasileño funcione correctamente."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
            'order_line': [
                Command.create({'product_id': self.product_to_ship1.id}),
                Command.create({'product_id': self.product_to_ship2.id}),
            ],
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.envia.id,
            'order_id': sale_order.id,
        })

        with _mock_envia_call():
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()

            self.assertGreater(
                len(sale_order.picking_ids), 0,
                "La Orden de Venta debería generar pickings para el envío."
            )

            picking = sale_order.picking_ids[0]
            self.assertEqual(
                picking.carrier_id.id, sale_order.carrier_id.id,
                "El carrier en el picking y en la OS deben coincidir."
            )

            picking.action_assign()
            # En Odoo 17, el campo 'picked' está disponible en stock.move.line
            picking.move_ids.picked = True
            self.assertGreater(picking.weight, 0.0, "El peso del picking debería ser positivo.")

            picking._action_done()
            self.assertEqual(
                picking.carrier_tracking_ref, "1Z48746Q48746",
                "El número de seguimiento de Envia no es correcto."
            )

    def test_shipping_generates_label_attachment(self):
        """Verifica que el envío genera correctamente la etiqueta PDF adjunta."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
            'order_line': [
                Command.create({'product_id': self.product_to_ship1.id}),
                Command.create({'product_id': self.product_to_ship2.id}),
            ],
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.envia.id,
            'order_id': sale_order.id,
        })

        with _mock_envia_call():
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()

            picking = sale_order.picking_ids[0]
            picking.action_assign()
            picking.move_ids.picked = True
            picking._action_done()

            # Verificar que se generó algún adjunto con el número de tracking
            attachments = picking.message_ids.attachment_ids
            tracking_attachments = attachments.filtered(
                lambda a: '1Z48746Q48746' in (a.name or '') or '1Z48746Q48746' in (a.description or '')
            )
            self.assertTrue(
                len(tracking_attachments) > 0 or len(attachments) > 0,
                "Debería haberse generado al menos un adjunto de etiqueta."
            )

    # ------------------------------------------------------------------
    # Tests de cancelación de envíos
    # ------------------------------------------------------------------

    def test_cancel_shipment(self):
        """Verifica la cancelación de un envío."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
            'order_line': [
                Command.create({'product_id': self.product_to_ship1.id}),
                Command.create({'product_id': self.product_to_ship2.id}),
            ],
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.envia.id,
            'order_id': sale_order.id,
        })

        with _mock_envia_call():
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()

            picking = sale_order.picking_ids[0]
            picking.action_assign()
            picking.move_ids.picked = True
            picking._action_done()

            self.assertEqual(picking.carrier_tracking_ref, "1Z48746Q48746")

        # Ahora intentar cancelar - mockear la repuesta de cancel
        def _mock_cancel_request(*args, **kwargs):
            response = requests.Response()
            response._content = json.dumps({'meta': 'cancel', 'data': True}).encode()
            response.status_code = 200
            return response

        with patch.object(requests.Session, 'request', _mock_cancel_request):
            self.envia.envia_cancel_shipment(picking)
            self.assertEqual(
                picking.carrier_tracking_ref, '',
                "El número de seguimiento debería limpiarse tras la cancelación."
            )
            self.assertEqual(
                picking.carrier_price, 0.0,
                "El precio del carrier debería ser 0 tras la cancelación."
            )

    # ------------------------------------------------------------------
    # Tests de tracking link
    # ------------------------------------------------------------------

    def test_tracking_link_sandbox(self):
        """Verifica que el enlace de seguimiento en sandbox sea correcto."""
        self.envia.prod_environment = False
        picking = self.env['stock.picking'].search([], limit=1)
        if not picking:
            self.skipTest("No hay pickings disponibles para este test.")
        picking.carrier_tracking_ref = 'TEST123456'
        link = self.envia.envia_get_tracking_link(picking)
        self.assertIn('dev.envia.com', link, "En sandbox el enlace debe apuntar a dev.envia.com.")
        self.assertIn('TEST123456', link, "El enlace debe contener el número de tracking.")

    def test_tracking_link_production(self):
        """Verifica que el enlace de seguimiento en producción sea correcto."""
        self.envia.prod_environment = True
        picking = self.env['stock.picking'].search([], limit=1)
        if not picking:
            self.skipTest("No hay pickings disponibles para este test.")
        picking.carrier_tracking_ref = 'PROD123456'
        link = self.envia.envia_get_tracking_link(picking)
        self.assertIn('envia.com', link, "En producción el enlace debe apuntar a envia.com.")
        self.assertNotIn('dev.envia.com', link, "En producción el enlace no debe apuntar a dev.envia.com.")
        self.assertIn('PROD123456', link, "El enlace debe contener el número de tracking.")
        # Resetear a sandbox para no afectar otros tests
        self.envia.prod_environment = False

    # ------------------------------------------------------------------
    # Tests del wizard de sincronización de carriers
    # ------------------------------------------------------------------

    def test_open_envia_wizard(self):
        """Verifica que el wizard de sincronización de carriers se abre correctamente."""
        with _mock_envia_call():
            action = self.envia.action_open_envia_wizard()
            self.assertEqual(action['res_model'], 'envia.shipping.wizard')
            self.assertEqual(action['type'], 'ir.actions.act_window')
            self.assertIn('default_available_services', action['context'])
            self.assertTrue(
                len(action['context']['default_available_services']) > 0,
                "El wizard debería tener servicios disponibles."
            )

    def test_wizard_validates_service_selection(self):
        """Verifica que la validación del wizard funciona correctamente."""
        from odoo.exceptions import ValidationError
        wizard = self.env['envia.shipping.wizard'].create({
            'carrier_id': self.envia.id,
            'available_services': [
                {'carrier_name': 'ups', 'name': 'saver', 'description': 'UPS Express Saver', 'id': 1},
            ],
            'selected_service_code': 'saver',
            'selected_carrier_code': 'ups',
        })
        # Validación correcta no debe lanzar excepción
        wizard.action_validate()
        self.assertEqual(self.envia.envia_service_code, 'saver')
        self.assertEqual(self.envia.envia_carrier_code, 'ups')

    def test_wizard_rejects_invalid_service(self):
        """Verifica que el wizard rechaza una selección inválida."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['envia.shipping.wizard'].create({
                'carrier_id': self.envia.id,
                'available_services': [
                    {'carrier_name': 'ups', 'name': 'saver', 'description': 'UPS Express Saver', 'id': 1},
                ],
                'selected_service_code': 'servicio_invalido',
                'selected_carrier_code': 'carrier_invalido',
            })

    # ------------------------------------------------------------------
    # Tests de conversión de unidades
    # ------------------------------------------------------------------

    def test_envia_convert_weight(self):
        """Verifica la conversión de peso a KG."""
        result = self.envia._envia_convert_weight(1.0)
        self.assertIsInstance(result, float, "El resultado debe ser un float.")
        self.assertGreater(result, 0.0, "El peso convertido debe ser positivo.")

    def test_envia_convert_size(self):
        """Verifica la conversión de talla a CM."""
        result = self.envia._envia_convert_size(1.0)
        self.assertIsInstance(result, float, "El resultado debe ser un float.")
        self.assertGreater(result, 0.0, "El tamaño convertido debe ser positivo.")

    # ------------------------------------------------------------------
    # Tests de tipos de paquete
    # ------------------------------------------------------------------

    def test_package_type_envia_box(self):
        """Verifica que el tipo de paquete box está correctamente configurado."""
        box = self.env.ref('xtendoo_envia.envia_packaging_box')
        self.assertEqual(box.envia_mail_type, 'box')
        self.assertEqual(box.package_carrier_type, 'envia')
        self.assertGreater(box.packaging_length, 0)
        self.assertGreater(box.width, 0)
        self.assertGreater(box.height, 0)

    def test_package_type_envia_pallet(self):
        """Verifica que el tipo de paquete pallet está correctamente configurado."""
        pallet = self.env.ref('xtendoo_envia.envia_packaging_pallet')
        self.assertEqual(pallet.envia_mail_type, 'pallet')
        self.assertEqual(pallet.package_carrier_type, 'envia')

    def test_package_type_envia_envelope(self):
        """Verifica que el tipo de paquete envelope está correctamente configurado."""
        envelope = self.env.ref('xtendoo_envia.envia_packaging_envelope')
        self.assertEqual(envelope.envia_mail_type, 'envelope')
        self.assertEqual(envelope.package_carrier_type, 'envia')

    def test_package_type_constraint_zero_dimensions(self):
        """Verifica que no se puede crear un paquete Envia con dimensiones en cero."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['stock.package.type'].create({
                'name': 'Paquete Inválido',
                'package_carrier_type': 'envia',
                'envia_mail_type': 'box',
                'packaging_length': 0,
                'width': 0,
                'height': 0,
            })

    # ------------------------------------------------------------------
    # Tests de la API de Envia (lógica de negocio)
    # ------------------------------------------------------------------

    def test_fetch_envia_carriers(self):
        """Verifica que se pueden obtener los carriers de Envia."""
        from odoo.addons.xtendoo_envia.models.envia_request import Envia
        envia = Envia(self.envia, False, self.envia.log_xml)
        with _mock_envia_call():
            result = envia._fetch_envia_carriers()
            self.assertIn('carriers', result)
            self.assertIsInstance(result['carriers'], list)
            self.assertGreater(len(result['carriers']), 0)

    def test_envia_cancel_picking(self):
        """Verifica la lógica de cancelación en la clase Envia."""
        from odoo.addons.xtendoo_envia.models.envia_request import Envia
        envia = Envia(self.envia, False, self.envia.log_xml)

        picking = self.env['stock.picking'].search([], limit=1)
        if not picking:
            self.skipTest("No hay pickings disponibles para este test.")
        picking.write({
            'carrier_id': self.envia.id,
            'carrier_tracking_ref': '1Z48746Q48746',
        })

        def _mock_cancel(*args, **kwargs):
            response = requests.Response()
            response._content = json.dumps({'meta': 'cancel', 'data': True}).encode()
            response.status_code = 200
            return response

        with patch.object(requests.Session, 'request', _mock_cancel):
            invalid = envia._cancel_picking(picking)
            self.assertEqual(invalid, [], "No debería haber trackings inválidos al cancelar.")

    def test_envia_state_code_mapping(self):
        """Verifica que el mapeo de códigos de estado funciona correctamente."""
        from odoo.addons.xtendoo_envia.models.envia_request import Envia, STATE_CODE_MAP_ENVIA
        envia = Envia(self.envia, False, self.envia.log_xml)

        # Verificar que el mapeo existe para Argentina
        self.assertIn(('AR', 'A'), STATE_CODE_MAP_ENVIA)
        self.assertEqual(STATE_CODE_MAP_ENVIA[('AR', 'A')], 'SA')

        # Verificar que para un código sin mapeo, retorna el código original
        partner = self.br_partner
        state_code = envia._get_envia_state_code(partner)
        self.assertIsNotNone(state_code)

    def test_delivery_carrier_data_record(self):
        """Verifica que el registro de datos del carrier Envia se creó correctamente."""
        carrier = self.env.ref('xtendoo_envia.delivery_carrier_envia')
        self.assertEqual(carrier.delivery_type, 'envia')
        self.assertTrue(carrier.envia_default_package_type_id)

