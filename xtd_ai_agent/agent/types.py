"""Provider-neutral types. This module must not import any SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class StopReason(StrEnum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    REFUSAL = "refusal"
    PAUSE_TURN = "pause_turn"
    OTHER = "other"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool = False  # from MCP annotations.readOnlyHint


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class AttachmentRef:
    """Metadata of a chat attachment, as listed by ``xtd_ai/history`` (no content)."""

    id: int
    name: str = ""
    mimetype: str = ""
    size: int = 0


@dataclass(frozen=True)
class Attachment:
    """A downloaded attachment, ready to be sent to the model."""

    id: int
    name: str
    mimetype: str
    data_base64: str = field(default="", repr=False)  # never printed or logged


@dataclass(frozen=True)
class Message:
    """A conversation turn.

    ``raw`` is an opaque payload owned by the provider adapter that produced the
    message (e.g. Anthropic content blocks incl. thinking blocks, which must be
    replayed unchanged). The loop never inspects it.
    """

    role: Literal["user", "assistant"]
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
    attachments: tuple[Attachment, ...] = ()  # user turns only
    raw: Any = None


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens


@dataclass(frozen=True)
class LLMRequest:
    system: str
    tools: tuple[ToolSpec, ...]
    messages: tuple[Message, ...]


@dataclass(frozen=True)
class LLMResponse:
    message: Message
    stop_reason: StopReason
    usage: Usage = field(default_factory=Usage)
    model: str = ""


@dataclass(frozen=True)
class ToolOutcome:
    """Result of an MCP tools/call."""

    text: str
    is_error: bool = False


@dataclass(frozen=True)
class HistoryMessage:
    role: Literal["user", "assistant"]
    text: str
    date: str = ""
    # Tools used in the run that produced this assistant message: ({"tool", "outcome"},
    # ...)
    tools_used: tuple[dict[str, Any], ...] = ()
    attachments: tuple[AttachmentRef, ...] = ()  # user messages only


def _attachment_refs(raw: Any) -> tuple[AttachmentRef, ...]:
    refs = []
    for a in raw if isinstance(raw, list) else []:
        if not isinstance(a, dict) or isinstance(a.get("id"), bool):
            continue
        if not isinstance(a.get("id"), int):
            continue
        size = a.get("size")
        refs.append(
            AttachmentRef(
                id=a["id"],
                name=str(a.get("name") or ""),
                mimetype=str(a.get("mimetype") or ""),
                size=size
                if isinstance(size, int) and not isinstance(size, bool)
                else 0,
            )
        )
    return tuple(refs)


@dataclass(frozen=True)
class History:
    user: dict[str, Any]
    company: dict[str, Any]
    allowed_companies: list[dict[str, Any]]
    today: str
    confirm_writes: bool
    messages: list[HistoryMessage]

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> History:
        msgs = [
            HistoryMessage(
                role=m["role"],
                text=m.get("text") or "",
                date=m.get("date") or "",
                tools_used=tuple(
                    t for t in (m.get("tools_used") or []) if isinstance(t, dict)
                ),
                attachments=_attachment_refs(m.get("attachments")),
            )
            for m in data.get("messages", [])
            if m.get("role") in ("user", "assistant")
        ]
        return cls(
            user=data.get("user") or {},
            company=data.get("company") or {},
            allowed_companies=data.get("allowed_companies") or [],
            today=data.get("today") or "",
            confirm_writes=bool(data.get("confirm_writes", True)),
            messages=msgs,
        )


@dataclass(frozen=True)
class Reply:
    text: str
    status: Literal["done", "failed"]
    error: str = ""
    usage: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": self.text,
            "status": self.status,
            "usage": self.usage,
        }
        if self.error:
            payload["error"] = self.error
        return payload
