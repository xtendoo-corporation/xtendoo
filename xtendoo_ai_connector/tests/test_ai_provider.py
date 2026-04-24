# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

from odoo.addons.xtendoo_ai_connector.models.ai_provider import (
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    build_provider,
)


class TestAIProviderFactory(TransactionCase):
    """Test the build_provider factory function."""

    def test_build_gemini_provider(self):
        provider = build_provider("gemini", "fake-key", "gemini-2.5-flash")
        self.assertIsInstance(provider, GeminiProvider)

    def test_build_openai_provider(self):
        provider = build_provider("openai", "fake-key", "gpt-4o")
        self.assertIsInstance(provider, OpenAIProvider)

    def test_build_claude_provider(self):
        provider = build_provider("claude", "fake-key", "claude-opus-4-5")
        self.assertIsInstance(provider, ClaudeProvider)

    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            build_provider("unknown_provider", "fake-key", "some-model")


class TestGeminiProvider(TransactionCase):
    """Test GeminiProvider with mocked google-genai library."""

    def _make_provider(self):
        return GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai"
    )
    def test_send_prompt_text_only(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = '{"result": "ok"}'
        mock_client.models.generate_content.return_value = mock_response

        provider = self._make_provider()
        result = provider.send_prompt("Hello AI")

        self.assertEqual(result, '{"result": "ok"}')
        mock_client.models.generate_content.assert_called_once()

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai"
    )
    def test_send_prompt_with_file(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_types = MagicMock()

        with patch(
            "odoo.addons.xtendoo_ai_connector.models.ai_provider.google_types",
            mock_types,
        ):
            mock_response = MagicMock()
            mock_response.text = "response text"
            mock_client.models.generate_content.return_value = mock_response

            provider = self._make_provider()
            result = provider.send_prompt(
                "Analyze this",
                files=[{"data": b"fake-pdf", "mime_type": "application/pdf"}],
            )

        self.assertEqual(result, "response text")

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai",
        None,
    )
    def test_send_prompt_missing_library_raises(self):
        provider = self._make_provider()
        with self.assertRaises(ImportError):
            provider.send_prompt("Hello")

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai"
    )
    def test_list_models(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        m1 = MagicMock()
        m1.name = "models/gemini-2.5-flash"
        m2 = MagicMock()
        m2.name = "models/gemini-2.5-pro"
        mock_client.models.list.return_value = [m1, m2]

        provider = self._make_provider()
        models = provider.list_models()

        self.assertIn("gemini-2.5-flash", models)
        self.assertIn("gemini-2.5-pro", models)


class TestOpenAIProvider(TransactionCase):
    """Test OpenAIProvider with mocked openai library."""

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.openai_lib"
    )
    def test_send_prompt(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "AI response"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        provider = OpenAIProvider(api_key="fake-key", model="gpt-4o")
        result = provider.send_prompt("Hello OpenAI")

        self.assertEqual(result, "AI response")

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.openai_lib",
        None,
    )
    def test_send_prompt_missing_library_raises(self):
        provider = OpenAIProvider(api_key="fake-key", model="gpt-4o")
        with self.assertRaises(ImportError):
            provider.send_prompt("Hello")


class TestClaudeProvider(TransactionCase):
    """Test ClaudeProvider with mocked anthropic library."""

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.anthropic_lib"
    )
    def test_send_prompt(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_content = MagicMock()
        mock_content.text = "Claude response"
        mock_client.messages.create.return_value = MagicMock(
            content=[mock_content]
        )

        provider = ClaudeProvider(api_key="fake-key", model="claude-opus-4-5")
        result = provider.send_prompt("Hello Claude")

        self.assertEqual(result, "Claude response")

    def test_list_models_returns_known_models(self):
        provider = ClaudeProvider(api_key="fake-key", model="claude-opus-4-5")
        models = provider.list_models()
        self.assertIn("claude-opus-4-5", models)
        self.assertIn("claude-sonnet-4-5", models)

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.anthropic_lib",
        None,
    )
    def test_send_prompt_missing_library_raises(self):
        provider = ClaudeProvider(api_key="fake-key", model="claude-opus-4-5")
        with self.assertRaises(ImportError):
            provider.send_prompt("Hello")


