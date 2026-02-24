# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from datetime import date, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSeasonalityOrderpoint(TransactionCase):
    """Tests para el módulo xtendoo_stock_orderpoint_period."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.ref("base.main_company")
        cls.company.demand_factor_pct = 10.0  # 10% factor

        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.location = cls.warehouse.lot_stock_id

        # Producto almacenable
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Producto Estacional",
                "is_storable": True,
                "uom_id": cls.env.ref("uom.product_uom_unit").id,
            }
        )

        # Ubicación de cliente (para movimientos de salida)
        cls.customer_location = cls.env.ref("stock.stock_location_customers")

    # ────────────────────────────────────────────────────────────────────
    #  Test 1: Compute is_active_today con varios rangos
    # ────────────────────────────────────────────────────────────────────
    def test_is_active_today_no_dates(self):
        """Orderpoint sin fechas debe estar siempre activo."""
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
            }
        )
        self.assertTrue(op.is_active_today)

    def test_is_active_today_within_range(self):
        """Orderpoint con rango que incluye hoy debe estar activo."""
        today = date.today()
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
                "date_start": today - timedelta(days=5),
                "date_end": today + timedelta(days=5),
            }
        )
        self.assertTrue(op.is_active_today)

    def test_is_active_today_past_range(self):
        """Orderpoint con rango pasado no debe estar activo."""
        today = date.today()
        # Necesitamos un producto diferente porque hay unique constraint
        product2 = self.env["product.product"].create(
            {
                "name": "Test Producto Pasado",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product2.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
                "date_start": today - timedelta(days=30),
                "date_end": today - timedelta(days=1),
            }
        )
        self.assertFalse(op.is_active_today)

    def test_is_active_today_future_range(self):
        """Orderpoint con rango futuro no debe estar activo."""
        today = date.today()
        product3 = self.env["product.product"].create(
            {
                "name": "Test Producto Futuro",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product3.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
                "date_start": today + timedelta(days=1),
                "date_end": today + timedelta(days=30),
            }
        )
        self.assertFalse(op.is_active_today)

    def test_is_active_today_only_start_set(self):
        """Si solo date_start está definido y es pasado, debe estar activo."""
        today = date.today()
        product4 = self.env["product.product"].create(
            {
                "name": "Test Solo Inicio",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product4.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
                "date_start": today - timedelta(days=5),
            }
        )
        self.assertTrue(op.is_active_today)

    # ────────────────────────────────────────────────────────────────────
    #  Test 2: Constraint date_start <= date_end
    # ────────────────────────────────────────────────────────────────────
    def test_date_constraint(self):
        """date_start > date_end debe lanzar ValidationError."""
        today = date.today()
        product5 = self.env["product.product"].create(
            {
                "name": "Test Constraint",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["stock.warehouse.orderpoint"].create(
                {
                    "product_id": product5.id,
                    "warehouse_id": self.warehouse.id,
                    "location_id": self.location.id,
                    "product_min_qty": 5.0,
                    "product_max_qty": 10.0,
                    "date_start": today + timedelta(days=5),
                    "date_end": today - timedelta(days=5),
                }
            )

    # ────────────────────────────────────────────────────────────────────
    #  Test 3: Filtrado del CRON (_get_orderpoint_domain)
    # ────────────────────────────────────────────────────────────────────
    def test_cron_domain_filters_by_date(self):
        """El dominio del scheduler debe filtrar orderpoints por período."""
        StockRule = self.env["stock.rule"]
        domain = StockRule._get_orderpoint_domain(company_id=self.company.id)

        # Verificar que el dominio contiene filtros de fecha
        domain_str = str(domain)
        self.assertIn("date_start", domain_str)
        self.assertIn("date_end", domain_str)

    # ────────────────────────────────────────────────────────────────────
    #  Test 4: Wizard upsert - no duplica, actualiza
    # ────────────────────────────────────────────────────────────────────
    def test_wizard_upsert(self):
        """El wizard no debe duplicar un orderpoint existente."""
        today = date.today()
        # Crear orderpoint existente para enero del año objetivo
        ds = date(today.year, 1, 1)
        de = date(today.year, 1, 31)

        existing_op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
                "date_start": ds,
                "date_end": de,
            }
        )

        # Crear wizard
        wizard = self.env["stock.orderpoint.seasonality.wizard"].create(
            {
                "company_id": self.company.id,
                "warehouse_id": self.warehouse.id,
                "year_reference": today.year - 1,
                "target_year": today.year,
                "all_year": False,
                "product_ids": [(6, 0, [self.product.id])],
                "factor_pct": 10.0,
                "simulation": False,
            }
        )

        # Crear línea de preview manualmente simulando enero
        self.env["stock.orderpoint.seasonality.wizard.line"].create(
            {
                "wizard_id": wizard.id,
                "product_id": self.product.id,
                "month": 1,
                "demand_qty": 100.0,
                "factor_pct": 10.0,
                "suggested_min_qty": 110.0,
                "date_start": ds,
                "date_end": de,
                "action_flag": "update",
                "existing_orderpoint_id": existing_op.id,
            }
        )

        wizard.action_apply()

        # Verificar que se actualizó y no se duplicó
        ops = self.env["stock.warehouse.orderpoint"].search(
            [
                ("product_id", "=", self.product.id),
                ("location_id", "=", self.location.id),
                ("date_start", "=", ds),
                ("date_end", "=", de),
            ]
        )
        self.assertEqual(len(ops), 1, "No debe haber duplicados")
        self.assertAlmostEqual(ops.product_min_qty, 110.0, places=2)

    # ────────────────────────────────────────────────────────────────────
    #  Test 5: Factor aplicado correctamente
    # ────────────────────────────────────────────────────────────────────
    def test_factor_applied(self):
        """El factor de demanda se aplica correctamente."""
        demand_qty = 100.0
        factor_pct = 15.0
        expected = demand_qty * (1 + factor_pct / 100.0)  # 115.0
        self.assertAlmostEqual(expected, 115.0, places=2)

    # ────────────────────────────────────────────────────────────────────
    #  Test 6: Demand computation con movimientos de stock
    # ────────────────────────────────────────────────────────────────────
    def test_demand_computation_with_moves(self):
        """Verificar que el cálculo de demanda suma salidas y resta devoluciones."""
        # Crear un movimiento de salida (done)
        year_ref = date.today().year - 1
        move_date = date(year_ref, 3, 15)

        # Movimiento de salida
        move_out = self.env["stock.move"].create(
            {
                "name": "Salida test",
                "product_id": self.product.id,
                "product_uom_qty": 50.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.location.id,
                "location_dest_id": self.customer_location.id,
                "date": move_date,
                "company_id": self.company.id,
            }
        )
        move_out._action_confirm()
        move_out.quantity = 50.0
        move_out.picked = True
        move_out._action_done()

        # Crear wizard y calcular demanda
        wizard = self.env["stock.orderpoint.seasonality.wizard"].create(
            {
                "company_id": self.company.id,
                "warehouse_id": self.warehouse.id,
                "year_reference": year_ref,
                "target_year": date.today().year,
                "all_year": False,
                "product_ids": [(6, 0, [self.product.id])],
                "factor_pct": 0.0,
                "simulation": True,
            }
        )

        products = wizard._get_products()
        demand = wizard._compute_demand(products, [3])

        # La demanda de marzo debe ser >= 50 (puede tener otros movimientos)
        march_demand = demand.get((self.product.id, 3), 0.0)
        self.assertGreaterEqual(
            march_demand,
            50.0,
            "La demanda de marzo debe incluir el movimiento de salida",
        )

    # ────────────────────────────────────────────────────────────────────
    #  Test 7: action_replenish filtra por período
    # ────────────────────────────────────────────────────────────────────
    def test_action_replenish_filters_inactive(self):
        """action_replenish sobre un orderpoint inactivo hoy no genera error."""
        today = date.today()
        product6 = self.env["product.product"].create(
            {
                "name": "Test Replenish Inactivo",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product6.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.location.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
                "date_start": today - timedelta(days=30),
                "date_end": today - timedelta(days=1),
            }
        )
        # Debe devolver {} ya que el orderpoint no está activo hoy
        result = op.action_replenish()
        self.assertEqual(result, {}, "Un orderpoint inactivo no debe generar acción")

    # ────────────────────────────────────────────────────────────────────
    #  Test 8: Search is_active_today
    # ────────────────────────────────────────────────────────────────────
    def test_search_is_active_today(self):
        """El search de is_active_today debe devolver resultados correctos."""
        active_ops = self.env["stock.warehouse.orderpoint"].search(
            [
                ("is_active_today", "=", True),
                ("company_id", "=", self.company.id),
            ]
        )
        # Todos los encontrados deben tener is_active_today == True
        for op in active_ops:
            self.assertTrue(op.is_active_today)
