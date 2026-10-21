import json
from unittest.mock import patch

import requests

from odoo.tests import BaseCase, tagged

from ..agent.errors import ProviderError
from ..agent.types import (
    Attachment,
    LLMRequest,
    Message,
    StopReason,
    ToolResult,
    ToolSpec,
)
from ..providers import ProviderSettings, build_provider
from ..providers.anthropic_http import (
    AnthropicHttpProvider,
    count_optional_params,
    strict_schema,
)
from .helpers import PDF_B64, PNG_B64, TOOLS, capture_logs

KEY = "sk-ant-api03-SUPERSECRETKEY"


def message_json(content, stop="end_turn", usage=None, **extra):
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": content,
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": usage
        or {
            "input_tokens": 100,
            "output_tokens": 20,
            "cache_read_input_tokens": 400,
            "cache_creation_input_tokens": 50,
        },
    } | extra


class FakeResponse:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self._body = body
        self.headers = headers or {"request-id": "req_123"}

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def request(messages=None):
    msgs = messages or (
        Message(role="user", text="CTX"),
        Message(role="user", text="hola"),
    )
    return LLMRequest(
        system="SISTEMA", tools=tuple(reversed(TOOLS)), messages=tuple(msgs)
    )


class HttpMock:
    """Patch ``requests.Session.post`` with a scripted list of responses."""

    def __init__(self, items):
        self.items = list(items)
        self.calls = []  # (url, kwargs)

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, dict):
            return FakeResponse(200, item)
        return item

    @property
    def bodies(self):
        return [kw["json"] for _u, kw in self.calls]


class ProviderCase(BaseCase):
    def provider(self, items, **kw):
        self.sleeps = []
        kw.setdefault("sleep", self.sleeps.append)
        kw.setdefault("model", "claude-haiku-5-5")
        kw.setdefault("api_key", KEY)
        self.http = HttpMock(items)
        patcher = patch.object(requests.Session, "post", self.http)
        patcher.start()
        self.addCleanup(patcher.stop)
        return AnthropicHttpProvider(**kw)