class TestAIConnectorMixin(TransactionCase):
    """Test the AIConnectorMixin helper via res.config.settings."""

    def _set_params(self, provider="gemini", api_key="test-key", model="gemini-2.5-flash"):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("xtendoo_ai_connector.ai_provider", provider)
        ICP.set_param("xtendoo_ai_connector.ai_api_key", api_key)
        ICP.set_param("xtendoo_ai_connector.ai_model", model)

    def test_get_ai_provider_raises_without_api_key(self):
        self._set_params(api_key="")
        mixin = self.env["xtendoo.ai.connector.mixin"]
        with self.assertRaises(UserError):
            mixin._get_ai_provider()

    def test_get_ai_provider_returns_gemini_instance(self):
        self._set_params(provider="gemini", api_key="fake-key")
        mixin = self.env["xtendoo.ai.connector.mixin"]
        provider = mixin._get_ai_provider()
        self.assertIsInstance(provider, GeminiProvider)

    def test_get_ai_provider_raises_for_unknown_provider(self):
        self._set_params(provider="unknown_provider", api_key="fake-key")
        mixin = self.env["xtendoo.ai.connector.mixin"]
        with self.assertRaises(UserError):
            mixin._get_ai_provider()

    def test_action_test_ai_connection_no_key_raises(self):
        settings = self.env["res.config.settings"].create({})
        settings.ai_provider = "gemini"
        settings.ai_api_key = ""
        settings.ai_model = "gemini-2.5-flash"
        with self.assertRaises(UserError):
            settings.action_test_ai_connection()

    def test_get_ai_provider_returns_openai_instance(self):
        self._set_params(provider="openai", api_key="k", model="gpt-4o")
        mixin = self.env["xtendoo.ai.connector.mixin"]
        provider = mixin._get_ai_provider()
        self.assertIsInstance(provider, OpenAIProvider)

    def test_get_ai_provider_returns_claude_instance(self):
        self._set_params(provider="claude", api_key="k", model="claude-opus-4-5")
        mixin = self.env["xtendoo.ai.connector.mixin"]
        provider = mixin._get_ai_provider()
        self.assertIsInstance(provider, ClaudeProvider)

    def test_get_ai_provider_model_passed_correctly(self):
        self._set_params(provider="gemini", api_key="k", model="gemini-2.5-pro")
        provider = self.env["xtendoo.ai.connector.mixin"]._get_ai_provider()
        self.assertEqual(provider._model, "gemini-2.5-pro")


