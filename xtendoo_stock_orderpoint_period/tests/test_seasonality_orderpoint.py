# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from datetime import date, timedelta
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

WIZARD = "odoo.addons.xtendoo_stock_orderpoint_period.wizard.seasonality_wizard"


class TestSeasonalityOrderpoint(TransactionCase):
    """Tests para el módulo xtendoo_stock_orderpoint_period."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.demand_factor_pct = 10.0
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.location = cls.warehouse.lot_stock_id
        cls.OP = cls.env["stock.warehouse.orderpoint"]
        cls.today = date.today()
        cls.product = cls._create_product("Test Producto Estacional")

    @classmethod
    def _create_product(cls, name):
        return cls.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "uom_id": cls.env.ref("uom.product_uom_unit").id,
            }
        )

    def _create_op(self, product=None, start=None, end=None, **kwargs):
        vals = {
            "product_id": (product or self.product).id,
            "warehouse_id": self.warehouse.id,
            "location_id": self.location.id,
            "product_min_qty": 5.0,
            "product_max_qty": 10.0,
            "trigger": "auto",
            "date_start": start,
            "date_end": end,
        }
        vals.update(kwargs)
        return self.OP.create(vals)

    def _days(self, n):
        return self.today + timedelta(days=n)

    # ────────────────────────────────────────────────────────────────────
    #  is_active_today
    # ────────────────────────────────────────────────────────────────────
    def test_is_active_today(self):
        cases = {
            "sin fechas": (None, None, True),
            "dentro del rango": (self._days(-5), self._days(5), True),
            "rango pasado": (self._days(-30), self._days(-1), False),
            "rango futuro": (self._days(1), self._days(30), False),
            "solo inicio pasado": (self._days(-5), None, True),
            "solo fin pasado": (None, self._days(-1), False),
        }
        for label, (start, end, expected) in cases.items():
            product = self._create_product("Test %s" % label)
            op = self._create_op(product, start, end)
            self.assertEqual(op.is_active_today, expected, label)

    def test_search_is_active_today(self):
        """Odoo 19 convierte '=' True en 'in' [True]: los tres deben coincidir."""
        past = self._create_op(
            self._create_product("P pasado"), self._days(-30), self._days(-1)
        )
        now = self._create_op(
            self._create_product("P vigente"), self._days(-1), self._days(1)
        )
        future = self._create_op(
            self._create_product("P futuro"), self._days(1), self._days(30)
        )
        always = self._create_op(self._create_product("P siempre"))
        mine = [("id", "in", (past | now | future | always).ids)]

        def found(domain):
            return self.OP.search(mine + domain)

        active = now | always
        inactive = past | future
        self.assertEqual(found([("is_active_today", "=", True)]), active)
        self.assertEqual(found([("is_active_today", "!=", False)]), active)
        self.assertEqual(found([("is_active_today", "in", [True])]), active)
        self.assertEqual(found([("is_active_today", "=", False)]), inactive)
        self.assertEqual(found([("is_active_today", "!=", True)]), inactive)
        self.assertEqual(found([("is_active_today", "not in", [True])]), inactive)
        self.assertEqual(
            found([("is_active_today", "in", [True, False])]), active | inactive
        )

    # ────────────────────────────────────────────────────────────────────
    #  Validaciones de fechas y solapes
    # ────────────────────────────────────────────────────────────────────
    def test_date_constraint(self):
        with self.assertRaises(ValidationError):
            self._create_op(start=self._days(5), end=self._days(-5))

    def test_different_periods_allowed(self):
        self._create_op(start=self._days(-10), end=self._days(10))
        op2 = self._create_op(start=self._days(11), end=self._days(40))
        self.assertTrue(op2)

    def test_overlapping_periods_rejected(self):
        self._create_op(start=self._days(-10), end=self._days(10))
        with self.assertRaises(ValidationError):
            self._create_op(start=self._days(0), end=self._days(30))

    def test_two_rules_without_dates_rejected(self):
        """Los NULL no son iguales para el UNIQUE de SQL: lo cubre Python."""
        self._create_op()
        with self.assertRaises(ValidationError):
            self._create_op()

    def test_open_rule_overlaps_dated_rule(self):
        self._create_op()
        with self.assertRaises(ValidationError):
            self._create_op(start=self._days(1), end=self._days(5))

    def test_overlap_detected_on_write(self):
        self._create_op(start=self._days(-10), end=self._days(10))
        op2 = self._create_op(start=self._days(11), end=self._days(40))
        with self.assertRaises(ValidationError):
            op2.date_start = self._days(5)

    def test_overlap_ignores_other_product_and_manual(self):
        self._create_op(start=self._days(-10), end=self._days(10))
        other = self._create_product("Otro producto")
        self._create_op(other, self._days(-10), self._days(10))
        # una regla manual (informe de reposición) no bloquea la automática
        manual = self._create_op(
            self._create_product("Manual"), trigger="manual"
        )
        self._create_op(manual.product_id)

    def test_adjacent_periods_do_not_overlap(self):
        self._create_op(start=self._days(-10), end=self._days(0))
        self._create_op(start=self._days(1), end=self._days(10))

    # ────────────────────────────────────────────────────────────────────
    #  Scheduler / reposición
    # ────────────────────────────────────────────────────────────────────
    def test_cron_domain_only_active_rules(self):
        past = self._create_op(
            self._create_product("C pasado"), self._days(-30), self._days(-1)
        )
        now = self._create_op(
            self._create_product("C vigente"), self._days(-1), self._days(1)
        )
        future = self._create_op(
            self._create_product("C futuro"), self._days(1), self._days(30)
        )
        domain = self.env["stock.rule"]._get_orderpoint_domain(
            company_id=self.company.id
        )
        found = self.OP.search(domain + [("id", "in", (past | now | future).ids)])
        self.assertEqual(found, now)

    def test_action_replenish_warns_on_inactive(self):
        op = self._create_op(start=self._days(-30), end=self._days(-1))
        result = op.action_replenish()
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "warning")

    def test_qty_to_order_zero_outside_period(self):
        """El informe de reposición no debe proponer pedidos de reglas
        caducadas o futuras, aunque el stock esté por debajo de su mínimo."""
        past = self._create_op(
            self._create_product("Q pasado"),
            self._days(-30),
            self._days(-1),
            product_min_qty=500,
            product_max_qty=500,
        )
        now = self._create_op(
            self._create_product("Q vigente"),
            self._days(-1),
            self._days(1),
            product_min_qty=40,
            product_max_qty=40,
        )
        both = past | now
        both._compute_qty_to_order_computed()
        self.assertEqual(past.qty_to_order_computed, 0.0)
        self.assertEqual(now.qty_to_order_computed, 40.0)

    # ────────────────────────────────────────────────────────────────────
    #  Wizard
    # ────────────────────────────────────────────────────────────────────
    def _create_wizard(self, **kwargs):
        vals = {
            "company_id": self.company.id,
            "warehouse_id": self.warehouse.id,
            "year_reference": self.today.year - 1,
            "target_year": self.today.year + 1,
            "product_ids": [(6, 0, [self.product.id])],
            "factor_pct": 10.0,
            "max_margin_pct": 50.0,
            "simulation": False,
        }
        vals.update(kwargs)
        return self.env["stock.orderpoint.seasonality.wizard"].create(vals)

    def _fake_demand(self, per_month):
        def _compute(self_wiz, products, months):
            return {
                (p.id, m): per_month.get(m, 0.0) for p in products for m in months
            }

        return patch(
            WIZARD + ".SeasonalityWizard._compute_demand", autospec=True,
            side_effect=_compute,
        )

    def test_month_selector_has_twelve_months(self):
        months = self.env["stock.orderpoint.seasonality.wizard.month"].search([])
        self.assertEqual(sorted(int(m) for m in months.mapped("month")), list(range(1, 13)))

    def test_month_selector_filters_months(self):
        Month = self.env["stock.orderpoint.seasonality.wizard.month"]
        wizard = self._create_wizard(
            all_year=False,
            month_ids=[(6, 0, Month.search([("month", "in", ("3", "7"))]).ids)],
        )
        with self._fake_demand({3: 100.0, 7: 40.0}):
            wizard.action_compute_preview()
        self.assertEqual(sorted(wizard.line_ids.mapped("month")), [3, 7])

    def test_no_months_selected_raises(self):
        wizard = self._create_wizard(all_year=False)
        with self.assertRaises(UserError):
            wizard.action_compute_preview()

    def test_preview_and_apply_with_max_margin(self):
        wizard = self._create_wizard(all_year=True)
        with self._fake_demand({1: 100.0}):
            wizard.action_compute_preview()
        jan = wizard.line_ids.filtered(lambda l: l.month == 1)
        self.assertAlmostEqual(jan.suggested_min_qty, 110.0)  # 100 × 1,10
        self.assertAlmostEqual(jan.suggested_max_qty, 165.0)  # 110 × 1,50
        self.assertEqual(jan.action_flag, "create")
        self.assertEqual(len(wizard.line_ids), 12)

        wizard.action_apply()
        year = self.today.year + 1
        op = self.OP.search(
            [
                ("product_id", "=", self.product.id),
                ("location_id", "=", self.location.id),
                ("date_start", "=", date(year, 1, 1)),
                ("date_end", "=", date(year, 1, 31)),
            ]
        )
        self.assertEqual(len(op), 1)
        self.assertAlmostEqual(op.product_min_qty, 110.0)
        self.assertAlmostEqual(op.product_max_qty, 165.0)
        self.assertEqual(op.trigger, "auto")

    def test_simulation_does_not_apply(self):
        wizard = self._create_wizard(simulation=True)
        with self._fake_demand({1: 100.0}):
            wizard.action_compute_preview()
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_wizard_upsert(self):
        """Una segunda ejecución actualiza en lugar de duplicar."""
        for _i in range(2):
            wizard = self._create_wizard()
            with self._fake_demand({1: 100.0}):
                wizard.action_compute_preview()
            wizard.action_apply()
        year = self.today.year + 1
        ops = self.OP.search(
            [
                ("product_id", "=", self.product.id),
                ("date_start", "=", date(year, 1, 1)),
            ]
        )
        self.assertEqual(len(ops), 1)
        wizard = self._create_wizard()
        with self._fake_demand({1: 100.0}):
            wizard.action_compute_preview()
        self.assertEqual(set(wizard.line_ids.mapped("action_flag")), {"update"})

    def test_wizard_skips_conflicting_rules(self):
        """Una regla automática sin fechas ya existente bloquea la creación;
        el wizard lo marca como conflicto y lo omite sin romper el lote."""
        self._create_op()
        wizard = self._create_wizard()
        with self._fake_demand({1: 100.0}):
            wizard.action_compute_preview()
        self.assertEqual(set(wizard.line_ids.mapped("action_flag")), {"conflict"})
        before = self.OP.search_count([("product_id", "=", self.product.id)])
        wizard.action_apply()
        self.assertEqual(
            self.OP.search_count([("product_id", "=", self.product.id)]), before
        )

    def test_demand_filtered_by_warehouse(self):
        """Las ventas de otro almacén no cuentan para la demanda."""
        if "sale.order" not in self.env or "warehouse_id" not in self.env["sale.order"]._fields:
            self.skipTest("sale_stock no instalado")
        other_wh = self.env["stock.warehouse"].create(
            {"name": "Otro almacén", "code": "OTW", "company_id": self.company.id}
        )
        partner = self.env["res.partner"].create({"name": "Cliente test"})
        year = self.today.year - 1
        for wh, qty in ((self.warehouse, 7.0), (other_wh, 1000.0)):
            order = self.env["sale.order"].create(
                {
                    "partner_id": partner.id,
                    "warehouse_id": wh.id,
                    "order_line": [
                        (0, 0, {"product_id": self.product.id, "product_uom_qty": qty})
                    ],
                }
            )
            order.action_confirm()
            order.date_order = date(year, 3, 10)
        wizard = self._create_wizard(year_reference=year)
        demand = wizard._compute_demand(self.product, [3])
        self.assertAlmostEqual(demand.get((self.product.id, 3), 0.0), 7.0)