@tagged("post_install", "-at_install")
class TestAnthropicHttp(ProviderCase):
    def test_request_mapping_strict_cache_effort(self):
        resp = self.provider(
            [message_json([{"type": "text", "text": "Hola"}])]
        ).complete(request())
        url = self.http.calls[0][0]
        body = self.http.bodies[0]
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(body["model"], "claude-haiku-5-5")
        self.assertEqual(body["output_config"], {"effort": "low"})
        self.assertNotIn("thinking", body)
        self.assertNotIn("tool_choice", body)
        names = [t["name"] for t in body["tools"]]
        self.assertEqual(names, sorted(names))
        self.assertTrue(all(t["strict"] is True for t in body["tools"]))
        self.assertEqual(["cache_control" in t for t in body["tools"]], [False, True])
        self.assertEqual(
            body["system"],
            [
                {
                    "type": "text",
                    "text": "SISTEMA",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        )
        self.assertEqual(len(body["messages"]), 1)
        self.assertEqual(
            [b["text"] for b in body["messages"][0]["content"]], ["CTX", "hola"]
        )
        self.assertEqual(resp.message.text, "Hola")
        self.assertEqual(resp.stop_reason, StopReason.END_TURN)

    def test_headers(self):
        p = self.provider([message_json([{"type": "text", "text": "x"}])])
        p.complete(request())
        headers = self.http.calls[0][1]["headers"]
        self.assertEqual(headers["x-api-key"], KEY)
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        self.assertNotIn("anthropic-workspace-id", headers)
        self.assertEqual(self.http.calls[0][1]["timeout"], 30.0)

    def test_workspace_header_only_when_configured(self):
        p = self.provider(
            [message_json([{"type": "text", "text": "x"}])], workspace_id="wrkspc_1"
        )
        p.complete(request())
        self.assertEqual(
            self.http.calls[0][1]["headers"]["anthropic-workspace-id"], "wrkspc_1"
        )

    def test_timeout_is_passed(self):
        p = self.provider([message_json([{"type": "text", "text": "x"}])], timeout=12)
        p.complete(request())
        self.assertEqual(self.http.calls[0][1]["timeout"], 12)

    def test_usage_mapping_includes_cache_tokens(self):
        p = self.provider([message_json([{"type": "text", "text": "x"}])])
        u = p.complete(request()).usage
        self.assertEqual(
            (
                u.input_tokens,
                u.output_tokens,
                u.cache_read_tokens,
                u.cache_write_tokens,
            ),
            (100, 20, 400, 50),
        )

    def test_tool_use_roundtrip_and_replay_with_thinking(self):
        first = message_json(
            [
                {"type": "thinking", "thinking": "", "signature": "SIG123"},
                {"type": "text", "text": "Busco"},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "search_partners",
                    "input": {"query": "deco"},
                },
                {
                    "type": "tool_use",
                    "id": "toolu_2",
                    "name": "get_user_context",
                    "input": {},
                },
            ],
            stop="tool_use",
        )
        p = self.provider([first, message_json([{"type": "text", "text": "fin"}])])
        r1 = p.complete(request())
        self.assertEqual(r1.stop_reason, StopReason.TOOL_USE)
        self.assertEqual(
            [(c.id, c.name, c.arguments) for c in r1.message.tool_calls],
            [
                ("toolu_1", "search_partners", {"query": "deco"}),
                ("toolu_2", "get_user_context", {}),
            ],
        )
        results = Message(
            role="user",
            tool_results=(
                ToolResult("toolu_1", '{"status":"ok"}'),
                ToolResult("toolu_2", '{"status":"error"}', True),
            ),
        )
        p.complete(
            request(
                (
                    Message(role="user", text="CTX"),
                    Message(role="user", text="hola"),
                    r1.message,
                    results,
                )
            )
        )
        msgs = self.http.bodies[1]["messages"]
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
        self.assertEqual(msgs[1]["content"][0]["type"], "thinking")
        self.assertEqual(msgs[1]["content"][0]["signature"], "SIG123")
        tr = msgs[2]["content"]
        self.assertEqual([b["tool_use_id"] for b in tr], ["toolu_1", "toolu_2"])
        self.assertNotIn("is_error", tr[0])
        self.assertTrue(tr[1]["is_error"])
        self.assertEqual(tr[-1]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(
            ["cache_control" in t for t in self.http.bodies[1]["tools"]], [False, True]
        )

    def test_refusal_and_stop_reason_mapping(self):
        body = message_json(
            [],
            stop="refusal",
            stop_details={"type": "refusal", "category": "cyber", "explanation": "x"},
        )
        p = self.provider([body])
        r = p.complete(request())
        self.assertEqual(r.stop_reason, StopReason.REFUSAL)
        self.assertEqual(r.message.text, "")
        for raw, expected in (
            ("max_tokens", StopReason.MAX_TOKENS),
            ("pause_turn", StopReason.PAUSE_TURN),
            ("stop_sequence", StopReason.END_TURN),
            ("weird", StopReason.OTHER),
        ):
            p = self.provider([message_json([{"type": "text", "text": "x"}], stop=raw)])
            self.assertEqual(p.complete(request()).stop_reason, expected, raw)

    def test_no_tools_omits_tools_param(self):
        p = self.provider([message_json([{"type": "text", "text": "x"}])])
        p.complete(
            LLMRequest(
                system="S", tools=(), messages=(Message(role="user", text="hi"),)
            )
        )
        self.assertNotIn("tools", self.http.bodies[0])

    # -- errors ------------------------------------------------------------
    def test_400_becomes_provider_error_without_body(self):
        err = FakeResponse(
            400,
            {"error": {"type": "invalid_request_error", "message": "PROMPT LEAK"}},
        )
        p = self.provider([err])
        with self.assertRaises(ProviderError) as cm:
            p.complete(request())
        message = str(cm.exception)
        self.assertNotIn("LEAK", message)
        self.assertIn("400", message)
        self.assertIn("req_123", message)
        self.assertFalse(cm.exception.retryable)
        self.assertEqual(len(self.http.calls), 1)  # 400 is not retried

    def test_400_detail_only_when_flag_is_on(self):
        err = {"error": {"type": "invalid_request_error", "message": "TOO MANY TOOLS"}}
        p = self.provider([FakeResponse(400, err)], log_error_details=True)
        with self.assertRaises(ProviderError) as cm:
            p.complete(request())
        self.assertIn("TOO MANY TOOLS", str(cm.exception))
        # the flag never adds the detail of other statuses
        p = self.provider([FakeResponse(401, err)], log_error_details=True)
        with self.assertRaises(ProviderError) as cm:
            p.complete(request())
        self.assertNotIn("TOO MANY", str(cm.exception))

    def test_retries_on_5xx_and_429_with_backoff(self):
        ok_body = message_json([{"type": "text", "text": "ya"}])
        p = self.provider([FakeResponse(529, {}), FakeResponse(429, {}), ok_body])
        self.assertEqual(p.complete(request()).message.text, "ya")
        self.assertEqual(len(self.http.calls), 3)
        self.assertEqual(self.sleeps, [0.5, 1.0])

    def test_retry_after_header_is_honoured_and_capped(self):
        ok_body = message_json([{"type": "text", "text": "ya"}])
        p = self.provider(
            [FakeResponse(429, {}, {"retry-after": "3"}), ok_body],
        )
        p.complete(request())
        self.assertEqual(self.sleeps, [3.0])
        p = self.provider([FakeResponse(429, {}, {"retry-after": "999"}), ok_body])
        p.complete(request())
        self.assertEqual(self.sleeps, [8.0])

    def test_gives_up_after_two_retries_and_is_retryable(self):
        p = self.provider([FakeResponse(503, {}) for _i in range(3)])
        with self.assertRaises(ProviderError) as cm:
            p.complete(request())
        self.assertTrue(cm.exception.retryable)
        self.assertEqual(len(self.http.calls), 3)

    def test_retries_408_and_409_but_not_404(self):
        ok_body = message_json([{"type": "text", "text": "ya"}])
        p = self.provider([FakeResponse(408, {}), FakeResponse(409, {}), ok_body])
        p.complete(request())
        self.assertEqual(len(self.http.calls), 3)
        p = self.provider([FakeResponse(404, {})])
        with self.assertRaises(ProviderError):
            p.complete(request())
        self.assertEqual(len(self.http.calls), 1)

    def test_timeout_and_connection_errors_retry_then_fail(self):
        ok_body = message_json([{"type": "text", "text": "ya"}])
        p = self.provider([requests.Timeout("slow https://x?key=" + KEY), ok_body])
        self.assertEqual(p.complete(request()).message.text, "ya")
        p = self.provider([requests.ConnectionError("boom " + KEY) for _i in range(3)])
        with self.assertRaises(ProviderError) as cm:
            p.complete(request())
        self.assertTrue(cm.exception.retryable)
        self.assertIn("ConnectionError", str(cm.exception))
        self.assertNotIn(KEY, str(cm.exception))
        self.assertIsNone(cm.exception.__cause__)

    def test_malformed_response(self):
        p = self.provider([FakeResponse(200, None)])
        with self.assertRaises(ProviderError):
            p.complete(request())

    # -- secrets -----------------------------------------------------------
    def test_key_not_in_repr_or_logs(self):
        p = self.provider([FakeResponse(500, {}) for _i in range(3)])
        self.assertNotIn(KEY, repr(p))
        self.assertNotIn(KEY, str(p))
        settings = ProviderSettings(api_key=KEY)
        self.assertNotIn(KEY, repr(settings))
        with capture_logs() as logs, self.assertRaises(ProviderError) as cm:
            p.complete(request())
        self.assertNotIn(KEY, logs.text())
        self.assertNotIn(KEY, str(cm.exception))

    def test_attachment_blocks_before_text_and_cache_last(self):
        p = self.provider([message_json([{"type": "text", "text": "ok"}])])
        msgs = (
            Message(role="user", text="CTX"),
            Message(role="assistant", text="antes"),
            Message(
                role="user",
                text="[Adjunto: f.pdf (id 12)]\ncrea",
                attachments=(
                    Attachment(12, "f.pdf", "application/pdf", PDF_B64),
                    Attachment(13, "p.png", "image/png", PNG_B64),
                    Attachment(14, "x.txt", "text/plain", "eA=="),
                ),
            ),
        )
        p.complete(LLMRequest(system="S", tools=(), messages=msgs))
        body = self.http.bodies[0]
        blocks = body["messages"][-1]["content"]
        self.assertEqual([b["type"] for b in blocks], ["document", "image", "text"])
        self.assertEqual(
            blocks[0]["source"],
            {"type": "base64", "media_type": "application/pdf", "data": PDF_B64},
        )
        self.assertEqual(blocks[1]["source"]["media_type"], "image/png")
        self.assertEqual(blocks[-1]["cache_control"], {"type": "ephemeral"})
        self.assertNotIn("cache_control", blocks[0])
        self.assertEqual(body["system"][0]["cache_control"], {"type": "ephemeral"})

    def test_factory(self):
        with self.assertRaises(Exception) as cm:
            build_provider(ProviderSettings(provider="anthropic", api_key=""))
        self.assertEqual(type(cm.exception).__name__, "ProviderNotConfigured")
        p = build_provider(
            ProviderSettings(
                api_key=KEY, timeout=12, model="m", effort="high", workspace_id="w"
            )
        )
        self.assertEqual(
            (p.timeout, p.model, p.effort, p.workspace_id), (12, "m", "high", "w")
        )


@tagged("post_install", "-at_install")
class TestStrictSchema(BaseCase):
    def test_strict_schema_strips_unsupported_constraints(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["query", "lines"],
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 100,
                    "description": "Texto",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                "date": {"type": "string", "format": "date"},
                "lines": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["qty"],
                        "properties": {"qty": {"type": "number", "minimum": 0}},
                    },
                },
            },
        }
        out = strict_schema(schema)
        blob = json.dumps(out)
        for key in ("minLength", "maxLength", "minimum", "maximum", "maxItems"):
            self.assertNotIn(f'"{key}"', blob)
        props = out["properties"]
        self.assertEqual(
            props["query"]["description"],
            "Texto (mín. 2 caracteres, máx. 100 caracteres)",
        )
        self.assertEqual(props["limit"]["description"], "(mín. 1, máx. 200)")
        self.assertEqual(props["date"]["format"], "date")
        self.assertEqual(props["lines"]["minItems"], 1)
        self.assertEqual(
            props["lines"]["items"]["properties"]["qty"]["description"], "(mín. 0)"
        )
        self.assertEqual(schema["properties"]["query"]["minLength"], 2)  # not mutated

    def test_strict_limited_to_20_and_writes_first(self):
        schema = {
            "type": "object",
            "properties": {"q": {"type": "string", "maxLength": 5}},
            "required": [],
            "additionalProperties": False,
        }
        tools = tuple(
            ToolSpec(
                name=f"read_{i:02d}",
                description="r",
                input_schema=schema,
                read_only=True,
            )
            for i in range(22)
        )
        tools += tuple(
            ToolSpec(name=f"write_{i}", description="w", input_schema=schema)
            for i in range(6)
        )
        params = AnthropicHttpProvider.tool_params(tools)
        strict = [p["name"] for p in params if p.get("strict")]
        self.assertEqual(len(strict), 20)
        for i in range(6):
            self.assertIn(f"write_{i}", strict)
        names = [p["name"] for p in params]
        self.assertEqual(names, sorted(names))
        loose = next(p for p in params if not p.get("strict"))
        self.assertEqual(loose["input_schema"]["properties"]["q"]["maxLength"], 5)

    def test_strict_respects_optional_parameter_budget(self):
        def schema(n_optional):
            props = {f"o{i}": {"type": "string"} for i in range(n_optional)}
            props["req"] = {"type": "string"}
            return {
                "type": "object",
                "properties": props,
                "required": ["req"],
                "additionalProperties": False,
            }

        self.assertEqual(count_optional_params(schema(3)), 3)
        nested = {
            "type": "object",
            "required": ["lines"],
            "additionalProperties": False,
            "properties": {"lines": {"type": "array", "items": schema(2)}},
        }
        self.assertEqual(count_optional_params(nested), 2)
        tools = (
            ToolSpec(name="w_a", description="", input_schema=schema(10)),
            ToolSpec(name="w_b", description="", input_schema=schema(10)),
            ToolSpec(name="w_c", description="", input_schema=schema(10)),
            ToolSpec(
                name="r_a", description="", input_schema=schema(4), read_only=True
            ),
        )
        params = {p["name"]: p for p in AnthropicHttpProvider.tool_params(tools)}
        strict = {n for n, p in params.items() if p.get("strict")}
        self.assertEqual(strict, {"w_a", "w_b", "r_a"})
