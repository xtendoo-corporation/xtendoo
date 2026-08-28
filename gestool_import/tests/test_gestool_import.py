from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestGestoolTicketImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard = cls.env["gestool.import"].create({})
        income_account = cls.env["account.account"].create({
            "code": "GESTOOL.SALES",
            "name": "Ventas Gestool",
            "account_type": "income",
        })
        suspense_account = cls.env["account.account"].create({
            "code": "GESTOOL.CASH.SUSPENSE",
            "name": "Transitoria caja Gestool",
            "account_type": "asset_current",
            "reconcile": True,
        })
        pos_receivable_account = cls.env["account.account"].create({
            "code": "GESTOOL.POS.RECEIVABLE",
            "name": "Cobros TPV Gestool",
            "account_type": "asset_receivable",
            "reconcile": True,
        })
        cls.env.company.account_default_pos_receivable_account_id = (
            pos_receivable_account
        )
        cash_loss_account = cls.env["account.account"].create({
            "code": "GESTOOL.CASH.LOSS",
            "name": "Pérdidas caja Gestool",
            "account_type": "expense",
        })
        cash_profit_account = cls.env["account.account"].create({
            "code": "GESTOOL.CASH.PROFIT",
            "name": "Ganancias caja Gestool",
            "account_type": "income_other",
        })
        template = cls.env["product.template"].create({
            "name": "Producto Gestool",
            "default_code": "GESTOOL-001",
            "property_account_income_id": income_account.id,
        })
        cls.product = template.product_variant_id
        cls.partner = cls.env["res.partner"].create({
            "name": "Cliente Gestool",
            "ref": "CLIENTE-001",
        })
        cls.pricelist = cls.env["product.pricelist"].create({
            "name": "Tarifa Gestool",
            "currency_id": cls.env.company.currency_id.id,
            "company_id": cls.env.company.id,
        })
        cls.pos_configs = cls.env["pos.config"]
        for name in ("TPV Gestool Norte", "TPV Gestool Sur"):
            cash_method = cls.env["pos.config"]._create_cash_payment_method({
                "name": f"Efectivo {name}",
            })
            cash_method.journal_id.suspense_account_id = suspense_account
            cash_method.journal_id.loss_account_id = cash_loss_account
            cash_method.journal_id.profit_account_id = cash_profit_account
            cls.pos_configs |= cls.env["pos.config"].create({
                "name": name,
                "company_id": cls.env.company.id,
                "payment_method_ids": [(6, 0, [cash_method.id])],
                "pricelist_id": cls.pricelist.id,
            })

    @classmethod
    def _ticket_row(
        cls, reference="TICKET-001", product_code="GESTOOL-001",
        pos_name=None,
    ):
        row = [""] * 19
        row[3] = reference
        row[5] = "24/08/2026"
        row[7] = pos_name or cls.pos_configs[0].name
        row[9] = "CLIENTE-001"
        row[15] = product_code
        row[16] = "10.00"
        row[17] = "1"
        row[18] = "21"
        return row

    def test_get_ticket_product_strips_code(self):
        product = self.wizard._get_ticket_product("  GESTOOL-001  ")

        self.assertEqual(product, self.product)

    def test_parse_ticket_missing_product_returns_false(self):
        row = self._ticket_row(product_code="NO-EXISTE")

        self.assertFalse(self.wizard.parse_ticket(row, self.env["pos.session"]))

    def test_invalid_line_skips_complete_ticket_without_session(self):
        header = ",".join(["cabecera"] * 19)
        valid_line = ",".join(self._ticket_row())
        invalid_line = ",".join(self._ticket_row(product_code="NO-EXISTE"))
        csv_data = "\n".join((header, valid_line, invalid_line)).encode()
        orders_before = self.env["pos.order"].search_count([
            ("pos_reference", "=", "TICKET-001"),
        ])

        with patch.object(
            type(self.wizard),
            "_create_import_session",
            side_effect=AssertionError("No debe abrir una sesión para tickets inválidos"),
        ):
            result = self.wizard._import_ticket(csv_data)

        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("NO-EXISTE", result["params"]["message"])
        self.assertEqual(
            self.env["pos.order"].search_count([
                ("pos_reference", "=", "TICKET-001"),
            ]),
            orders_before,
        )

    def test_masked_quantity_skips_complete_ticket_without_session(self):
        header = ",".join(["cabecera"] * 19)
        valid_line = self._ticket_row(reference="TICKET-CANTIDAD-INVALIDA")
        invalid_line = self._ticket_row(reference="TICKET-CANTIDAD-INVALIDA")
        invalid_line[17] = "******.**"
        csv_data = "\n".join((
            header,
            ",".join(valid_line),
            ",".join(invalid_line),
        )).encode()

        with patch.object(
            type(self.wizard),
            "_create_import_session",
            side_effect=AssertionError("No debe abrir una sesión para números inválidos"),
        ):
            result = self.wizard._import_ticket(csv_data)

        message = result["params"]["message"]
        self.assertIn("TICKET-CANTIDAD-INVALIDA", message)
        self.assertIn("cantidad '******.**'", message)
        self.assertFalse(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-CANTIDAD-INVALIDA"),
        ]))

    def test_invalid_number_does_not_block_valid_ticket(self):
        header = ",".join(["cabecera"] * 19)
        invalid_line = self._ticket_row(reference="TICKET-PRECIO-INVALIDO")
        invalid_line[16] = "NaN"
        valid_line = self._ticket_row(reference="TICKET-NUMERICO-VALIDO")

        result = self.wizard._import_ticket("\n".join((
            header,
            ",".join(invalid_line),
            ",".join(valid_line),
        )).encode())

        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("precio 'NaN'", result["params"]["message"])
        self.assertFalse(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-PRECIO-INVALIDO"),
        ]))
        self.assertTrue(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-NUMERICO-VALIDO"),
        ]))

    def test_import_session_has_cash_payment_method(self):
        session = self.wizard._create_import_session(self.pos_configs[0])

        cash_methods = session.config_id.payment_method_ids.filtered(
            lambda method: method.type == "cash"
        )
        self.assertTrue(cash_methods)
        self.assertEqual(cash_methods[:1].config_ids, session.config_id)
        self.assertEqual(session.name, "0000")
        self.assertEqual(session.state, "opened")
        self.assertTrue(session.rescue)

    def test_existing_non_cash_payment_is_replaced_with_cash(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        order = self.wizard.parse_ticket(self._ticket_row(), session)
        non_cash_method = self.env["pos.payment.method"].create({
            "name": "Pago CSV no efectivo",
            "company_id": self.env.company.id,
            "config_ids": [(4, session.config_id.id)],
        })
        order.add_payment({
            "pos_order_id": order.id,
            "payment_method_id": non_cash_method.id,
            "amount": 1.0,
            "payment_date": order.date_order,
        })

        cash_method = self.wizard._ensure_import_cash_payment_method(
            session.config_id
        )
        payments = self.wizard._replace_order_payments_with_cash(
            order, cash_method
        )

        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.payment_method_id.type, "cash")
        self.assertEqual(payments.amount, order.amount_total)
        self.assertEqual(order.amount_paid, order.amount_total)

    def test_negative_order_is_reported_without_creating_session(self):
        row = self._ticket_row(reference="TICKET-NEGATIVO")
        row[17] = "-1"
        header = ",".join(["cabecera"] * 19)

        with patch.object(
            type(self.wizard),
            "_create_import_session",
            side_effect=AssertionError("No debe abrir una sesión para ventas negativas"),
        ):
            result = self.wizard._import_ticket(
                "\n".join((header, ",".join(row))).encode()
            )

        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("TICKET-NEGATIVO", result["params"]["message"])
        self.assertIn("total negativo", result["params"]["message"])
        self.assertFalse(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-NEGATIVO"),
        ]))

    def test_multiline_negative_order_is_skipped_completely(self):
        header = ",".join(["cabecera"] * 19)
        positive_line = self._ticket_row(reference="TICKET-MULTILINEA-NEGATIVO")
        negative_line = self._ticket_row(reference="TICKET-MULTILINEA-NEGATIVO")
        negative_line[17] = "-2"
        csv_data = "\n".join((
            header,
            ",".join(positive_line),
            ",".join(negative_line),
        )).encode()

        with patch.object(
            type(self.wizard),
            "_create_import_session",
            side_effect=AssertionError("No debe abrir una sesión para ventas negativas"),
        ):
            result = self.wizard._import_ticket(csv_data)

        self.assertIn("TICKET-MULTILINEA-NEGATIVO", result["params"]["message"])
        self.assertFalse(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-MULTILINEA-NEGATIVO"),
        ]))

    def test_multiline_order_with_positive_total_is_imported(self):
        header = ",".join(["cabecera"] * 19)
        positive_line = self._ticket_row(reference="TICKET-MULTILINEA-POSITIVO")
        positive_line[17] = "2"
        negative_line = self._ticket_row(reference="TICKET-MULTILINEA-POSITIVO")
        negative_line[17] = "-1"

        result = self.wizard._import_ticket("\n".join((
            header,
            ",".join(positive_line),
            ",".join(negative_line),
        )).encode())
        order = self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-MULTILINEA-POSITIVO"),
        ])

        self.assertTrue(result)
        self.assertEqual(len(order), 1)
        self.assertEqual(len(order.lines), 2)
        self.assertGreater(order.amount_total, 0)

    def test_negative_price_ticket_does_not_block_positive_ticket(self):
        header = ",".join(["cabecera"] * 19)
        negative_line = self._ticket_row(reference="TICKET-PRECIO-NEGATIVO")
        negative_line[16] = "-10.00"
        positive_line = self._ticket_row(reference="TICKET-VALIDO")

        result = self.wizard._import_ticket("\n".join((
            header,
            ",".join(negative_line),
            ",".join(positive_line),
        )).encode())

        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("TICKET-PRECIO-NEGATIVO", result["params"]["message"])
        self.assertFalse(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-PRECIO-NEGATIVO"),
        ]))
        self.assertTrue(self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-VALIDO"),
        ]))

    def test_positive_order_still_creates_customer_invoice(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        order = self.wizard.parse_ticket(
            self._ticket_row(reference="TICKET-POSITIVO"), session
        )

        self.wizard._confirm_and_invoice_order(order)

        self.assertFalse(order.is_refund)
        self.assertEqual(order.account_move.move_type, "out_invoice")
        self.assertEqual(order.account_move.state, "posted")

    def test_get_ticket_pos_config_strips_name(self):
        config = self.wizard._get_ticket_pos_config(
            f"  {self.pos_configs[1].name}  "
        )

        self.assertEqual(config, self.pos_configs[1])

    def test_order_uses_pos_default_pricelist(self):
        session = self.wizard._create_import_session(self.pos_configs[0])

        order = self.wizard.parse_ticket(self._ticket_row(), session)

        self.assertEqual(order.pricelist_id, self.pricelist)

    def test_import_pricelist_falls_back_when_pos_has_no_default(self):
        config = self.pos_configs[0]
        config.pricelist_id = False

        pricelist = self.wizard._get_import_pricelist(config)

        self.assertTrue(pricelist)
        self.assertEqual(pricelist.currency_id, config.currency_id)
        self.assertIn(pricelist.company_id, (config.company_id, self.env["res.company"]))

    def test_unknown_pos_is_reported_without_creating_session(self):
        header = ",".join(["cabecera"] * 19)
        line = ",".join(self._ticket_row(pos_name="TPV INEXISTENTE"))

        with patch.object(
            type(self.wizard),
            "_create_import_session",
            side_effect=AssertionError("No debe abrir una sesión para un TPV inválido"),
        ):
            result = self.wizard._import_ticket(
                "\n".join((header, line)).encode()
            )

        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("TPV INEXISTENTE", result["params"]["message"])

    def test_same_ticket_in_multiple_points_of_sale_is_rejected(self):
        header = ",".join(["cabecera"] * 19)
        north = ",".join(self._ticket_row(pos_name=self.pos_configs[0].name))
        south = ",".join(self._ticket_row(pos_name=self.pos_configs[1].name))

        with patch.object(
            type(self.wizard),
            "_create_import_session",
            side_effect=AssertionError("No debe abrir una sesión para un ticket ambiguo"),
        ):
            result = self.wizard._import_ticket(
                "\n".join((header, north, south)).encode()
            )

        self.assertIn("varios puntos de venta", result["params"]["message"])

    def test_order_uses_requested_pos_and_session_is_closed(self):
        config = self.pos_configs[1]
        session = self.wizard._create_import_session(config)
        order = self.wizard.parse_ticket(
            self._ticket_row(pos_name=config.name), session
        )
        cash_method = self.wizard._ensure_import_cash_payment_method(config)
        self.wizard._replace_order_payments_with_cash(order, cash_method)
        order.action_pos_order_paid()

        self.wizard._close_import_session(session)

        self.assertEqual(order.config_id, config)
        self.assertEqual(order.session_id, session)
        self.assertEqual(session.name, "0000")
        self.assertEqual(session.state, "closed")
        self.assertEqual(session.cash_register_difference, 0.0)

    def test_csv_groups_orders_in_closed_session_per_pos(self):
        header = ",".join(["cabecera"] * 19)
        north = ",".join(self._ticket_row(
            reference="TICKET-NORTE",
            pos_name=self.pos_configs[0].name,
        ))
        south = ",".join(self._ticket_row(
            reference="TICKET-SUR",
            pos_name=self.pos_configs[1].name,
        ))

        def pay_without_invoice(wizard, order):
            cash_method = wizard._ensure_import_cash_payment_method(
                order.config_id
            )
            wizard._replace_order_payments_with_cash(order, cash_method)
            order.action_pos_order_paid()

        with patch.object(
            type(self.wizard),
            "_confirm_and_invoice_order",
            autospec=True,
            side_effect=pay_without_invoice,
        ):
            result = self.wizard._import_ticket(
                "\n".join((header, north, south)).encode()
            )

        self.assertTrue(result)
        orders = self.env["pos.order"].search([
            ("pos_reference", "in", ("TICKET-NORTE", "TICKET-SUR")),
        ])
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders.session_id.mapped("name"), ["0000", "0000"])
        self.assertEqual(set(orders.config_id.ids), set(self.pos_configs.ids))
        self.assertEqual(set(orders.session_id.mapped("state")), {"closed"})

