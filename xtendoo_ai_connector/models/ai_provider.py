# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from abc import ABC, abstractmethod

_logger = logging.getLogger(__name__)

try:
    from google import genai as google_genai
    from google.genai import types as google_types
except ImportError:
    google_genai = None
    google_types = None

try:
    import openai as openai_lib
except ImportError:
    openai_lib = None

try:
    import anthropic as anthropic_lib
except ImportError:
    anthropic_lib = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def send_prompt(self, prompt: str, files: list = None) -> str:
        """
        Send a prompt to the AI provider.

        :param prompt: Text prompt to send.
        :param files: Optional list of dicts with keys:
                      - 'data': bytes content of the file
                      - 'mime_type': MIME type string (e.g. 'application/pdf', 'image/png')
        :returns: Text response from the AI.
        """

    @abstractmethod
    def list_models(self) -> list:
        """Return a list of available model name strings."""


class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model = model

    def send_prompt(self, prompt: str, files: list = None) -> str:
        if not google_genai:
            raise ImportError("google-genai library is not installed.")
        client = google_genai.Client(api_key=self._api_key)
        contents = [prompt]
        if files:
            for f in files:
                contents.append(
                    google_types.Part.from_bytes(
                        data=f["data"],
                        mime_type=f["mime_type"],
                    )
                )
        response = client.models.generate_content(
            model=self._model,
            contents=contents,
        )
        return response.text

    def list_models(self) -> list:
        if not google_genai:
            raise ImportError("google-genai library is not installed.")
        client = google_genai.Client(api_key=self._api_key)
        result = []
        try:
            for m in client.models.list():
                name = getattr(m, "name", "")
                if name.startswith("models/"):
                    name = name[len("models/"):]
                result.append(name)
        except Exception as exc:
            _logger.warning("Could not list Gemini models: %s", exc)
        return result


class OpenAIProvider(AIProvider):
    """OpenAI (ChatGPT) AI provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._api_key = api_key
        self._model = model

    def send_prompt(self, prompt: str, files: list = None) -> str:
        if not openai_lib:
            raise ImportError("openai library is not installed.")
        import base64
        client = openai_lib.OpenAI(api_key=self._api_key)
        messages_content = [{"type": "text", "text": prompt}]
        if files:
            for f in files:
                b64 = base64.b64encode(f["data"]).decode("utf-8")
                messages_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{f['mime_type']};base64,{b64}",
                        },
                    }
                )
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": messages_content}],
        )
        return response.choices[0].message.content

    def list_models(self) -> list:
        if not openai_lib:
            raise ImportError("openai library is not installed.")
        client = openai_lib.OpenAI(api_key=self._api_key)
        try:
            return [m.id for m in client.models.list().data]
        except Exception as exc:
            _logger.warning("Could not list OpenAI models: %s", exc)
            return []


class ClaudeProvider(AIProvider):
    """Anthropic Claude AI provider."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-5"):
        self._api_key = api_key
        self._model = model

    def send_prompt(self, prompt: str, files: list = None) -> str:
        if not anthropic_lib:
            raise ImportError("anthropic library is not installed.")
        import base64
        client = anthropic_lib.Anthropic(api_key=self._api_key)
        content = [{"type": "text", "text": prompt}]
        if files:
            for f in files:
                b64 = base64.b64encode(f["data"]).decode("utf-8")
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f["mime_type"],
                            "data": b64,
                        },
                    }
                )
        response = client.messages.create(
            model=self._model,
            max_tokens=8192,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text

    def list_models(self) -> list:
        return [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-3-5",
        ]


PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
}


def build_provider(provider_name: str, api_key: str, model: str) -> AIProvider:
    """
    Factory function to instantiate the correct AIProvider.

    :param provider_name: One of 'gemini', 'openai', 'claude'.
    :param api_key: API key string.
    :param model: Model identifier string.
    :returns: AIProvider instance.
    :raises ValueError: If the provider name is unknown.
    """
    cls = PROVIDER_CLASSES.get(provider_name)
    if not cls:
        raise ValueError(
            f"Unknown AI provider '{provider_name}'. "
            f"Supported providers: {list(PROVIDER_CLASSES.keys())}"
        )
    return cls(api_key=api_key, model=model)
