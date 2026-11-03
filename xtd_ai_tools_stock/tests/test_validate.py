from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS, XtdAiCase
from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


@tagged("post_install", "-at_install")
class TestValidatePicking(XtdAiCase):
    """Wave 2B: validate a complete receipt or delivery (§4 Inventario)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.keeper = new_test_user(
            cls.env, "xtd_ai_keeper2b", groups=AI_GROUPS + ",stock.group_stock_user"
        )
        cls.nobody = new_test_user(cls.env, "xtd_ai_nobody_st", groups=AI_GROUPS)
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente Stock SL", "email": "stock@cliente.example"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Caja Omega", "type": "consu", "is_storable": True}
        )
        cls.tracked = cls.env["product.product"].create(
            {
                "name": "Motor con serie",
                "type": "consu",
                "is_storable": True,
                "tracking": "serial",
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )

    def setUp(self):
        super().setUp()
        self.set_confirm(self.keeper, False)
        self.set_policy("validate_picking", "N2")

    def picking(self, kind="in", qty=5, product=None):
        ptype = (
            self.warehouse.in_type_id if kind == "in" else self.warehouse.out_type_id
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": ptype.id,
                "partner_id": self.partner.id,
                "location_id": ptype.default_location_src_id.id
                or self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": ptype.default_location_dest_id.id
                or self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": (product or self.product).id,
                            "product_uom_qty": qty,
                            "location_id": ptype.default_location_src_id.id
                            or self.env.ref("stock.stock_location_suppliers").id,
                            "location_dest_id": ptype.default_location_dest_id.id
                            or self.env.ref("stock.stock_location_customers").id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        return picking

    def sc(self, args, user=None):
        user = user or self.keeper
        runs = self.__dict__.setdefault("_runs", {})
        if user.id not in runs:
            runs[user.id] = self.start_run(user)[0]
        return self.call(user, runs[user.id], "validate_picking", args)[
            "structuredContent"
        ]

    def confirm(self, res):
        self.assertEqual(res["status"], "pending_confirmation", res)
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        return action, action.with_user(self.keeper).action_confirm()

    def test_receipt_card_and_validate(self):
        receipt = self.picking("in")
        self.assertEqual(receipt.state, "assigned")
        res = self.sc({"picking": str(receipt.id)})
        action, out = self.confirm(res)
        self.assertTrue(action.preview["irreversible"])
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(receipt.state, "done")
        self.assertEqual(self.product.qty_available, 5)

    def test_off_by_default_opens_the_transfer(self):
        self.set_policy("validate_picking", False)
        receipt = self.picking("in")
        res = self.sc({"picking": str(receipt.id)})
        self.assertEqual(res["status"], "handoff", res)
        self.assertEqual(res["data"]["button"], "Validar")
        self.assertEqual(receipt.state, "assigned")

    def test_partial_transfer_refused_without_backorder(self):
        receipt = self.picking("in", qty=5)
        receipt.move_ids.quantity = 3
        res = self.sc({"picking": str(receipt.id)})
        self.assertEqual(res["error"]["code"], "needs_user", res)
        self.assertEqual(receipt.state, "assigned")
        self.assertFalse(receipt.backorder_ids)

    def test_tracked_products_refused(self):
        receipt = self.picking("in", product=self.tracked, qty=1)
        res = self.sc({"picking": str(receipt.id)})
        self.assertEqual(res["error"]["code"], "needs_user", res)

    def test_delivery_with_confirmation_email_is_shown_and_sent(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 10
        )
        self.company.stock_move_email_validation = True
        delivery = self.picking("out", qty=2)
        self.assertEqual(delivery.state, "assigned")
        res = self.sc({"picking": str(delivery.id)})
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        self.assertTrue(
            any(
                "stock@cliente.example" in line["value"]
                for line in action.preview["lines"]
            ),
            action.preview,
        )
        _action, out = self.confirm(res)
        self.assertEqual(out["state"], "confirmed", out)
        self.assertEqual(delivery.state, "done")

    def test_unlock_only_its_transfer(self):
        one, two = self.picking("in"), self.picking("in")
        run, _t = self.start_run(self.keeper)
        env = self.tool_env(self.keeper, run)
        key = {
            "xtd_ai_grant": ("stock.picking.button_validate",),
            "xtd_ai_unlock": ("stock.picking.button_validate", one.id),
        }
        with self.assertRaises(XtdAiDraftOnlyError):
            env["stock.picking"].browse(two.id).with_context(**key).button_validate()
        with self.assertRaises(XtdAiDraftOnlyError):
            env["stock.picking"].browse(one.id).with_context(**key).unlink()
        self.assertEqual((one | two).mapped("state"), ["assigned", "assigned"])

    def test_without_stock_rights_not_offered(self):
        run, _t = self.start_run(self.nobody)
        _status, response = self.rpc(self.nobody, run, "tools/list", {})
        names = {t["name"] for t in response["result"]["tools"]}
        self.assertNotIn("validate_picking", names)
