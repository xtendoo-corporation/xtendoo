"""Unit tests for the MCP tools helper layer and gate primitives.

TransactionCase coverage the HttpCase suites only reach indirectly:

* ``tools/smart_fields`` field-importance scoring and the sensitive-name
  blocklist (the LLM-data-leak guard) -- pairs with the get_record /
  search_records sensitive-field stripping.
* ``tools/formatters`` value rendering (numeric, datetime, selection, boolean,
  truncation) and ``tools/uri_schema`` build/parse round-trips + error paths.
* ``call_model_method``'s ``_validate_method_call`` boundary for the
  self-elevating action/cron models plus the ``run`` / ``method_direct_trigger``
  method-name backstop.
"""

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import common, tagged

from ..models import mcp_tools_read
from ..tools import smart_fields
from ..tools.formatters import DatasetFormatter, RecordFormatter
from ..tools.uri_schema import (
    URIParseError,
    build_attachment_uri,
    build_field_uri,
    parse_attachment_uri,
    parse_field_uri,
)


@tagged("much_unit", "post_install", "-at_install")
class TestSmartFields(common.TransactionCase):
    """Field-importance scoring + sensitive-name blocklist (LLM leak guard)."""

    def test_sensitive_named_fields_score_zero(self):
        """A credential-named field scores 0 and is flagged sensitive."""
        for name in (
            "password",
            "user_password",
            "api_key",
            "openai_api_key",
            "webhook_secret",
            "client_secret",
            "access_token",
            "refresh_token",
            "private_key",
            "auth_token",
            "session_token",
            "secret_key",
            "stripe_secret_key",
        ):
            self.assertEqual(
                smart_fields.score_field_importance(name, {"type": "char"}), 0, name
            )
            self.assertTrue(smart_fields.is_sensitive_field_name(name), name)

    def test_benign_lookalike_fields_not_sensitive(self):
        """Names that merely contain a marker substring are NOT flagged.

        The blocklist matches whole ``_``-delimited segments, so a relational
        reference (``token_id``), a boolean flag (``is_secret``), an unrelated
        word (``secretary_id``, ``sort_key``) and a metadata descriptor that
        pushes the marker off the final segment (``password_expiry_date``,
        ``access_token_expiry``) are honored rather than silently stripped.
        """
        for name in (
            "secretary_id",
            "secretariat_id",
            "is_secret",
            "token_id",
            "sort_key",
            "password_expiry_date",
            "access_token_expiry",
        ):
            self.assertFalse(smart_fields.is_sensitive_field_name(name), name)

    def test_sensitive_fields_excluded_from_smart_defaults(self):
        """A sensitive-named field never enters the smart default selection."""
        fields_info = {
            "id": {"type": "integer"},
            "name": {"type": "char"},
            "openai_api_key": {"type": "char", "store": True},
        }
        selected = smart_fields.get_smart_default_fields(fields_info)
        self.assertIn("name", selected)
        self.assertNotIn("openai_api_key", selected)

    def test_large_and_x2many_field_types_excluded(self):
        """binary/image/html and one2many/many2many types score 0."""
        for ftype in ("binary", "image", "html", "one2many", "many2many"):
            self.assertEqual(
                smart_fields.score_field_importance("some_field", {"type": ftype}),
                0,
                ftype,
            )

    def test_non_stored_field_score_capped(self):
        """A non-stored (computed/related) field is capped at 30."""
        score = smart_fields.score_field_importance(
            "amount_total", {"type": "float", "store": False, "required": True}
        )
        self.assertLessEqual(score, 30)

    def test_essential_field_scores_top(self):
        """An essential field always scores highest."""
        self.assertEqual(
            smart_fields.score_field_importance("display_name", {"type": "char"}), 1000
        )

    def test_strip_sensitive_fields_enforced_on_read_result(self):
        """_strip_sensitive_fields drops credential-named keys.

        This is the guard get_record / search_records apply on the *bulk* paths
        -- smart defaults and the ``["__all__"]`` sentinel, never an explicit
        field list -- so a credential-named field is not surfaced by a caller
        that did not ask for it by name.
        """
        strip = self.env["mcp.mixin"]._strip_sensitive_fields
        record = {
            "id": 1,
            "name": "ACME",
            "api_key": "sk-should-not-leak",
            "webhook_secret": "shh",
        }
        strip(record)
        self.assertEqual(set(record), {"id", "name"})

    def test_get_record_strips_bulk_but_honors_explicit_fields(self):
        """get_record drops a sensitive-named field on ``__all__`` but not when named.

        ``is_sensitive_field_name`` is patched to flag the benign ``comment``
        field so the branch is observable on a real model: the ``["__all__"]``
        read omits it (bulk guard), while an explicit ``["name", "comment"]``
        request returns it (Odoo field-level ``groups=`` is the real ACL there).
        """
        partner_model = self.env.ref("base.model_res_partner")
        enabled = self.env["mcp.enabled.model"].search(
            [("model_id", "=", partner_model.id)], limit=1
        )
        if enabled:
            enabled.write({"allow_read": True, "active": True})
        else:
            self.env["mcp.enabled.model"].create(
                {"model_id": partner_model.id, "allow_read": True}
            )
        partner = self.env["res.partner"].create(
            {"name": "Sensitive Co", "comment": "confidential"}
        )
        mixin = self.env["mcp.mixin"]

        # get_record's model gate calls the global is_mcp_enabled(), which reads
        # the HTTP ``request`` -- unbound in a TransactionCase. Patch it True so
        # the gate resolves via ``env`` (the enabled-model row set up above); the
        # per-model allow_read flag is still enforced.
        with patch(
            "odoo.addons.mcp_server.controllers.utils.is_mcp_enabled",
            return_value=True,
        ), patch.object(
            mcp_tools_read, "is_sensitive_field_name", lambda name: name == "comment"
        ):
            explicit = mixin.get_record(
                "res.partner", partner.id, ["name", "comment"]
            )
            bulk = mixin.get_record("res.partner", partner.id, ["__all__"])

        self.assertIn("comment", explicit["structuredContent"]["record"])
        self.assertNotIn("comment", bulk["structuredContent"]["record"])


