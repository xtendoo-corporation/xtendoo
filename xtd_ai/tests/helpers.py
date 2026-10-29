import base64
import json
import logging
from contextlib import contextmanager

from ..agent.loop import AgentLoop
from ..agent.pricing import DEFAULT_PRICES
from ..agent.types import (
    Attachment,
    History,
    Reply,
    ToolOutcome,
    ToolSpec,
)

HISTORY_PAYLOAD = {
    "user": {"name": "Ana", "lang": "es_ES", "tz": "Europe/Madrid"},
    "company": {"id": 1, "name": "Xtendoo Demo SL", "currency": "EUR"},
    "allowed_companies": [{"id": 1, "name": "Xtendoo Demo SL"}],
    "today": "2026-10-20",
    "confirm_writes": True,
    "messages": [
        {
            "role": "user",
            "text": "Cuántos presupuestos hay?",
            "date": "2026-10-20 10:00:00",
        }
    ],
}

TOOLS = [
    ToolSpec(
        "search_partners",
        "Busca clientes",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
    ),
    ToolSpec(
        "get_user_context",
        "Contexto",
        {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {},
        },
    ),
]

PDF_B64 = base64.b64encode(b"%PDF-1.4 fake pdf body SECRET-CONTENT").decode()
PNG_B64 = base64.b64encode(b"\x89PNG fake image SECRET-CONTENT").decode()


def ok(data):
    return ToolOutcome(text=json.dumps({"status": "ok", "data": data}), is_error=False)


class FakeGateway:
    """In-memory OdooGateway. ``tool_handler(name, args)`` returns a ToolOutcome."""

    def __init__(self, history=None, tools=None, tool_handler=None):
        self._history = History.from_payload(history or HISTORY_PAYLOAD)
        self._tools = tools if tools is not None else TOOLS.copy()
        self.tool_handler = tool_handler or (lambda name, args: ok({"echo": name}))
        self.calls = []
        self.replies = []
        self.initialized = False
        self.fail_on = {}
        self.attachments = {}
        self.fetched = []
        self.checks = 0

    def _maybe_fail(self, what):
        exc = self.fail_on.get(what)
        if exc:
            raise exc

    def check_active(self):
        self.checks += 1
        self._maybe_fail("check_active")

    def initialize(self):
        self._maybe_fail("initialize")
        self.initialized = True

    def history(self):
        self._maybe_fail("history")
        return self._history

    def list_tools(self):
        self._maybe_fail("list_tools")
        return list(self._tools)

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.tool_handler(name, arguments)

    def post_reply(self, reply: Reply):
        self._maybe_fail("post_reply")
        self.replies.append(reply)

    def get_attachment(self, attachment_id):
        self.fetched.append(attachment_id)
        self._maybe_fail("get_attachment")
        return self.attachments[attachment_id]


def make_loop(provider, gateway, **kw):
    kw.setdefault("post_retry_delay", 0)
    return AgentLoop(provider, gateway, "SYSTEM", prices=DEFAULT_PRICES, **kw)


def gateway_with_attachments(messages):
    g = FakeGateway(history=HISTORY_PAYLOAD | {"messages": messages})
    g.attachments = {
        12: Attachment(12, "factura.pdf", "application/pdf", PDF_B64),
        13: Attachment(13, "foto.png", "image/png", PNG_B64),
        7: Attachment(7, "vieja.pdf", "application/pdf", PDF_B64),
    }
    return g


class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def text(self):
        return "\n".join(
            r.getMessage() + json.dumps(getattr(r, "fields", {}), default=str)
            for r in self.records
        )


@contextmanager
def capture_logs(name="odoo.addons.xtd_ai"):
    handler = LogCapture()
    logger = logging.getLogger(name)
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
