"""Neutral error types shared by the domain and its adapters."""

from __future__ import annotations


class AgentError(Exception):
    """Base class for expected errors."""


class OdooError(AgentError):
    """Error talking to the Odoo gateway (CONTRACT section 4.2)."""

    code: int | None = None

    def __init__(self, message: str = "", *, code: int | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code


class OdooAuthError(OdooError):
    """401 / -32001: the run is not authorised any more."""

    code = -32001


class OdooForbiddenError(OdooError):
    """403 / -32003: company not allowed or other checks."""

    code = -32003


class RunCancelled(OdooError):
    """409 / -32004: run cancelled, finished or tool-call cap exceeded."""

    code = -32004


class OdooMethodNotFound(OdooError):
    """-32601: unknown method or tool not visible to the user."""

    code = -32601


class OdooInvalidParams(OdooError):
    """-32602: malformed params."""

    code = -32602


class OdooServerError(OdooError):
    """Unexpected failure or malformed response."""


class ProviderError(AgentError):
    """LLM provider failure. The message is safe to log (no bodies, no keys)."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ProviderNotConfigured(AgentError):
    """The selected provider cannot be built (e.g. no API key)."""