@tagged("much_unit", "post_install", "-at_install")
class TestRecordFormatter(common.TransactionCase):
    """RecordFormatter value rendering."""

    def setUp(self):
        super().setUp()
        self.fmt = RecordFormatter("res.partner")

    def test_integer_thousands_separator(self):
        self.assertEqual(
            self.fmt._format_field_value("x", 1234567, {"type": "integer"}),
            "1,234,567",
        )

    def test_float_precision_from_digits(self):
        self.assertEqual(
            self.fmt._format_field_value(
                "x", 1234.5, {"type": "float", "digits": (16, 3)}
            ),
            "1,234.500",
        )

    def test_monetary_two_decimals(self):
        self.assertEqual(
            self.fmt._format_field_value("x", 1234.5, {"type": "monetary"}),
            "1,234.50",
        )

    def test_datetime_iso8601_utc_offset(self):
        self.assertEqual(
            self.fmt._format_field_value(
                "x", "2024-01-15 13:45:30", {"type": "datetime"}
            ),
            "2024-01-15T13:45:30+00:00",
        )

    def test_selection_label_and_key(self):
        meta = {
            "type": "selection",
            "selection": [("draft", "Draft"), ("done", "Done")],
        }
        self.assertEqual(
            self.fmt._format_field_value("state", "draft", meta), "Draft (draft)"
        )

    def test_boolean_yes_no(self):
        self.assertEqual(
            self.fmt._format_field_value("b", True, {"type": "boolean"}), "Yes"
        )
        self.assertEqual(
            self.fmt._format_field_value("b", False, {"type": "boolean"}), "No"
        )

    def test_empty_char_reads_not_set(self):
        """An empty char field reads 'Not set', not 'No' (driven by type)."""
        self.assertEqual(
            self.fmt._format_field_value("ref", False, {"type": "char"}), "Not set"
        )

    def test_long_value_truncated_with_marker(self):
        rendered = self.fmt._format_field_value("note", "a" * 2500, {"type": "text"})
        self.assertIn("truncated", rendered)
        self.assertIn("2500", rendered)
        self.assertLess(len(rendered), 2500)


