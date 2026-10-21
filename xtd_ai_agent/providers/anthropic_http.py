"""Anthropic Messages API over ``requests`` (no SDK).

Same rules as the external service adapter:

- ``tool_choice`` is left at its default (auto).
- Tools use ``strict: true`` within the API limits (20 tools, 24 optional params);
  tools are ordered by name and the last one carries ``cache_control``.
- The system prompt is one stable block with ``cache_control``; the variable
  context travels in the first user turn, so tools+system stay cacheable.
- A rolling breakpoint on the last block of the last user turn (3 of 4
  breakpoints at most).
- ``thinking`` is omitted (adaptive by default). Content blocks of an assistant
  turn are replayed unchanged through ``Message.raw``.
- Errors carry only the status and request id; the message of a 400 is added
  only when ``log_error_details`` is on. Never the request body or the key.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ..agent.errors import ProviderError
from ..agent.types import (
    Attachment,
    LLMRequest,
    LLMResponse,
    Message,
    StopReason,
    ToolCall,
    ToolResult,
    ToolSpec,
    Usage,
)

log = logging.getLogger(__name__)


def _logger_debug_ignored_retry_after():
    log.debug("ignoring a malformed retry-after header")


API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
RETRY_STATUSES = frozenset({408, 409, 429})
MAX_RETRY_DELAY = 8.0

_STOP = {
    "end_turn": StopReason.END_TURN,
    "stop_sequence": StopReason.END_TURN,
    "tool_use": StopReason.TOOL_USE,
    "max_tokens": StopReason.MAX_TOKENS,
    "refusal": StopReason.REFUSAL,
    "pause_turn": StopReason.PAUSE_TURN,
}
_EPHEMERAL = {"type": "ephemeral"}
MAX_STRICT_TOOLS = 20
MAX_STRICT_OPTIONAL_PARAMS = 24  # API limit across all strict tools of a request


class AnthropicHttpProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        effort: str = "low",
        max_tokens: int = 16000,
        timeout: float = 30.0,
        max_retries: int = 2,
        workspace_id: str | None = None,
        log_error_details: bool = False,
        url: str = API_URL,
        session: requests.Session | None = None,
        sleep=time.sleep,
    ):
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.workspace_id = workspace_id or None
        self.log_error_details = log_error_details
        self.url = url
        self._api_key = api_key
        self._session = session or requests.Session()
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"AnthropicHttpProvider(model={self.model!r}, api_key=***)"

    # ------------------------------------------------------------ request mapping

    @staticmethod
    def tool_params(tools: tuple[ToolSpec, ...]) -> list[dict[str, Any]]:
        # The API accepts at most MAX_STRICT_TOOLS strict tools: strict goes to the
        # write tools first (schema-valid arguments matter most there). Every
        # argument is validated again by the Odoo gateway in any case.
        ordered = sorted(tools, key=lambda t: t.name)
        strict_names: set[str] = set()
        optional_budget = MAX_STRICT_OPTIONAL_PARAMS
        for t in sorted(ordered, key=lambda t: t.read_only):  # write tools first
            cost = count_optional_params(t.input_schema)
            if len(strict_names) < MAX_STRICT_TOOLS and cost <= optional_budget:
                strict_names.add(t.name)
                optional_budget -= cost
        params = []
        for t in ordered:
            param: dict[str, Any] = {"name": t.name, "description": t.description}
            if t.name in strict_names:
                param["input_schema"] = strict_schema(t.input_schema)
                param["strict"] = True
            else:
                param["input_schema"] = t.input_schema
            params.append(param)
        if params:
            params[-1]["cache_control"] = _EPHEMERAL.copy()
        return params

    @staticmethod
    def message_params(messages: tuple[Message, ...]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "assistant":
                content: Any = m.raw if m.raw is not None else _assistant_blocks(m)
                blocks = (
                    list(content)
                    if not isinstance(content, str)
                    else [{"type": "text", "text": content}]
                )
            else:
                blocks = _user_blocks(m)
            if not blocks:
                continue
            if out and out[-1]["role"] == m.role:
                out[-1]["content"].extend(blocks)  # merge consecutive same-role turns
            else:
                out.append({"role": m.role, "content": blocks})
        # rolling breakpoint on the last block when the last turn is a user turn
        if len(out) > 1 and out[-1]["role"] == "user":
            last = out[-1]["content"][-1]
            if isinstance(last, dict):
                out[-1]["content"][-1] = {**last, "cache_control": _EPHEMERAL.copy()}
        return out

    def build_request(self, request: LLMRequest) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": [
                {
                    "type": "text",
                    "text": request.system,
                    "cache_control": _EPHEMERAL.copy(),
                }
            ],
            "tools": self.tool_params(request.tools),
            "messages": self.message_params(request.messages),
            "output_config": {"effort": self.effort},
        }

    def _headers(self) -> dict[str, str]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        if self.workspace_id:
            headers["anthropic-workspace-id"] = self.workspace_id
        return headers

    # ----------------------------------------------------------------- completion

    def complete(self, request: LLMRequest) -> LLMResponse:
        params = self.build_request(request)
        if not params["tools"]:
            params.pop("tools")
        return self.parse_response(self._post(params))

    def _post(self, params: dict[str, Any]) -> dict[str, Any]:
        """POST with retries on 408/409/429/5xx and network failures."""
        attempt = 0
        while True:
            try:
                resp = self._session.post(
                    self.url,
                    json=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                # type name only: exception messages may carry URLs or headers
                if attempt < self.max_retries:
                    self._backoff(attempt)
                    attempt += 1
                    continue
                raise ProviderError(
                    f"anthropic connection error: {type(exc).__name__}",
                    retryable=True,
                ) from None
            status = resp.status_code
            if 200 <= status < 300:
                try:
                    return resp.json()
                except ValueError:
                    raise ProviderError("anthropic malformed response") from None
            if (status in RETRY_STATUSES or status >= 500) and (
                attempt < self.max_retries
            ):
                self._backoff(attempt, resp.headers.get("retry-after"))
                attempt += 1
                continue
            raise self._status_error(resp) from None

    def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        delay = 0.5 * (2**attempt)
        try:
            if retry_after is not None:
                delay = max(delay, float(retry_after))
        except ValueError:
            _logger_debug_ignored_retry_after()
        self._sleep(min(delay, MAX_RETRY_DELAY))

    def _status_error(self, resp: Any) -> ProviderError:
        # status and request id only. The API message of a 400 may echo prompt
        # content, so it is added only when explicitly enabled for diagnosis.
        rid = resp.headers.get("request-id") or resp.headers.get("x-request-id")
        detail = ""
        if self.log_error_details and resp.status_code == 400:
            try:
                body = resp.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                message = str((body.get("error") or {}).get("message") or "")
                detail = f" message={message[:200]!r}"
        return ProviderError(
            f"anthropic http {resp.status_code} request_id={rid}{detail}",
            retryable=resp.status_code >= 500 or resp.status_code == 429,
        )

    def parse_response(self, resp: dict[str, Any]) -> LLMResponse:
        content = resp.get("content") or []
        texts: list[str] = []
        calls: list[ToolCall] = []
        for block in content:
            if block.get("type") == "text":
                texts.append(block.get("text") or "")
            elif block.get("type") == "tool_use":
                calls.append(
                    ToolCall(
                        id=block["id"],
                        name=block["name"],
                        arguments=dict(block.get("input") or {}),
                    )
                )
        stop = _STOP.get(resp.get("stop_reason") or "", StopReason.OTHER)
        if stop == StopReason.REFUSAL:
            details = resp.get("stop_details") or {}
            log.warning(
                "model_refusal category=%s model=%s",
                details.get("category") if isinstance(details, dict) else None,
                resp.get("model"),
            )
        u = resp.get("usage") or {}
        usage = Usage(
            input_tokens=u.get("input_tokens") or 0,
            output_tokens=u.get("output_tokens") or 0,
            cache_read_tokens=u.get("cache_read_input_tokens") or 0,
            cache_write_tokens=u.get("cache_creation_input_tokens") or 0,
        )
        message = Message(
            role="assistant",
            text="\n".join(texts),
            tool_calls=tuple(calls),
            raw=list(content),  # includes thinking blocks: replay unchanged
        )
        return LLMResponse(
            message=message,
            stop_reason=stop,
            usage=usage,
            model=resp.get("model") or self.model,
        )


# Keywords that strict tool use rejects. The Odoo gateway still enforces them
# server-side, so they are only moved into the description as a hint.
_UNSUPPORTED = {
    "minimum": "mín. {}",
    "maximum": "máx. {}",
    "exclusiveMinimum": "mayor que {}",
    "exclusiveMaximum": "menor que {}",
    "multipleOf": "múltiplo de {}",
    "minLength": "mín. {} caracteres",
    "maxLength": "máx. {} caracteres",
    "minItems": "mín. {} elementos",
    "maxItems": "máx. {} elementos",
}


def count_optional_params(schema: Any) -> int:
    """Optional object properties in ``schema``, nested ones included."""
    if isinstance(schema, list):
        return sum(count_optional_params(s) for s in schema)
    if not isinstance(schema, dict):
        return 0
    total = 0
    props = schema.get("properties")
    if isinstance(props, dict):
        required = set(schema.get("required") or ())
        total += sum(1 for name in props if name not in required)
        total += sum(count_optional_params(sub) for sub in props.values())
    for key in ("items", "anyOf", "allOf", "$defs"):
        if key in schema:
            sub = schema[key]
            total += count_optional_params(
                list(sub.values()) if key == "$defs" else sub
            )
    return total


def strict_schema(schema: Any) -> Any:
    """Return a copy of ``schema`` without keywords unsupported by ``strict: true``."""
    if isinstance(schema, list):
        return [strict_schema(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    hints: list[str] = []
    for key, value in schema.items():
        if key in _UNSUPPORTED and not isinstance(value, dict):
            if key == "minItems" and value in (0, 1):
                out[key] = value  # the only array bound strict mode accepts
            else:
                hints.append(_UNSUPPORTED[key].format(value))
        elif key in ("properties", "$defs"):
            out[key] = {name: strict_schema(sub) for name, sub in value.items()}
        else:
            out[key] = strict_schema(value)
    if hints:
        note = f"({', '.join(hints)})"
        out["description"] = (
            f"{out['description']} {note}" if out.get("description") else note
        )
    return out


def _assistant_blocks(m: Message) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if m.text:
        blocks.append({"type": "text", "text": m.text})
    for c in m.tool_calls:
        blocks.append(
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
        )
    return blocks


def _tool_result_block(r: ToolResult) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": r.call_id,
        "content": r.content,
    }
    if r.is_error:
        block["is_error"] = True
    return block


_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def _attachment_block(a: Attachment) -> dict[str, Any] | None:
    """``document`` block for PDFs, ``image`` block for images; None otherwise."""
    if a.mimetype == "application/pdf":
        kind = "document"
    elif a.mimetype in _IMAGE_TYPES:
        kind = "image"
    else:
        return None
    return {
        "type": kind,
        "source": {"type": "base64", "media_type": a.mimetype, "data": a.data_base64},
    }


def _user_blocks(m: Message) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        _tool_result_block(r) for r in m.tool_results
    ]  # results first
    # documents and images go BEFORE the text of the turn (API guidance)
    blocks.extend(b for a in m.attachments if (b := _attachment_block(a)))
    if m.text:
        blocks.append({"type": "text", "text": m.text})
    return blocks
