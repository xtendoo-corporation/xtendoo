from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError
from odoo.addons.xtd_ai.tools.unlock import GRANT_KEY, UNLOCK_KEY

from .common import XtdAiAccountCase


@tagged("post_install", "-at_install")
class TestGuardContext(XtdAiAccountCase):
    """Riesgo 13: las guardas del ORM dependen del contexto ``xtd_ai_run``.

    Con la marca activa, publicar, pagar y borrar facturas siguen bloqueados
    también al ejecutar una tarjeta confirmada y aunque el contexto traiga
    claves de desbloqueo falsificadas. Sin la marca, la barrera de fondo son
    las ACL del usuario (ANALISIS_PERMISOS §2)."""

    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run(self.biller)
        self.move = self.make_move(
            "out_invoice", self.customer, 100, "2026-07-31", post=False
        )

    def blocked_ops(self, env):
        """Publicar, pagar y borrar en ``env``: cada una debe lanzar la guarda."""
        move = env["account.move"].browse(self.move.id)
        return {
            "action_post": move.action_post,
            "_post": move._post,
            "action_register_payment": move.action_register_payment,
            "unlink": move.unlink,
            "payment_create": lambda: env["account.payment"].create(
                {"partner_id": self.customer.id, "amount": 1.0}
            ),
        }

    def test_forged_unlock_keys_do_not_lift_accounting_guards(self):
        env = self.tool_env(self.biller, self.run)
        forged = env(
            context=dict(
                env.context,
                **{
                    GRANT_KEY: ("*.action_post", "*._post", "*.unlink"),
                    UNLOCK_KEY: (
                        ("account.move.action_post", "account.move.unlink"),
                        self.move.id,
                    ),
                },
            )
        )
        for name, op in self.blocked_ops(forged).items():
            with self.assertRaises(XtdAiDraftOnlyError, msg=name):
                op()
        self.assertEqual(self.move.state, "draft")
        self.assertTrue(self.move.exists())

    def test_confirmed_card_runs_under_the_guards(self):
        # una tarjeta confirmada por el usuario (con derechos de facturación)
        # ejecuta la herramienta con xtd_ai_run: si su código intentara publicar,
        # pagar o borrar, la guarda lo para y la tarjeta queda fallida
        self.set_confirm(self.biller, True)
        toolbox = self.env["xtd.ai.toolbox"]
        tool = toolbox._xtd_ai_tools()["zz_test_draft"]
        model_cls = type(self.env[tool["model"]])
        for index, name in enumerate(self.blocked_ops(self.env)):
            structured = self.agent_call(
                self.biller, self.run, "zz_test_draft", {"name": f"guard-{index}"}
            )
            self.assertEqual(structured["status"], "pending_confirmation", structured)
            action = (
                self.env["xtd.ai.pending_action"]
                .with_user(self.biller)
                .browse(structured["pending_action_id"])
            )

            def body(toolbox_self, args, op_name=name):
                self.assertTrue(toolbox_self.env.context.get("xtd_ai_run"))
                self.blocked_ops(toolbox_self.env)[op_name]()
                return {"data": {}, "records": []}

            with patch.object(model_cls, tool["attr"], body):
                result = action.action_confirm()
            self.assertEqual(result["state"], "failed", name)
        self.assertEqual(
            self.audits(self.run, event="guard_blocked").mapped("outcome"),
            ["denied"] * len(self.blocked_ops(self.env)),
        )
        self.assertEqual(self.move.state, "draft")
        self.assertTrue(self.move.exists())
        self.assertFalse(
            self.env["account.payment"].search([("partner_id", "=", self.customer.id)])
        )

    def test_acl_is_the_barrier_without_the_run_context(self):
        # sin la marca no hay guardas: un usuario del agente sin derechos de
        # contabilidad tampoco puede publicar, pagar ni borrar
        env = self.env(
            user=self.nobody.id, context={"allowed_company_ids": self.company.ids}
        )
        self.assertFalse(env.context.get("xtd_ai_run"))
        for name, op in self.blocked_ops(env).items():
            with self.assertRaises(AccessError, msg=name):
                op()
        self.assertEqual(self.move.state, "draft")
        self.assertTrue(self.move.exists())
