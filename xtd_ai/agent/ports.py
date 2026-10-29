"""Protocols (ports) the domain depends on. Everything is synchronous."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import (
    Attachment,
    History,
    LLMRequest,
    LLMResponse,
    Reply,
    ToolOutcome,
    ToolSpec,
)


@runtime_checkable
class LLMProvider(Protocol):
    """A swappable LLM backend. Implement ``complete`` and expose identity.

    Must raise ``errors.ProviderError`` for provider failures (with a message safe
    to log). ``complete`` must keep ``raw`` payloads replayable.
    """

    name: str
    model: str

    def complete(self, request: LLMRequest) -> LLMResponse: ...


@runtime_checkable
class OdooGateway(Protocol):
    """In-process gateway toward the MCP handler (CONTRACT sections 4 and 15)."""

    def check_active(self) -> None:
        """Raise ``RunCancelled`` (or an auth error) if the run must stop."""

    def initialize(self) -> None: ...

    def history(self) -> History: ...

    def list_tools(self) -> list[ToolSpec]: ...

    def call_tool(self, name: str, arguments: dict) -> ToolOutcome: ...

    def post_reply(self, reply: Reply) -> None: ...

    def get_attachment(self, attachment_id: int) -> Attachment: ...