class TestGeminiProviderExtended(TransactionCase):
    """Extended tests for GeminiProvider covering all branches."""

    def _make_provider(self):
        return GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_types")
    def test_send_prompt_with_multiple_files(self, mock_types, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = MagicMock(text="ok")

        provider = self._make_provider()
        provider.send_prompt(
            "Analyze",
            files=[
                {"data": b"file1", "mime_type": "image/png"},
                {"data": b"file2", "mime_type": "image/jpeg"},
            ],
        )

        self.assertEqual(mock_types.Part.from_bytes.call_count, 2)

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_list_models_strips_models_prefix(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        m1, m2 = MagicMock(), MagicMock()
        m1.name = "models/gemini-2.5-flash"
        m2.name = "models/gemini-2.5-pro"
        mock_client.models.list.return_value = [m1, m2]

        result = self._make_provider().list_models()

        self.assertIn("gemini-2.5-flash", result)
        self.assertIn("gemini-2.5-pro", result)
        self.assertNotIn("models/gemini-2.5-flash", result)

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_list_models_returns_empty_on_exception(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.list.side_effect = Exception("network error")

        result = self._make_provider().list_models()
        self.assertEqual(result, [])

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_list_models_missing_library_raises(self, _mock_genai):
        import odoo.addons.xtendoo_ai_connector.models.ai_provider as mod
        original = mod.google_genai
        mod.google_genai = None
        try:
            with self.assertRaises(ImportError):
                self._make_provider().list_models()
        finally:
            mod.google_genai = original

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_uses_correct_model_name(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = MagicMock(text="x")

        GeminiProvider(api_key="k", model="gemini-2.5-pro").send_prompt("Hello")

        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs.get("model"), "gemini-2.5-pro")


class TestOpenAIProviderExtended(TransactionCase):
    """Extended tests for OpenAIProvider."""

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.openai_lib")
    def test_send_prompt_with_file_uses_base64_image_url(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )

        provider = OpenAIProvider(api_key="k", model="gpt-4o")
        provider.send_prompt(
            "Analyze",
            files=[{"data": b"img", "mime_type": "image/png"}],
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        content = messages[0]["content"]
        types_ = [c["type"] for c in content]
        self.assertIn("text", types_)
        self.assertIn("image_url", types_)

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.openai_lib")
    def test_list_models_returns_ids(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        m1, m2 = MagicMock(), MagicMock()
        m1.id = "gpt-4o"
        m2.id = "gpt-4o-mini"
        mock_client.models.list.return_value = MagicMock(data=[m1, m2])

        result = OpenAIProvider(api_key="k", model="gpt-4o").list_models()
        self.assertIn("gpt-4o", result)
        self.assertIn("gpt-4o-mini", result)

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.openai_lib")
    def test_list_models_returns_empty_on_exception(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.models.list.side_effect = Exception("api error")

        result = OpenAIProvider(api_key="k", model="gpt-4o").list_models()
        self.assertEqual(result, [])

    @patch(
        "odoo.addons.xtendoo_ai_connector.models.ai_provider.openai_lib", None
    )
    def test_list_models_missing_library_raises(self):
        with self.assertRaises(ImportError):
            OpenAIProvider(api_key="k", model="gpt-4o").list_models()


class TestClaudeProviderExtended(TransactionCase):
    """Extended tests for ClaudeProvider."""

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.anthropic_lib")
    def test_send_prompt_with_file_encodes_base64(self, mock_anthropic):
        import base64

        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="ok")]
        )

        provider = ClaudeProvider(api_key="k", model="claude-opus-4-5")
        provider.send_prompt(
            "Analyze",
            files=[{"data": b"img-bytes", "mime_type": "image/jpeg"}],
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        content = messages[0]["content"]
        image_items = [c for c in content if c.get("type") == "image"]
        self.assertEqual(len(image_items), 1)
        self.assertEqual(image_items[0]["source"]["media_type"], "image/jpeg")
        self.assertEqual(
            image_items[0]["source"]["data"],
            base64.b64encode(b"img-bytes").decode(),
        )

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.anthropic_lib")
    def test_send_prompt_max_tokens_is_8192(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="x")]
        )

        ClaudeProvider(api_key="k", model="claude-opus-4-5").send_prompt("Hello")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs.get("max_tokens"), 8192)


class TestResConfigSettingsAIExtended(TransactionCase):
    """Extended tests for res.config.settings AI connection."""

    def _settings(self, provider="gemini", api_key="k", model="gemini-2.5-flash"):
        s = self.env["res.config.settings"].create({})
        s.ai_provider = provider
        s.ai_api_key = api_key
        s.ai_model = model
        return s

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_action_test_connection_success_with_models(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        m = MagicMock()
        m.name = "models/gemini-2.5-flash"
        mock_client.models.list.return_value = [m]

        result = self._settings().action_test_ai_connection()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_action_test_connection_no_models_still_success(self, mock_genai):
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.list.side_effect = Exception("no models")

        result = self._settings().action_test_ai_connection()

        self.assertEqual(result["params"]["type"], "success")

    @patch("odoo.addons.xtendoo_ai_connector.models.ai_provider.google_genai")
    def test_action_test_connection_api_error_raises_userror(self, mock_genai):
        mock_genai.Client.side_effect = Exception("invalid key")

        with self.assertRaises(UserError):
            self._settings().action_test_ai_connection()

    def test_action_test_missing_library_raises_userror(self):
        import odoo.addons.xtendoo_ai_connector.models.ai_provider as mod
        original = mod.openai_lib
        mod.openai_lib = None
        try:
            with self.assertRaises(UserError):
                self._settings(provider="openai").action_test_ai_connection()
        finally:
            mod.openai_lib = original
