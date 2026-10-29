import ast
import pathlib

from odoo.tests import BaseCase, tagged

from ..agent.pricing import DEFAULT_PRICES, estimate_cost, parse_price_table
from ..agent.prompts import load_system_prompt
from ..agent.types import Usage

AGENT = pathlib.Path(__file__).resolve().parents[1] / "agent"
FORBIDDEN = {"odoo", "requests", "anthropic", "httpx", "werkzeug", "psycopg2"}


@tagged("post_install", "-at_install")
class TestAgentDomain(BaseCase):
    def test_agent_package_imports_no_odoo_or_http(self):
        offenders = []
        for path in AGENT.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif (
                    isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
                ):
                    names = [node.module]
                offenders += [
                    (path.name, n) for n in names if n.split(".")[0] in FORBIDDEN
                ]
        self.assertEqual(offenders, [])

    def test_system_prompt_loaded(self):
        prompt = load_system_prompt()
        self.assertTrue(prompt.startswith("Eres el asistente de XTD"))
        self.assertIn("Reglas fijas", prompt)

    def test_sonnet_with_cache(self):
        u = Usage(1_000_000, 1_000_000, 1_000_000, 1_000_000)
        # 2 + 10 + 0.2 + 2*1.25
        self.assertEqual(estimate_cost(DEFAULT_PRICES, "claude-sonnet-5-5", u), 14.7)

    def test_unknown_model_zero_and_dated_suffix(self):
        self.assertEqual(estimate_cost(DEFAULT_PRICES, "otro", Usage(10, 10)), 0.0)
        self.assertEqual(
            estimate_cost(
                DEFAULT_PRICES, "claude-haiku-5-5-20260101", Usage(1_000_000, 0)
            ),
            0.1,
        )

    def test_parse_price_table(self):
        prices = parse_price_table({"x": {"input": 1, "output": 2, "cache_read": 0.5}})
        self.assertEqual(estimate_cost(prices, "x", Usage(1_000_000, 1_000_000)), 3.0)
        for bad in (
            {"x": {"input": 1}},
            {"x": "no"},
            {"x": {"input": "a", "output": 1}},
        ):
            with self.assertRaises(ValueError):
                parse_price_table(bad)
