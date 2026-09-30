from base64 import b64encode
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class GestoolTransactionMixin:
    """Tests cannot COMMIT/ROLLBACK the test cursor: record the calls instead."""

    def setUp(self):
        super().setUp()
        wizard_class = type(self.env["gestool.import"])
        self.commit_mock = self.startPatcher(
            patch.object(wizard_class, "_commit_import_progress")
        )
        self.rollback_mock = self.startPatcher(
            patch.object(wizard_class, "_rollback_import_progress")
        )


class TestGestoolMultipleFileImport(GestoolTransactionMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard = cls.env["gestool.import"].create({})

    def _attachment(self, name, contents):
        return self.env["ir.attachment"].create({
            "name": name,
            "datas": b64encode(contents),
        })

    def test_imports_multiple_files_sequentially(self):
        first = self._attachment("clientes-01.csv", b"first")
        second = self._attachment("clientes-02.csv", b"second")
        self.wizard.partner_attachment_ids = [(6, 0, [second.id, first.id])]
        imported = []

        with patch.object(
            type(self.wizard),
            "_import_partner",
            side_effect=lambda data: imported.append(data),
        ):
            result = self.wizard.import_file()

        self.assertEqual(imported, [b"first", b"second"])
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("2", result["params"]["message"])

    def test_continues_with_next_file_after_error(self):
        first = self._attachment("clientes-error.csv", b"invalid")
        second = self._attachment("clientes-ok.csv", b"valid")
        self.wizard.partner_attachment_ids = [(6, 0, [first.id, second.id])]
        imported = []

        def import_partner(data):
            if data == b"invalid":
                raise UserError("CSV no válido")
            imported.append(data)

        with patch.object(
            type(self.wizard), "_import_partner", side_effect=import_partner
        ):
            result = self.wizard.import_file()

        self.assertEqual(imported, [b"valid"])
        self.assertEqual(result["params"]["type"], "danger")
        self.assertIn("clientes-error.csv", result["params"]["message"])
        self.rollback_mock.assert_called_once_with()
        self.commit_mock.assert_called_once_with()

    def test_commits_each_successful_file(self):
        first = self._attachment("clientes-01.csv", b"first")
        second = self._attachment("clientes-02.csv", b"second")
        self.wizard.partner_attachment_ids = [(6, 0, [first.id, second.id])]

        with patch.object(type(self.wizard), "_import_partner"):
            self.wizard.import_file()

        self.assertEqual(self.commit_mock.call_count, 2)
        self.rollback_mock.assert_not_called()

    def test_keeps_legacy_single_binary_file_compatibility(self):
        self.wizard.write({
            "data_file_partner": b64encode(b"legacy"),
            "filename_partner": "clientes-antiguo.csv",
        })

        with patch.object(type(self.wizard), "_import_partner") as import_partner:
            self.wizard.import_file()

        import_partner.assert_called_once_with(b"legacy")

    def test_requires_at_least_one_file(self):
        with self.assertRaisesRegex(UserError, "Selecciona al menos un fichero"):
            self.wizard.import_file()


class TestGestoolTicketImport(GestoolTransactionMixin, TransactionCase):
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
        # Sin plan contable instalado no hay diario de ventas ni cuenta a
        # cobrar para facturar los pedidos: se crean para aislar los tests.
        if not cls.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", cls.env.company.id),
        ], limit=1):
            cls.env["account.journal"].create({
                "name": "Ventas Gestool",
                "code": "GVEN",
                "type": "sale",
                "company_id": cls.env.company.id,
                "default_account_id": income_account.id,
            })
        receivable_account = cls.env["account.account"].create({
            "code": "GESTOOL.RECEIVABLE",
            "name": "Clientes Gestool",
            "account_type": "asset_receivable",
            "reconcile": True,
        })
        if not cls.env.company.transfer_account_id:
            cls.env.company.transfer_account_id = cls.env["account.account"].create({
                "code": "GESTOOL.TRANSFER",
                "name": "Transferencias internas Gestool",
                "account_type": "asset_current",
                "reconcile": True,
            })
        cls.product = template.product_variant_id
        cls.partner = cls.env["res.partner"].create({
            "name": "Cliente Gestool",
            "ref": "CLIENTE-001",
            "property_account_receivable_id": receivable_account.id,
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
        row[5] = "24/07/2026"
        row[7] = pos_name or cls.pos_configs[0].name
        row[9] = "CLIENTE-001"
        row[15] = product_code
        row[16] = "10.00"
        row[17] = "1"
        row[18] = "21"
        return row

    def test_order_env_uses_session_company_without_force_company(self):
        session = self.wizard._create_import_session(self.pos_configs[0])

        order = self.wizard.parse_ticket(self._ticket_row(), session)

        self.assertEqual(order.env.company, session.company_id)
        self.assertNotIn("force_company", order.env.context)

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

    def test_import_payment_method_is_not_cash(self):
        payment_method = self.wizard._ensure_import_payment_method(
            self.pos_configs[0]
        )

        self.assertNotEqual(payment_method.journal_id.type, "cash")
        self.assertEqual(payment_method.config_ids, self.pos_configs[0])

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

    @staticmethod
    def _pay_without_invoice(wizard, order):
        cash_method = wizard._ensure_import_cash_payment_method(order.config_id)
        wizard._replace_order_payments_with_cash(order, cash_method)
        order.action_pos_order_paid()

    def _ticket_csv(self, *references):
        header = ",".join(["cabecera"] * 19)
        rows = [
            ",".join(self._ticket_row(reference=reference))
            for reference in references
        ]
        return "\n".join((header, *rows)).encode()

    def test_failed_order_is_rolled_back_without_blocking_the_rest(self):
        def confirm_or_fail(wizard, order):
            if order.pos_reference == "TICKET-FALLA":
                order.write({"amount_paid": 999.0})
                raise UserError("Factura no válida")
            self._pay_without_invoice(wizard, order)

        with patch.object(
            type(self.wizard),
            "_confirm_and_invoice_order",
            autospec=True,
            side_effect=confirm_or_fail,
        ):
            result = self.wizard._import_ticket(
                self._ticket_csv("TICKET-ANTES", "TICKET-FALLA", "TICKET-DESPUES")
            )

        orders = self.env["pos.order"].search([
            ("pos_reference", "in", (
                "TICKET-ANTES", "TICKET-FALLA", "TICKET-DESPUES",
            )),
        ])
        self.assertEqual(
            set(orders.mapped("pos_reference")),
            {"TICKET-ANTES", "TICKET-DESPUES"},
        )
        self.assertFalse(
            orders.filtered(lambda order: order.state == "draft"),
            "Los pedidos válidos deben quedar pagados",
        )
        self.assertEqual(orders.session_id.state, "closed")
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("TICKET-FALLA", result["params"]["message"])
        self.assertIn("Factura no válida", result["params"]["message"])

    def test_multiline_ticket_is_confirmed_once_inside_its_savepoint(self):
        header = ",".join(["cabecera"] * 19)
        first_line = ",".join(self._ticket_row(reference="TICKET-MULTI"))
        second_line = ",".join(self._ticket_row(reference="TICKET-MULTI"))

        with patch.object(
            type(self.wizard),
            "_confirm_and_invoice_order",
            autospec=True,
            side_effect=self._pay_without_invoice,
        ) as confirm:
            self.wizard._import_ticket(
                "\n".join((header, first_line, second_line)).encode()
            )

        order = self.env["pos.order"].search([
            ("pos_reference", "=", "TICKET-MULTI"),
        ])
        self.assertEqual(len(order), 1)
        self.assertEqual(len(order.lines), 2)
        confirm.assert_called_once()

    def test_commits_every_ten_orders_and_after_closing_session(self):
        references = [f"TICKET-{number:02d}" for number in range(1, 12)]

        with patch.object(
            type(self.wizard),
            "_confirm_and_invoice_order",
            autospec=True,
            side_effect=self._pay_without_invoice,
        ):
            result = self.wizard._import_ticket(self._ticket_csv(*references))

        self.assertIs(result, True)
        # 1 commit tras el décimo pedido + 1 tras cerrar la sesión 0000.
        self.assertEqual(self.commit_mock.call_count, 2)
        self.rollback_mock.assert_not_called()

    def _two_pos_csv(self):
        header = ",".join(["cabecera"] * 19)
        north = ",".join(self._ticket_row(
            reference="TICKET-NORTE", pos_name=self.pos_configs[0].name,
        ))
        south = ",".join(self._ticket_row(
            reference="TICKET-SUR", pos_name=self.pos_configs[1].name,
        ))
        return "\n".join((header, north, south)).encode()

    def test_session_open_error_skips_only_that_pos(self):
        wizard_class = type(self.wizard)
        create_session = wizard_class._create_import_session
        failing_config = self.pos_configs[0]

        def create_or_fail(wizard, config):
            if config == failing_config:
                raise UserError("Sesión bloqueada")
            return create_session(wizard, config)

        with patch.object(
            wizard_class, "_create_import_session",
            autospec=True, side_effect=create_or_fail,
        ):
            result = self._import_tickets_without_invoice(self._two_pos_csv())

        self.assertFalse(self._orders("TICKET-NORTE"))
        south = self._orders("TICKET-SUR")
        self.assertEqual(len(south), 1)
        self.assertEqual(south.session_id.state, "closed")
        message = result["params"]["message"]
        self.assertIn(f"TPV {failing_config.name}: error en su sesión 0000", message)
        self.assertIn("Sesión bloqueada", message)
        self.assertIn("TICKET-NORTE omitido por error", message)

    def test_session_close_error_keeps_orders_and_continues(self):
        wizard_class = type(self.wizard)
        close_session = wizard_class._close_import_session
        failing_config = self.pos_configs[0]

        def close_or_fail(wizard, session):
            if session.config_id == failing_config:
                session.write({"opening_notes": "cierre parcial"})
                raise UserError("Descuadre de caja")
            return close_session(wizard, session)

        with patch.object(
            wizard_class, "_close_import_session",
            autospec=True, side_effect=close_or_fail,
        ):
            result = self._import_tickets_without_invoice(self._two_pos_csv())

        north = self._orders("TICKET-NORTE")
        south = self._orders("TICKET-SUR")
        self.assertEqual(len(north), 1)
        self.assertEqual(north.state, "paid")
        self.assertEqual(north.session_id.state, "opened")
        self.assertNotEqual(north.session_id.opening_notes, "cierre parcial")
        self.assertEqual(south.session_id.state, "closed")
        message = result["params"]["message"]
        self.assertIn(f"TPV {failing_config.name}: error en su sesión 0000", message)
        self.assertIn("Descuadre de caja", message)

    def test_warning_truncates_failed_tickets(self):
        failed_tickets = {
            f"TICKET-{number:02d}": "error" for number in range(21)
        }

        result = self.wizard._ticket_import_warning(
            {}, [], failed_tickets=failed_tickets
        )

        message = result["params"]["message"]
        self.assertIn("TICKET-19", message)
        self.assertNotIn("TICKET-20", message)
        self.assertIn("1 ticket(s) más con error", message)

    def _import_tickets_without_invoice(self, csv_data):
        with patch.object(
            type(self.wizard),
            "_confirm_and_invoice_order",
            autospec=True,
            side_effect=self._pay_without_invoice,
        ):
            return self.wizard._import_ticket(csv_data)

    def _orders(self, reference):
        return self.env["pos.order"].search([("pos_reference", "=", reference)])

    def test_reimporting_same_csv_discards_already_imported_tickets(self):
        csv_data = self._ticket_csv("TICKET-DUP")
        self.assertIs(self._import_tickets_without_invoice(csv_data), True)
        first_order = self._orders("TICKET-DUP")

        with patch.object(
            type(self.wizard), "_create_import_session"
        ) as create_session:
            result = self._import_tickets_without_invoice(csv_data)

        self.assertEqual(self._orders("TICKET-DUP"), first_order)
        create_session.assert_not_called()
        message = result["params"]["message"]
        self.assertIn("1 ticket(s) descartado(s) por estar ya importados", message)
        self.assertIn(
            f"Ticket TICKET-DUP ya importado (pedido {first_order.name})", message
        )

    def test_mixed_csv_imports_only_new_tickets(self):
        self._import_tickets_without_invoice(self._ticket_csv("TICKET-VIEJO"))

        result = self._import_tickets_without_invoice(
            self._ticket_csv("TICKET-VIEJO", "TICKET-NUEVO")
        )

        self.assertEqual(len(self._orders("TICKET-VIEJO")), 1)
        self.assertEqual(len(self._orders("TICKET-NUEVO")), 1)
        self.assertIn("TICKET-VIEJO ya importado", result["params"]["message"])
        self.assertNotIn("TICKET-NUEVO", result["params"]["message"])

    def test_same_reference_in_another_pos_is_not_a_duplicate(self):
        north, south = self.pos_configs
        header = ",".join(["cabecera"] * 19)
        self._import_tickets_without_invoice("\n".join((
            header,
            ",".join(self._ticket_row(reference="TICKET-COMUN", pos_name=north.name)),
        )).encode())

        result = self._import_tickets_without_invoice("\n".join((
            header,
            ",".join(self._ticket_row(reference="TICKET-COMUN", pos_name=south.name)),
        )).encode())

        self.assertIs(result, True)
        self.assertEqual(
            set(self._orders("TICKET-COMUN").config_id.ids), set(self.pos_configs.ids)
        )

    def test_cancelled_order_does_not_block_reimport(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        cancelled = self.wizard.parse_ticket(
            self._ticket_row(reference="TICKET-ANULADO"), session
        )
        cancelled.action_pos_order_cancel()
        self.assertEqual(cancelled.state, "cancel")

        result = self._import_tickets_without_invoice(
            self._ticket_csv("TICKET-ANULADO")
        )

        self.assertIs(result, True)
        self.assertEqual(len(self._orders("TICKET-ANULADO")), 2)

    def test_duplicate_detection_matches_unstripped_stored_reference(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        existing = self.wizard.parse_ticket(
            self._ticket_row(reference=" TICKET-ESPACIOS "), session
        )

        duplicates = self.wizard._find_already_imported_tickets(
            [(2, self._ticket_row(reference=" TICKET-ESPACIOS "))],
            {"TICKET-ESPACIOS": {self.pos_configs[0].name}},
            {self.pos_configs[0].name: self.pos_configs[0]},
        )

        self.assertEqual(duplicates, {"TICKET-ESPACIOS": existing.name})

    def test_find_duplicates_ignores_tickets_without_single_known_pos(self):
        duplicates = self.wizard._find_already_imported_tickets(
            [],
            {
                "TICKET-MIXTO": {"TPV A", "TPV B"},
                "TICKET-SIN-TPV": {"TPV inexistente"},
            },
            {"TPV inexistente": self.env["pos.config"]},
        )

        self.assertEqual(duplicates, {})

    def test_warning_truncates_duplicate_tickets(self):
        duplicate_tickets = {
            f"TICKET-{number:02d}": f"Pedido {number}" for number in range(21)
        }

        result = self.wizard._ticket_import_warning(
            {}, [], duplicate_tickets=duplicate_tickets
        )

        message = result["params"]["message"]
        self.assertIn("21 ticket(s) descartado(s)", message)
        self.assertIn("TICKET-19", message)
        self.assertNotIn("TICKET-20", message)
        self.assertIn("1 ticket(s) más ya importados", message)

    def _import_copies(self, csv_data, copies, invoice=True):
        """Import ``csv_data`` ``copies`` times, as the module used to allow."""
        with patch.object(
            type(self.wizard), "_find_already_imported_orders", return_value={}
        ):
            for _copy in range(copies):
                if invoice:
                    self.wizard._import_ticket(csv_data)
                else:
                    self._import_tickets_without_invoice(csv_data)

    def _use_cash_import_method(self):
        wizard_class = type(self.wizard)
        return patch.object(
            wizard_class,
            "_ensure_import_payment_method",
            autospec=True,
            side_effect=lambda wizard, config: (
                wizard._ensure_import_cash_payment_method(config)
            ),
        )

    def _assert_pos_receivable_reconciled(self, sessions):
        pos_account = self.env.company.account_default_pos_receivable_account_id
        lines = sessions.move_id.line_ids.filtered(
            lambda line: line.account_id == pos_account
        )
        self.assertTrue(lines)
        self.assertTrue(all(lines.mapped("reconciled")))

    def test_reimport_removes_bank_copies_of_closed_sessions(self):
        csv_data = self._ticket_csv("TICKET-TRIPLE")
        self._import_copies(csv_data, 3)
        copies = self._orders("TICKET-TRIPLE").sorted("id")
        self.assertEqual(len(copies), 3)
        kept, surplus = copies[0], copies[1:]
        surplus_invoices = surplus.account_move
        surplus_payment_moves = surplus.payment_ids.account_move_id
        surplus_sessions = surplus.session_id

        result = self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-TRIPLE"), kept)
        self.assertEqual(kept.account_move.payment_state, "paid")
        self.assertFalse(surplus.exists())
        self.assertFalse(surplus_invoices.exists())
        self.assertFalse(surplus_payment_moves.exists())
        adjustments = self.env["account.payment"].search([
            ("pos_session_id", "in", surplus_sessions.ids),
            ("payment_type", "=", "outbound"),
        ])
        self.assertEqual(len(adjustments), 2)
        self.assertEqual(adjustments.mapped("amount"), [kept.amount_total] * 2)
        self.assertFalse(adjustments.filtered(
            lambda payment: payment.state in ("draft", "canceled")
        ))
        self._assert_pos_receivable_reconciled(surplus_sessions)
        message = result["params"]["message"]
        self.assertIn(
            "2 copia(s) duplicada(s) eliminada(s) de 1 ticket(s)", message
        )
        self.assertIn(f"TICKET-TRIPLE ya importado (pedido {kept.name})", message)

    def test_reimport_removes_cash_copies_of_closed_sessions(self):
        csv_data = self._ticket_csv("TICKET-CAJA")
        with self._use_cash_import_method():
            self._import_copies(csv_data, 2)
        kept, surplus = self._orders("TICKET-CAJA").sorted("id")
        cash_journal = kept.payment_ids.payment_method_id.journal_id
        self.assertEqual(cash_journal.type, "cash")
        surplus_session = surplus.session_id

        self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-CAJA"), kept)
        adjustment = self.env["account.bank.statement.line"].search([
            ("pos_session_id", "=", surplus_session.id),
            ("amount", "<", 0),
        ])
        self.assertEqual(adjustment.journal_id, cash_journal)
        self.assertAlmostEqual(adjustment.amount, -kept.amount_total)
        session_lines = self.env["account.bank.statement.line"].search([
            ("pos_session_id", "in", (kept.session_id | surplus_session).ids),
        ])
        self.assertAlmostEqual(
            sum(session_lines.mapped("amount")), kept.amount_total
        )
        self._assert_pos_receivable_reconciled(surplus_session)

    def test_copy_in_closed_session_is_kept_over_older_open_copy(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        open_copy = self.wizard.parse_ticket(
            self._ticket_row(reference="TICKET-ABIERTA"), session
        )
        self.wizard._confirm_and_invoice_order(open_copy)
        open_invoice = open_copy.account_move
        csv_data = self._ticket_csv("TICKET-ABIERTA")
        self._import_copies(csv_data, 1)
        closed_copy = self._orders("TICKET-ABIERTA") - open_copy

        self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-ABIERTA"), closed_copy)
        self.assertFalse(open_invoice.exists())
        self.assertFalse(self.env["account.payment"].search([
            ("pos_session_id", "=", session.id),
        ]))
        self.assertEqual(session.state, "opened")

    def test_copy_outside_import_session_is_kept_over_import_copy(self):
        csv_data = self._ticket_csv("TICKET-REAL")
        self._import_copies(csv_data, 2)
        older_copy, import_copy = self._orders("TICKET-REAL").sorted("id")
        import_session = import_copy.session_id
        older_copy.session_id.name = "POS/2026/00001"

        self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-REAL"), older_copy)
        self.assertFalse(import_copy.exists())
        self._assert_pos_receivable_reconciled(import_session)

    def test_copies_outside_import_session_are_reported_not_removed(self):
        csv_data = self._ticket_csv("TICKET-TIENDA")
        self._import_copies(csv_data, 2)
        first, second = self._orders("TICKET-TIENDA").sorted("id")
        first.session_id.name = "POS/2026/00001"
        second.session_id.name = "POS/2026/00002"

        result = self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-TIENDA"), first | second)
        self.assertIn(
            f"Ticket TICKET-TIENDA: copia(s) {second.name} no eliminada(s)",
            result["params"]["message"],
        )
        self.assertNotIn(
            "copia(s) duplicada(s) eliminada(s)", result["params"]["message"]
        )

    def _import_dated_copies(self, reference, date, copies):
        row = self._ticket_row(reference=reference)
        row[5] = date
        csv_data = "\n".join((",".join(["cabecera"] * 19), ",".join(row)))
        self._import_copies(csv_data.encode(), copies)
        return csv_data.encode()

    def test_copies_from_cleanup_limit_are_reported_not_removed(self):
        csv_data = self._import_dated_copies("TICKET-AGOSTO", "01/08/2026", 2)
        first, second = self._orders("TICKET-AGOSTO").sorted("id")

        result = self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-AGOSTO"), first | second)
        self.assertIn(
            f"Ticket TICKET-AGOSTO: copia(s) {second.name} no eliminada(s)",
            result["params"]["message"],
        )

    def test_copies_before_cleanup_limit_are_removed(self):
        csv_data = self._import_dated_copies("TICKET-JULIO", "31/07/2026", 2)
        kept, surplus = self._orders("TICKET-JULIO").sorted("id")

        self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-JULIO"), kept)
        self.assertFalse(surplus.exists())

    def test_cleanup_limit_can_be_changed_by_system_parameter(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "gestool_import.duplicate_cleanup_before", "2026-09-01"
        )
        csv_data = self._import_dated_copies("TICKET-PARAM", "15/08/2026", 2)
        kept, surplus = self._orders("TICKET-PARAM").sorted("id")

        self.wizard._import_ticket(csv_data)

        self.assertEqual(self._orders("TICKET-PARAM"), kept)
        self.assertFalse(surplus.exists())

    def test_copy_with_different_total_is_reported_not_removed(self):
        csv_data = self._ticket_csv("TICKET-DISTINTO")
        self._import_copies(csv_data, 1, invoice=False)
        different_row = self._ticket_row(reference="TICKET-DISTINTO")
        different_row[16] = "20.00"
        self._import_copies(
            "\n".join((",".join(["cabecera"] * 19), ",".join(different_row))).encode(),
            1,
            invoice=False,
        )
        first, second = self._orders("TICKET-DISTINTO").sorted("id")

        result = self._import_tickets_without_invoice(csv_data)

        self.assertEqual(self._orders("TICKET-DISTINTO"), first | second)
        self.assertIn(
            f"Ticket TICKET-DISTINTO: copia(s) {second.name} no eliminada(s)",
            result["params"]["message"],
        )

    def test_uninvoiced_copy_of_closed_session_is_not_removed(self):
        csv_data = self._ticket_csv("TICKET-SIN-FACTURA")
        self._import_copies(csv_data, 2, invoice=False)
        copies = self._orders("TICKET-SIN-FACTURA")

        result = self._import_tickets_without_invoice(csv_data)

        self.assertEqual(self._orders("TICKET-SIN-FACTURA"), copies)
        message = result["params"]["message"]
        self.assertIn(
            "TICKET-SIN-FACTURA: no se pudieron eliminar sus copias", message
        )
        self.assertIn("no está facturado", message)
        self.assertNotIn("eliminada(s)", message)

    def test_failed_cleanup_is_rolled_back_per_session(self):
        csv_data = self._ticket_csv("TICKET-ERROR-LIMPIEZA", "TICKET-LIMPIO")
        self._import_copies(csv_data, 2)
        self.commit_mock.reset_mock()
        original_remove = type(self.wizard)._remove_session_duplicate_orders

        def remove_or_fail(wizard, session, orders):
            references = orders.mapped("pos_reference")
            original_remove(wizard, session, orders)
            if "TICKET-ERROR-LIMPIEZA" in references:
                raise UserError("Fallo al limpiar")

        with patch.object(
            type(self.wizard),
            "_remove_session_duplicate_orders",
            autospec=True,
            side_effect=remove_or_fail,
        ):
            result = self.wizard._import_ticket(csv_data)

        # Ambos tickets están en la misma sesión: se deshace la sesión entera.
        self.assertEqual(len(self._orders("TICKET-ERROR-LIMPIEZA")), 2)
        self.assertEqual(len(self._orders("TICKET-LIMPIO")), 2)
        self.assertIn("Fallo al limpiar", result["params"]["message"])
        self.commit_mock.assert_not_called()

    def test_payment_move_without_pos_line_is_rejected(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        order = self.wizard.parse_ticket(self._ticket_row(), session)
        self.wizard._confirm_and_invoice_order(order)

        with self.assertRaisesRegex(UserError, "línea de cobro TPV"):
            self.wizard._get_payment_move_pos_line(order.account_move)

    def test_adjustment_requires_payment_method_journal(self):
        session = self.wizard._create_import_session(self.pos_configs[0])
        pay_later = self.env["pos.payment.method"].create({
            "name": "Crédito Gestool",
            "company_id": self.env.company.id,
        })

        with self.assertRaisesRegex(UserError, "no tiene diario"):
            self.wizard._create_duplicate_adjustment(
                session,
                pay_later,
                self.env.company.account_default_pos_receivable_account_id,
                10.0,
            )

    def test_warning_truncates_duplicate_cleanup_details(self):
        tickets = [f"TICKET-{number:02d}" for number in range(21)]

        result = self.wizard._ticket_import_warning(
            {}, [],
            removed_copies=dict.fromkeys(tickets, 2),
            conflicting_copies={ticket: ["Pedido"] for ticket in tickets},
            cleanup_errors=dict.fromkeys(tickets, "error"),
        )

        message = result["params"]["message"]
        self.assertIn("42 copia(s) duplicada(s) eliminada(s) de 21", message)
        self.assertIn("1 ticket(s) más con copias distintas", message)
        self.assertIn("1 ticket(s) más cuyas copias no se pudieron eliminar", message)


class TestGestoolBarcodeImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard = cls.env["gestool.import"].create({})
        cls.template = cls.env["product.template"].create({
            "name": "Producto códigos Gestool",
            "default_code": "GESTOOL-BARCODE-001",
        })
        cls.product = cls.template.product_variant_id

    def test_normalize_excel_integer_without_losing_string_zeroes(self):
        self.assertEqual(
            self.wizard._normalize_import_value(155507.0),
            "155507",
        )
        self.assertEqual(
            self.wizard._normalize_import_value("00155507"),
            "00155507",
        )

    def test_parse_barcode_creates_and_ignores_duplicates(self):
        row = ["GESTOOL-BARCODE-001", "155507"]

        self.assertEqual(self.wizard.parse_multiple_barcodes(row), "created")
        self.assertEqual(self.wizard.parse_multiple_barcodes(row), "existing")
        self.assertEqual(
            self.env["product.barcode"].search_count([
                ("name", "=", "155507"),
                ("product_id", "=", self.product.id),
            ]),
            1,
        )

    def test_parse_barcode_ignores_code_assigned_to_another_product(self):
        other_template = self.env["product.template"].create({
            "name": "Otro producto Gestool",
            "default_code": "GESTOOL-BARCODE-002",
        })
        self.env["product.barcode"].create({
            "name": "999999",
            "product_id": other_template.product_variant_id.id,
            "product_tmpl_id": other_template.id,
        })

        self.assertEqual(
            self.wizard.parse_multiple_barcodes(
                ["GESTOOL-BARCODE-001", "999999"]
            ),
            "conflict",
        )
        self.assertFalse(self.product.barcode_ids.filtered(
            lambda barcode: barcode.name == "999999"
        ))
