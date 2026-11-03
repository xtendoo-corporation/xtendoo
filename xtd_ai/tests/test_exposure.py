from odoo.tests import tagged

from ..agent.types import LLMRequest, Message, ToolResult, ToolSpec
from ..providers.anthropic_http import AnthropicHttpProvider
from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestToolExposure(XtdAiCase):
    """Tools of the areas of the request are loaded, the rest deferred (§6.5)."""

    def deferred(self, user, text, screen=None):
        conversation = self.env["xtd.ai.conversation"].with_user(user)
        run, _token = conversation._xtd_ai_start_run(text, screen=screen)
        run = run.sudo()
        tools = self.rpc(user, run, "tools/list", {})[1]["result"]["tools"]
        run.state = "done"
        return {t["name"]: t["annotations"]["xtdDeferred"] for t in tools}

    def test_core_tools_always_loaded(self):
        flags = self.deferred(self.user, "hola")
        for name in ("load_skill", "count_records", "open_record", "search_partners"):
            self.assertFalse(flags[name], name)
        self.assertTrue(flags["get_partner_summary"])
        self.assertTrue(flags["create_contact"])

    def test_words_of_the_message_select_the_area(self):
        flags = self.deferred(self.user, "Dame el resumen del Cliente Pérez")
        self.assertFalse(flags["get_partner_summary"])
        self.assertFalse(flags["create_contact"])

    def test_screen_selects_the_area(self):
        partner = self.env["res.partner"].create({"name": "Pantalla SA"})
        flags = self.deferred(
            self.user,
            "¿qué me dices de esto?",
            screen={"model": "res.partner", "view_type": "form", "res_id": partner.id},
        )
        self.assertFalse(flags["get_partner_summary"])

    def test_previous_message_keeps_the_area(self):
        self.deferred(self.user, "Busca el contacto Pérez")
        flags = self.deferred(self.user, "sí, ese")
        self.assertFalse(flags["get_partner_summary"])

    def test_admin_gets_the_same_selection(self):
        admin = self.env.ref("base.user_admin")
        admin.group_ids = [(4, self.env.ref("xtd_ai.group_xtd_ai_user").id)]
        for text in ("hola", "resumen del cliente Pérez"):
            mine = self.deferred(self.user, text)
            theirs = self.deferred(admin, text)
            common = set(mine) & set(theirs)
            self.assertTrue(common)
            self.assertEqual(
                {n: mine[n] for n in common}, {n: theirs[n] for n in common}, text
            )

    def test_exposure_all_loads_everything(self):
        self.env["ir.config_parameter"].sudo().set_param("xtd_ai.tool_exposure", "all")
        self.assertFalse(any(self.deferred(self.user, "hola").values()))

    def test_load_skill_returns_the_tools_of_the_area(self):
        run, _token = self.start_run()
        result = self.call(self.user, run, "load_skill", {"skill": "contactos"})
        loaded = result["_meta"]["xtd_ai/load_tools"]
        self.assertIn("get_partner_summary", loaded)
        self.assertIn("create_contact", loaded)
        self.assertEqual(
            loaded, result["structuredContent"]["data"]["tools"], "same list"
        )
        # a user without the right does not get the tool referenced
        run2, _token = self.start_run(self.user2)
        result = self.call(self.user2, run2, "load_skill", {"skill": "contactos"})
        self.assertNotIn("create_contact", result["_meta"]["xtd_ai/load_tools"])


@tagged("post_install", "-at_install")
class TestProviderDeferred(XtdAiCase):
    schema = {
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
        "additionalProperties": False,
    }

    def tools(self):
        return (
            ToolSpec("a_core", "", self.schema, read_only=True),
            ToolSpec("b_write", "", self.schema),
            ToolSpec("c_deferred", "", self.schema, deferred=True),
            ToolSpec("d_deferred", "", self.schema, read_only=True, deferred=True),
        )

    def test_defer_loading_and_cache_breakpoint(self):
        params = {p["name"]: p for p in AnthropicHttpProvider.tool_params(self.tools())}
        self.assertTrue(params["c_deferred"]["defer_loading"])
        self.assertTrue(params["d_deferred"]["defer_loading"])
        self.assertNotIn("defer_loading", params["a_core"])
        # the breakpoint goes on the last loaded tool, never on a deferred one
        self.assertEqual(
            [n for n, p in params.items() if "cache_control" in p], ["b_write"]
        )

    def test_strict_prefers_loaded_tools(self):
        params = AnthropicHttpProvider.tool_params(self.tools(), max_strict=2)
        self.assertEqual(
            {p["name"] for p in params if p.get("strict")}, {"a_core", "b_write"}
        )

    def test_all_deferred_loads_them(self):
        tools = (ToolSpec("x", "", self.schema, deferred=True),)
        params = AnthropicHttpProvider.tool_params(tools)
        self.assertNotIn("defer_loading", params[0])
        self.assertIn("cache_control", params[0])

    def test_load_skill_result_becomes_tool_references(self):
        provider = AnthropicHttpProvider(model="m", api_key="k")
        result = ToolResult(
            call_id="t1",
            content='{"status": "ok"}',
            load_tools=("c_deferred", "a_core", "unknown"),
        )
        request = LLMRequest(
            system="s",
            tools=self.tools(),
            messages=(
                Message(role="user", text="hola"),
                Message(role="assistant", text="", raw=[{"type": "text", "text": "x"}]),
                Message(role="user", tool_results=(result,)),
            ),
        )
        body = provider.build_request(request)
        blocks = body["messages"][-1]["content"]
        self.assertEqual(blocks[0]["type"], "tool_result")
        # only deferred tools of the request are referenced; no text in the result
        self.assertEqual(
            blocks[0]["content"],
            [{"type": "tool_reference", "tool_name": "c_deferred"}],
        )
        self.assertEqual(blocks[1]["type"], "text")
        self.assertIn('{"status": "ok"}', blocks[1]["text"])
        # nothing deferred to load: a plain result
        plain = ToolResult(call_id="t1", content="x", load_tools=("a_core",))
        request = LLMRequest(
            system="s",
            tools=self.tools(),
            messages=(Message(role="user", tool_results=(plain,)),),
        )
        block = provider.build_request(request)["messages"][-1]["content"][0]
        self.assertEqual(block["content"], "x")
