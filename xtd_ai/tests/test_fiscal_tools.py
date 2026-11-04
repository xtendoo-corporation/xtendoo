import re
from unittest.mock import patch

from odoo.tests import tagged

from ..models.xtd_ai_policy import FIXED_CLASSES, POLICY_TABLE
from .common import XtdAiCase

# Documentos fiscales: los que Veri*Factu, SII o TicketBAI declaran o afectan.
FISCAL_MODELS = frozenset(
    {"account.move", "account.move.line", "hr.expense", "hr.expense.sheet"}
)
# Métodos que publican, validan o sacan de borrador un documento fiscal.
FISCAL_METHODS = frozenset(
    {
        "action_post",
        "_post",
        "button_draft",
        "button_cancel",
        "action_reverse",
        "action_send_and_print",
        "action_invoice_sent",
        "action_process_edi_web_services",
    }
)
# Nombres de herramienta que dicen publicar o validar un documento fiscal.
FISCAL_NAME_RE = re.compile(
    r"(?:post|publish|validate|contabiliz|publica|valida|emit|emite)\w*_"
    r"(?:\w+_)?(?:invoice|bill|refund|move|entry|factura|asiento|abono)s?\b"
)


def publishes_fiscal_documents(tool):
    """Criterio del freno fiscal (``xtd.ai.policy._xtd_ai_tool_brakes``): una
    herramienta que publica o valida un documento fiscal lo tiene que
    desbloquear (``unlocks``, §6.5: dentro de ``xtd_ai_run`` las guardas lo
    impiden) o lo anuncia en su nombre."""
    for op in tool.get("unlocks") or ():
        model, _dot, method = op.rpartition(".")
        if method in FISCAL_METHODS and (model in FISCAL_MODELS or model == "*"):
            return True
    return bool(FISCAL_NAME_RE.search(tool["name"]))


@tagged("post_install", "-at_install")
class TestFiscalTools(XtdAiCase):
    """Riesgo 5: el freno fiscal solo actúa sobre ``op_class="post"`` (y las
    transiciones o envíos de la skill de contabilidad). Si alguien registra una
    herramienta que publica facturas sin declararlo, el freno quedaría mudo:
    este test lo impide."""

    def test_detector(self):
        # el criterio reconoce lo que debe (si no, el test de abajo no prueba nada)
        for tool in (
            {"name": "post_invoice"},
            {"name": "validate_vendor_bill"},
            {"name": "publish_journal_entry"},
            {"name": "contabilizar_factura"},
            {"name": "x", "unlocks": ("account.move.action_post",)},
            {"name": "x", "unlocks": ("account.move._post",)},
            {"name": "x", "unlocks": ("*.action_post",)},
            {"name": "x", "unlocks": ("hr.expense.action_post",)},
        ):
            self.assertTrue(publishes_fiscal_documents(tool), tool)
        for tool in (
            {"name": "create_customer_invoice"},
            {"name": "get_journal_entry"},
            {"name": "validate_picking"},
            {"name": "send_payment_reminder"},
            {"name": "x", "unlocks": ("account.move.send_email",)},
            {"name": "x", "unlocks": ("sale.order.action_confirm",)},
        ):
            self.assertFalse(publishes_fiscal_documents(tool), tool)

    def test_tools_that_publish_fiscal_documents_declare_post(self):
        tools = self.env["xtd.ai.toolbox"]._xtd_ai_tools()
        self.assertTrue(tools)
        offenders = sorted(
            name
            for name, tool in tools.items()
            if publishes_fiscal_documents(tool) and tool.get("op_class") != "post"
        )
        self.assertFalse(
            offenders,
            "Herramientas que publican o validan documentos fiscales sin "
            "op_class='post' (el freno de Veri*Factu/SII no las vería): "
            f"{offenders}",
        )

    def test_post_is_never_relaxed_and_brakes_with_fiscal_reporting(self):
        self.assertIn("post", FIXED_CLASSES)
        self.assertEqual(set(POLICY_TABLE["post"]), {"N3"})
        policy = self.env["xtd.ai.policy"]
        company_cls = type(self.env["res.company"])
        with patch.object(
            company_cls, "_xtd_ai_has_fiscal_reporting", return_value=True
        ):
            # cualquier skill: publicar es N3 con el freno activo
            for skill in ("contabilidad", "ventas", None):
                tool = {"name": "x", "op_class": "post", "skill": skill}
                self.assertEqual(policy._xtd_ai_tool_brakes(tool, "N1"), "N3")
