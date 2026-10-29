"""Provider adapters and factory. To add a provider: implement ``LLMProvider``
(see ``agent/ports.py``) in a new module and register it in ``build_provider``."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agent.errors import ProviderNotConfigured
from ..agent.ports import LLMProvider

PROVIDERS = ("anthropic", "fake")


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "anthropic"
    model: str = "claude-haiku-5-5"
    effort: str = "low"
    timeout: float = 30.0
    max_tokens: int = 16000
    workspace_id: str = ""
    log_error_details: bool = False
    api_key: str = field(default="", repr=False)  # never printed
    fake_script: str = ""


def build_provider(settings: ProviderSettings) -> LLMProvider:
    if settings.provider == "fake":
        from .fake import FakeProvider

        if not settings.fake_script:
            raise ProviderNotConfigured("fake provider needs a script")
        return FakeProvider.from_file(settings.fake_script, model=settings.model)
    if settings.provider == "anthropic":
        if not settings.api_key:
            raise ProviderNotConfigured("anthropic api key not configured")
        from .anthropic_http import AnthropicHttpProvider

        return AnthropicHttpProvider(
            model=settings.model,
            api_key=settings.api_key,
            effort=settings.effort,
            max_tokens=settings.max_tokens,
            timeout=settings.timeout,
            workspace_id=settings.workspace_id,
            log_error_details=settings.log_error_details,
        )
    raise ProviderNotConfigured(f"unknown provider {settings.provider!r}")
