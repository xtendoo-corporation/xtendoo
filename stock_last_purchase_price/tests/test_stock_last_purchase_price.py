# -*- coding: utf-8 -*-
"""Tests para el módulo stock_last_purchase_price (Odoo 18).

Cubre:
  - El método 'last' aparece en la selección property_cost_method
  - product_price_update_before_done actualiza standard_price con el precio
    de la última compra (corrige bug Odoo 18: _get_price_unit() devuelve dict)
  - Los productos con otro cost_method no se ven afectados por el override
"""
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestStockLastPurchasePrice(TransactionCase):
    """Tests del módulo stock_last_purchase_price."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Categoría con método de coste 'last' y valoración manual
        # (manual_periodic no requiere configuración de cuentas contables)
        cls.categ_last = cls.env['product.category'].create({
            'name': 'Categoría Last Purchase Price',
            'property_cost_method': 'last',
            'property_valuation': 'manual_periodic',
        })

        # Producto almacenable con la categoría creada
        # Odoo 18: type='consu' + is_storable=True reemplaza el antiguo type='product'
        cls.product_last = cls.env['product.product'].create({
            'name': 'Producto Last Price',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.categ_last.id,
            'standard_price': 10.0,      # Precio inicial
        })

        # Categoría con método de coste estándar (para test de no-afectación)
        cls.categ_std = cls.env['product.category'].create({
            'name': 'Categoría Standard Cost',
            'property_cost_method': 'standard',
            'property_valuation': 'manual_periodic',
        })
        cls.product_std = cls.env['product.product'].create({
            'name': 'Producto Standard Cost',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.categ_std.id,
            'standard_price': 20.0,
        })

        # Localizaciones (siempre disponibles en base/stock)
        cls.loc_supplier = cls.env.ref('stock.stock_location_suppliers')
        cls.loc_stock = cls.env.ref('stock.stock_location_stock')

    # ------------------------------------------------------------------
    # Tests de la selección de coste
    # ------------------------------------------------------------------

    def test_last_cost_method_in_selection(self):
        """El método 'last' debe estar disponible en property_cost_method."""
        fields = self.env['product.category'].fields_get(['property_cost_method'])
        selection_keys = [k for k, _ in fields['property_cost_method']['selection']]
        self.assertIn(
            'last',
            selection_keys,
            "El método de coste 'last' no se encontró en la selección",
        )

    def test_last_cost_method_label(self):
        """El label del método 'last' debe ser 'Last Purchase Price'."""
        fields = self.env['product.category'].fields_get(['property_cost_method'])
        selection_dict = dict(fields['property_cost_method']['selection'])
        self.assertEqual(
            selection_dict.get('last'),
            'Last Purchase Price',
            "El label del método 'last' no es correcto",
        )

    def test_product_cost_method_last(self):
        """Un producto cuya categoría usa 'last' debe reflejarlo en product.cost_method."""
        self.assertEqual(
            self.product_last.cost_method,
            'last',
            "product.cost_method debe ser 'last' para productos con esa categoría",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_receipt_and_validate(self, product, price_unit, quantity=5.0):
        """Crea un albarán de entrada (recepción) y lo valida.

        Crea el picking, el move, las move_lines con picked=True,
        y llama a product_price_update_before_done() tal como lo haría Odoo
        al validar el albarán antes de crear los SVL.

        Returns: el stock.move creado
        """
        move = self.env['stock.move'].create({
            'name': f'Test entrada {product.name}',
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': product.uom_id.id,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'price_unit': price_unit,
            'company_id': self.env.company.id,
        })

        # Move line con picked=True para que _get_in_move_lines() lo devuelva
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': product.id,
            'quantity': quantity,
            'product_uom_id': product.uom_id.id,
            'location_id': self.loc_supplier.id,
            'location_dest_id': self.loc_stock.id,
            'picked': True,
        })

        return move

    # ------------------------------------------------------------------
    # Tests del comportamiento de product_price_update_before_done
    # ------------------------------------------------------------------

    def test_standard_price_updated_last_cost_method(self):
        """Con cost_method='last', standard_price debe actualizarse al precio de recepción.

        Odoo 18: _get_price_unit() devuelve {lot_record: float}.
        El fix usa next(iter(...)) para extraer el float correctamente.
        """
        # Precio inicial
        self.product_last.sudo().with_context(disable_auto_svl=True).write(
            {'standard_price': 10.0}
        )

        move = self._create_receipt_and_validate(self.product_last, price_unit=75.0)

        # Invocar el método directamente (igual que lo hace _action_done)
        move.product_price_update_before_done()

        self.assertEqual(
            self.product_last.standard_price,
            75.0,
            "standard_price debe actualizarse a 75.0 (último precio de compra)",
        )

    def test_standard_price_not_updated_standard_cost_method(self):
        """Con cost_method='standard', el override NO debe modificar standard_price.

        El método base (AVCO) también saltará los productos 'standard',
        así que el precio debe quedar intacto.
        """
        self.product_std.sudo().with_context(disable_auto_svl=True).write(
            {'standard_price': 20.0}
        )

        move = self._create_receipt_and_validate(self.product_std, price_unit=999.0)
        move.product_price_update_before_done()

        self.assertEqual(
            self.product_std.standard_price,
            20.0,
            "standard_price no debe cambiar para productos con cost_method='standard'",
        )

    def test_standard_price_updated_multiple_receipts(self):
        """Cada recepción actualiza standard_price al precio de esa recepción."""
        self.product_last.sudo().with_context(disable_auto_svl=True).write(
            {'standard_price': 10.0}
        )

        # Primera recepción: precio 50
        move1 = self._create_receipt_and_validate(self.product_last, price_unit=50.0)
        move1.product_price_update_before_done()
        self.assertEqual(self.product_last.standard_price, 50.0)

        # Segunda recepción: precio 80 → debe sobreescribir
        move2 = self._create_receipt_and_validate(self.product_last, price_unit=80.0)
        move2.product_price_update_before_done()
        self.assertEqual(
            self.product_last.standard_price,
            80.0,
            "standard_price debe reflejar el precio de la última recepción",
        )

    def test_get_price_unit_returns_dict_odoo18(self):
        """Verificar que _get_price_unit() devuelve un dict en Odoo 18.

        Esto documenta el cambio de API que motivó el fix en stock_move.py.
        """
        move = self._create_receipt_and_validate(self.product_last, price_unit=42.0)
        price_result = move._get_price_unit()

        self.assertIsInstance(
            price_result,
            dict,
            "_get_price_unit() debe devolver un dict {lot_record: float} en Odoo 18",
        )
        self.assertEqual(len(price_result), 1)
        price_float = next(iter(price_result.values()))
        self.assertAlmostEqual(price_float, 42.0, places=2)