@tagged("much_unit", "post_install", "-at_install")
class TestDatasetFormatter(common.TransactionCase):
    """DatasetFormatter search-result rendering."""

    def test_search_results_header_and_pagination(self):
        fmt = DatasetFormatter("res.partner")
        rows = [{"id": 1, "display_name": "ACME"}, {"id": 2, "display_name": "Globex"}]
        text = fmt.format_search_results(
            rows, total_count=5, offset=0, limit=2, current_page=1, total_pages=3
        )
        self.assertIn("Search Results: res.partner", text)
        self.assertIn("Page 1 of 3", text)
        self.assertIn("Showing records 1-2 of 5", text)


@tagged("much_unit", "post_install", "-at_install")
class TestUriSchema(common.TransactionCase):
    """odoo:// URI build/parse round-trips and error paths."""

    def test_field_uri_round_trip(self):
        uri = build_field_uri("res.partner", 10, "image_1920")
        self.assertEqual(uri, "odoo://record/res.partner/10/image_1920")
        parsed = parse_field_uri(uri)
        self.assertEqual(parsed.model, "res.partner")
        self.assertEqual(parsed.record_id, 10)
        self.assertEqual(parsed.field, "image_1920")

    def test_attachment_uri_round_trip(self):
        self.assertEqual(build_attachment_uri(42), "odoo://attachment/42")
        self.assertEqual(parse_attachment_uri("odoo://attachment/42"), 42)

    def test_parse_field_uri_rejects_garbage(self):
        with self.assertRaises(URIParseError):
            parse_field_uri("not-a-uri")

    def test_parse_attachment_uri_rejects_non_numeric(self):
        with self.assertRaises(URIParseError):
            parse_attachment_uri("odoo://attachment/abc")

    def test_build_field_uri_rejects_invalid_model(self):
        with self.assertRaises(ValueError):
            build_field_uri("1badmodel", 10, "image_1920")

    def test_build_field_uri_rejects_empty_field(self):
        with self.assertRaises(ValueError):
            build_field_uri("res.partner", 10, "")


@tagged("much_unit", "post_install", "-at_install")
class TestValidateMethodCallGuard(common.TransactionCase):
    """call_model_method self-escalation guard (_validate_method_call)."""

    def setUp(self):
        super().setUp()
        self.mixin = self.env["mcp.mixin"]

    def test_action_server_run_blocked(self):
        """ir.actions.server.run (self-sudo code exec) is refused."""
        with self.assertRaises(AccessError):
            self.mixin._validate_method_call(
                "ir.actions.server", self.env["ir.actions.server"], "run"
            )

    def test_cron_method_direct_trigger_blocked(self):
        """ir.cron.method_direct_trigger (runs a job as its owner) is refused."""
        with self.assertRaises(AccessError):
            self.mixin._validate_method_call(
                "ir.cron", self.env["ir.cron"], "method_direct_trigger"
            )

    def test_actions_namespace_blocked_wholesale(self):
        """The whole ir.actions.* namespace is refused, not just the server model."""
        with self.assertRaises(AccessError):
            self.mixin._validate_method_call(
                "ir.actions.act_window",
                self.env["ir.actions.act_window"],
                "some_business_method",
            )

    def test_run_method_name_blocked_on_any_model(self):
        """'run' is refused even on a non-action model (method-name backstop)."""
        with self.assertRaises(AccessError):
            self.mixin._validate_method_call(
                "res.partner", self.env["res.partner"], "run"
            )
