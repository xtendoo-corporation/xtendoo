"""Tests for the native MCP write tools.

Exercises the write-side tool layer wired onto ``mcp.mixin`` and served through
``POST /mcp``:

* ``create_record`` / ``update_record`` / ``delete_record`` round-trip on a
  write-enabled model; a write-disabled model is blocked by the MCP per-op gate
  (``isError`` carrying the ``via MCP`` message); a low-privilege user is blocked
  by Odoo's own ACL (``AccessError`` surfaced as ``isError``, *not* the MCP gate).
* ``call_model_method`` is denied while ``allow_method_calls`` is off;
  once the flag is set a genuine business method (``message_post``, write-gated)
  runs, while a private (underscore-prefixed) method, an ORM CRUD method
  (``read``) and a generic ORM-surface method (``update``, on ``BaseModel``) are
  all rejected (the per-operation gates and the business-method-only boundary
  stay the real CRUD boundary).
* Each ``tools/call`` writes an ``mcp.log`` audit row -- a ``model_access`` row
  for a success (on the request cursor) and an ``error`` row for a failure (on
  the controller's independent committed cursor) -- which this suite asserts
  directly (audit failures are swallowed, so we query the rows rather than rely
  on an exception).
* The in-memory rate-limit primitives trip at the configured threshold.

Mirrors the HttpCase + ``_generate("rpc", ...)`` key-minting pattern of
``test_mcp_read_tools.py``; every request rides ``self.url_open`` so the HttpCase
test-cursor cookie travels with it -- required for the audit's independent cursor
(a ``TestCursor`` under HttpCase) to open and commit.

Note: ``mcp.log`` has no test-mode skip guard, so rows are logged whenever
``mcp_server.enable_logging`` is on; here we assert on the persisted rows.
"""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import common, tagged
from odoo.tools import mute_logger

from ..controllers import rate_limiting, utils
from .test_helpers import create_test_user, grant_mcp_access, users_groups_field


@tagged("much_unit", "post_install", "-at_install")
class TestMcpWriteTools(common.HttpCase):
    """Native MCP write tools + method calls + audit/rate-limit."""

    def setUp(self):
        super().setUp()
        utils.clear_mcp_caches()
        rate_limiting._api_limiter.clear()

        unique_id = str(int(time.time() * 1000))[-6:]

        groups_field = users_groups_field(self.env)

        # Key-owner user: internal user + Contact Creation, so it can fully
        # CRUD res.partner (the bare internal group is read-only on it), but
        # NOT ir.mail_server which is group_system only.
        self.mcp_user = create_test_user(
            self.env,
            "MCP Write User",
            f"mcp_write_user_{unique_id}",
            email=f"mcp_write_{unique_id}@example.com",
            **{
                groups_field: [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ]
            },
        )
        grant_mcp_access(self.mcp_user)
        self.api_key = self._mint_key(self.mcp_user, "Write Tools Key")

        # Low-privilege user pinned to the bare internal-user group: blocked by
        # Odoo ACL on an admin-only model even when MCP allows the operation.
        self.low_priv_user = create_test_user(
            self.env,
            "MCP Low Priv Write User",
            f"mcp_lowpriv_write_{unique_id}",
            email=f"mcp_lowpriv_write_{unique_id}@example.com",
            **{groups_field: [(6, 0, [self.env.ref("base.group_user").id])]},
        )
        # The door requires the MCP group; the user stays "low priv" for the
        # Odoo ACL assertions (no extra functional groups).
        grant_mcp_access(self.low_priv_user)
        self.low_priv_key = self._mint_key(self.low_priv_user, "Low Priv Write Key")

        # res.partner: fully write-enabled, method calls OFF (toggled per-test).
        self.partner_model = self._enable_model(
            "base.model_res_partner",
            allow_read=True,
            allow_create=True,
            allow_write=True,
            allow_unlink=True,
            allow_method_calls=False,
        )
        # res.country: read-only via MCP -> create is blocked by the per-op gate.
        self._enable_model("base.model_res_country", allow_read=True)
        # ir.mail_server: MCP create allowed, but admin-only in Odoo -> the
        # low-priv user is blocked by the ORM (AccessError, not the MCP gate).
        self._enable_model(
            "base.model_ir_mail_server", allow_read=True, allow_create=True
        )

        # A target record for call_model_method.
        self.partner = self.env["res.partner"].create(
            {"name": f"MCP Method Target {unique_id}"}
        )

        params = self.env["ir.config_parameter"].sudo()
        params.set_param("mcp_server.enabled", "True")
        params.set_param("mcp_server.enable_logging", "True")
        utils.clear_mcp_caches()

    # ------------------------------------------------------------------
    # Fixture helpers
    # ------------------------------------------------------------------
    def _mint_key(self, user, name):
        """Mint an ``rpc``-scope API key for ``user``."""
        return self.env(user=user)["res.users.apikeys"]._generate(
            "rpc", name, datetime.now() + timedelta(days=30)
        )

    def _enable_model(self, model_xmlid, **perms):
        """Find-or-create an ``mcp.enabled.model`` row for ``model_xmlid``."""
        model_id = self.env.ref(model_xmlid).id
        record = (
            self.env["mcp.enabled.model"]
            .sudo()
            .search([("model_id", "=", model_id)], limit=1)
        )
        vals = {"active": True, **perms}
        if record:
            record.write(vals)
        else:
            record = (
                self.env["mcp.enabled.model"]
                .sudo()
                .create({"model_id": model_id, **vals})
            )
        return record

    def _set_method_calls(self, enabled):
        """Toggle ``allow_method_calls`` on res.partner and refresh caches."""
        self.partner_model.allow_method_calls = enabled
        self.env.flush_all()
        utils.clear_mcp_caches()

    # ------------------------------------------------------------------
    # RPC helpers
    # ------------------------------------------------------------------
    _DEFAULT_KEY = object()

    def _post_rpc(self, body, api_key=_DEFAULT_KEY):
        """POST a JSON-RPC ``body`` dict to ``/mcp`` with bearer auth."""
        headers = {"Content-Type": "application/json"}
        if api_key is self._DEFAULT_KEY:
            api_key = self.api_key
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        return self.url_open("/mcp", data=json.dumps(body), headers=headers)

    def _call_tool(self, name, arguments=None, api_key=_DEFAULT_KEY):
        """Invoke ``tools/call`` and return the tool-result dict."""
        response = self._post_rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
            api_key=api_key,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("error", payload, msg=payload.get("error"))
        return payload["result"]

    # ------------------------------------------------------------------
    # Concurrency-conflict retry (service.model.retrying)
    # ------------------------------------------------------------------
    def test_serialization_failure_propagates_not_swallowed(self):
        """A concurrency conflict propagates as a JSON-RPC error, not an isError.

        A tool raising psycopg2 ``SerializationFailure`` (serialization failure /
        deadlock) must NOT be swallowed by the generic ``except`` into an
        ``isError`` tool result -- that robs Odoo's ``service.model.retrying`` of
        the exception it needs to retry, turning a transient conflict into a
        spurious internal error. Assert it surfaces as a top-level JSON-RPC error
        with no tool ``result`` (the buggy path returned
        ``{"result": {"isError": true}}`` here). The retry itself is core's job
        once the exception reaches it; it is not re-exercised under the HttpCase
        test cursor (a synthetic error carries no ``pgcode`` to loop on).
        """
        from psycopg2.errors import SerializationFailure

        mixin_cls = type(self.env["mcp.mixin"])
        boom = MagicMock(
            side_effect=SerializationFailure("could not serialize access")
        )
        with mute_logger(
            "odoo.addons.mcp_server.controllers.mcp_dispatcher",
            "odoo.http",
            "odoo.service.model",
        ), patch.object(mixin_cls, "_resolve_model", boom):
            response = self._post_rpc(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {
                        "name": "create_record",
                        "arguments": {
                            "model": "res.partner",
                            "values": {"name": "conflict"},
                        },
                    },
                }
            )
        payload = response.json()
        # Propagated as a JSON-RPC error, not swallowed into a tool result.
        self.assertIsNone(payload.get("result"), msg=payload)
        self.assertIn("error", payload)
        # The tool actually ran and hit the injected conflict.
        self.assertTrue(boom.called)

    # ------------------------------------------------------------------
    # create / update / delete round-trip
    # ------------------------------------------------------------------
    def test_create_update_delete_roundtrip(self):
        """create -> update -> delete a record on a write-enabled model."""
        create_res = self._call_tool(
            "create_record",
            {"model": "res.partner", "values": {"name": "MCP Created"}},
        )
        self.assertFalse(create_res["isError"], msg=create_res)
        new_id = create_res["structuredContent"]["record"]["id"]
        self.assertTrue(new_id)

        self.env.invalidate_all()
        partner = self.env["res.partner"].browse(new_id)
        self.assertTrue(partner.exists())
        self.assertEqual(partner.name, "MCP Created")

        update_res = self._call_tool(
            "update_record",
            {
                "model": "res.partner",
                "record_id": new_id,
                "values": {"name": "MCP Updated"},
            },
        )
        self.assertFalse(update_res["isError"], msg=update_res)
        self.env.invalidate_all()
        self.assertEqual(self.env["res.partner"].browse(new_id).name, "MCP Updated")

        delete_res = self._call_tool(
            "delete_record", {"model": "res.partner", "record_id": new_id}
        )
        self.assertFalse(delete_res["isError"], msg=delete_res)
        self.env.invalidate_all()
        self.assertFalse(self.env["res.partner"].browse(new_id).exists())

    def test_create_on_write_disabled_model_is_blocked(self):
        """A create on a read-only-via-MCP model is refused by the per-op gate."""
        result = self._call_tool(
            "create_record",
            {"model": "res.country", "values": {"name": "MCP Testland"}},
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("not allowed", text.lower())
        self.assertIn("via MCP", text)  # the MCP gate, not an ORM error
        self.assertNotIn("Traceback", text)

    def test_low_privilege_user_blocked_by_acl(self):
        """A low-priv user creating an admin-only model is blocked by Odoo ACL."""
        result = self._call_tool(
            "create_record",
            {"model": "ir.mail_server", "values": {"name": "MCP SMTP"}},
            api_key=self.low_priv_key,
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertTrue(text.strip())
        self.assertNotIn("Traceback", text)
        # The MCP gate allowed create here; the refusal comes from Odoo's ACL.
        self.assertNotIn("via MCP", text)

    # ------------------------------------------------------------------
    # call_model_method
    # ------------------------------------------------------------------
    def test_call_model_method_denied_when_flag_off(self):
        """With allow_method_calls off, call_model_method is denied."""
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "read",
                "record_ids": [self.partner.id],
                "args": [["name"]],
            },
        )
        self.assertTrue(result["isError"])
        self.assertIn("not enabled", result["content"][0]["text"].lower())

    def test_call_model_method_caps_record_ids(self):
        """A record_ids list longer than max_limit is refused before browsing.

        Unlike the read tools, this path has no built-in size cap; an unbounded
        id list is a large ``IN(...)`` + unbounded result serialization. The cap
        reuses ``max_limit`` and trips regardless of whether the ids exist.
        """
        self._set_method_calls(True)
        self.env["ir.config_parameter"].sudo().set_param("mcp_server.max_limit", "5")

        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": [1, 2, 3, 4, 5, 6],
            },
        )
        self.assertTrue(result["isError"], msg=result)
        self.assertIn("too many", result["content"][0]["text"].lower())

    def test_call_model_method_rejects_non_list_record_ids(self):
        """A non-list record_ids (e.g. the string "12") is rejected, not iterated.

        ``"12"`` is truthy and iterable, so ``[int(c) for c in "12"]`` would
        silently expand to ids ``[1, 2]`` and act on the wrong records. Like
        ``args``/``kwargs``, ``record_ids`` must be type-checked so the client
        gets a clean error instead of a silent misinterpretation.
        """
        self._set_method_calls(True)
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": "12",
            },
        )
        self.assertTrue(result["isError"], msg=result)
        self.assertIn("must be a list", result["content"][0]["text"].lower())

    def test_call_model_method_rejects_partial_missing_ids(self):
        """A batch with any non-existent record_id is refused, not silently run.

        ``[valid, 999999999]`` must not run on the valid subset and report
        success -- the missing id is surfaced as an error (like the single-record
        tools), and the valid record is left untouched.
        """
        self._set_method_calls(True)
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": [self.partner.id, 999999999],
                "kwargs": {"body": "should not post"},
            },
        )
        self.assertTrue(result["isError"], msg=result)
        text = result["content"][0]["text"]
        self.assertIn("not found", text.lower())
        self.assertIn("999999999", text)
        # The whole call was rejected before running -> the valid record was not
        # posted to (no silent partial side effect).
        self.env.invalidate_all()
        posted = self.env["mail.message"].search_count(
            [
                ("model", "=", "res.partner"),
                ("res_id", "=", self.partner.id),
                ("body", "like", "should not post"),
            ]
        )
        self.assertEqual(posted, 0)

    def test_call_model_method_public_runs_when_enabled(self):
        """With allow_method_calls on, a genuine business method runs.

        Uses ``message_post`` -- a real business method contributed by
        ``mail.thread`` (NOT an attribute of ``BaseModel``), mapped to the
        'write' operation. With ``allow_method_calls`` AND ``allow_write`` both
        on (allow_write is set in setUp) it runs and actually posts a chatter
        message, exercising the business-method allow-path through the per-op
        gate.
        """
        self._set_method_calls(True)
        before = self.env["mail.message"].search_count(
            [("model", "=", "res.partner"), ("res_id", "=", self.partner.id)]
        )
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": [self.partner.id],
                "kwargs": {"body": "business method ran"},
            },
        )
        self.assertFalse(result["isError"], msg=result)
        self.assertTrue(result["structuredContent"]["success"])
        # The business method really executed -> a new chatter message exists.
        self.env.invalidate_all()
        after = self.env["mail.message"].search_count(
            [("model", "=", "res.partner"), ("res_id", "=", self.partner.id)]
        )
        self.assertEqual(after, before + 1)

    def test_json_safe_caps_returned_recordset(self):
        """A recordset return is bounded so the output size cannot blow up.

        ``call_model_method`` caps its INPUT (record_ids) but a method can still
        return a huge recordset; ``_json_safe`` serializes one ``display_name``
        per record, so it caps the recordset and appends a truncation marker
        rather than dumping it unbounded.
        """
        from ..models.mcp_tools_write import _json_safe

        partners = self.env["res.partner"].create(
            [{"name": f"Cap Partner {i}"} for i in range(3)]
        )
        serialized = _json_safe(partners, max_records=2)
        # First two records as {id, display_name}, then a truncation marker.
        self.assertEqual(len(serialized), 3)
        self.assertEqual(serialized[0]["id"], partners[0].id)
        self.assertEqual(serialized[1]["id"], partners[1].id)
        self.assertIsInstance(serialized[2], str)
        self.assertIn("truncated", serialized[2])
        self.assertIn("2 of 3", serialized[2])
        # Within the cap: no marker appended.
        self.assertEqual(len(_json_safe(partners, max_records=5)), 3)

    def test_call_model_method_response_truncates_large_recordset(self):
        """A method returning a recordset > MAX_LIMIT is truncated in the RESPONSE.

        The isolated ``_json_safe`` test above pins the helper; this drives the
        whole ``call_model_method`` path end-to-end and asserts the cap + marker
        actually reach the tool result (structuredContent and text), not just the
        helper. A public business method is patched onto res.partner to return a
        recordset one larger than the serialization cap.
        """
        from ..models.mcp_tools_read import MAX_LIMIT

        self._set_method_calls(True)
        self.env["res.partner"].create(
            [{"name": f"Big Recordset Partner {i}"} for i in range(MAX_LIMIT + 1)]
        )

        def fake_big(records_self):
            # Return a recordset larger than the _json_safe cap; resolved in the
            # request's own env (shared test cursor) so no cross-env recordset.
            return records_self.search([("name", "=like", "Big Recordset Partner%")])

        partner_cls = type(self.env["res.partner"])
        with patch.object(partner_cls, "action_mcp_test_big", fake_big, create=True):
            result = self._call_tool(
                "call_model_method",
                {"model": "res.partner", "method": "action_mcp_test_big"},
            )

        self.assertFalse(result["isError"], msg=result)
        returned = result["structuredContent"]["result"]
        # MAX_LIMIT records serialized + a trailing truncation-marker string.
        self.assertEqual(len(returned), MAX_LIMIT + 1)
        self.assertIsInstance(returned[-1], str)
        self.assertIn("truncated", returned[-1])
        self.assertIn("%d of %d" % (MAX_LIMIT, MAX_LIMIT + 1), returned[-1])
        # The marker also reaches the human-readable text block.
        self.assertIn("truncated", result["content"][0]["text"])

    def test_call_model_method_generic_orm_method_blocked(self):
        """A generic ORM method (``update``) is refused via MCP.

        ``update`` is a public ``BaseModel`` method that mutates records, yet it
        is NOT in the CRUD denylist nor the per-op map -- only the generic-ORM
        -surface block (``hasattr(BaseModel, method)``) stops it. With
        ``allow_method_calls`` AND ``allow_write`` both on it must STILL be
        refused (it is not a model business method), and the record left
        unchanged. Guards the principled allow-business-methods-only boundary.
        """
        self._set_method_calls(True)  # allow_write already on from setUp
        original_name = self.partner.name
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "update",
                "record_ids": [self.partner.id],
                "args": [{"name": "HACKED VIA UPDATE"}],
            },
        )
        self.assertTrue(result["isError"], msg=result)
        text = result["content"][0]["text"]
        self.assertIn("generic orm", text.lower())
        self.assertNotIn("Traceback", text)
        # The blocked update must never have mutated the record.
        self.env.invalidate_all()
        self.assertEqual(
            self.env["res.partner"].browse(self.partner.id).name, original_name
        )

    def test_call_model_method_crud_method_blocked(self):
        """An ORM CRUD method (read) is refused even when method calls are on.

        ``allow_method_calls`` must not become a CRUD backdoor: the per-op MCP
        flags (allow_read/create/write/unlink) stay the real boundary.
        """
        self._set_method_calls(True)
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "read",
                "record_ids": [self.partner.id],
                "args": [["name"]],
            },
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"].lower()
        self.assertIn("crud", text)
        self.assertNotIn("Traceback", result["content"][0]["text"])

    def test_call_model_method_web_save_blocked(self):
        """The public ``web_save`` (CRUD via the web addon) is blocked.

        ``web_save`` writes/creates and would bypass allow_create/allow_write,
        so call_model_method must refuse the whole ``web_*`` family even when
        ``allow_method_calls`` is on -- the per-op gates stay the CRUD boundary.
        """
        self._set_method_calls(True)
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "web_save",
                "record_ids": [self.partner.id],
                "args": [{"ref": "HACKED"}, []],
            },
        )
        self.assertTrue(result["isError"], msg=result)
        text = result["content"][0]["text"]
        self.assertIn("data-access", text.lower())
        self.assertNotIn("Traceback", text)
        # The blocked web_save must never have mutated the record.
        self.env.invalidate_all()
        self.assertNotEqual(
            self.env["res.partner"].browse(self.partner.id).ref, "HACKED"
        )

    def test_call_model_method_base_registry_method_blocked(self):
        """``get_views`` (generic API on the ``base`` registry model) is blocked.

        ``get_views``/``get_view`` are contributed to the abstract ``base`` model
        by web+base, so they are NOT ``BaseModel`` Python attributes and slip past
        the ``hasattr(BaseModel, method)`` backstop. They return field/view
        metadata (like the hard-blocked ``fields_get``), so call_model_method must
        refuse them even with ``allow_method_calls`` on -- via the ``base``
        registry-model check.
        """
        self._set_method_calls(True)
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "get_views",
                "args": [[[False, "form"]]],
            },
        )
        self.assertTrue(result["isError"], msg=result)
        text = result["content"][0]["text"]
        self.assertIn("generic orm", text.lower())
        self.assertNotIn("Traceback", text)

    def test_call_model_method_private_rejected(self):
        """A private (underscore-prefixed) method is rejected even when enabled."""
        self._set_method_calls(True)
        result = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "_compute_display_name",
                "record_ids": [self.partner.id],
            },
        )
        self.assertTrue(result["isError"])
        self.assertIn("private", result["content"][0]["text"].lower())

    def test_call_model_method_per_op_gate_authoritative(self):
        """A KNOWN data-access method honours its per-op flag.

        ``message_post`` maps to the 'write' operation. With ``allow_method_calls``
        on but ``allow_write`` OFF it must be refused -- the per-op flags stay the
        authoritative boundary even through the method-call hatch, so the denylist
        misses (message_post/toggle_active/...) cannot slip through. Once
        ``allow_write`` is on, the same call runs.
        """
        # allow_method_calls on, but write OFF -> message_post (write) refused.
        self._enable_model(
            "base.model_res_partner",
            allow_read=True,
            allow_create=True,
            allow_write=False,
            allow_unlink=True,
            allow_method_calls=True,
        )
        utils.clear_mcp_caches()
        denied = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": [self.partner.id],
                "kwargs": {"body": "should be blocked"},
            },
        )
        self.assertTrue(denied["isError"], msg=denied)
        text = denied["content"][0]["text"]
        self.assertIn("write", text.lower())
        self.assertNotIn("Traceback", text)

        # Flip allow_write ON -> the same known write method now runs.
        self._enable_model(
            "base.model_res_partner",
            allow_read=True,
            allow_create=True,
            allow_write=True,
            allow_unlink=True,
            allow_method_calls=True,
        )
        utils.clear_mcp_caches()
        allowed = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": [self.partner.id],
                "kwargs": {"body": "now allowed"},
            },
        )
        self.assertFalse(allowed["isError"], msg=allowed)
        self.assertTrue(allowed["structuredContent"]["success"])

    # ------------------------------------------------------------------
    # Audit logging (mcp.log)
    # ------------------------------------------------------------------
    def test_audit_rows_written_for_success_and_failure(self):
        """A successful and a failing tools/call each persist an mcp.log row."""
        ok = self._call_tool(
            "create_record",
            {"model": "res.partner", "values": {"name": "Audit OK"}},
        )
        self.assertFalse(ok["isError"], msg=ok)

        bad = self._call_tool(
            "create_record",
            {"model": "res.country", "values": {"name": "Audit Bad"}},
        )
        self.assertTrue(bad["isError"])

        self.env.invalidate_all()
        log_model = self.env["mcp.log"].sudo()

        success_rows = log_model.search(
            [
                ("event_type", "=", "model_access"),
                ("model_name", "=", "res.partner"),
                ("operation", "=", "create"),
                ("user_id", "=", self.mcp_user.id),
            ]
        )
        self.assertTrue(
            success_rows, "expected a model_access audit row for the successful create"
        )

        # The blocked create is an authorization denial (the per-model gate
        # raises AccessError), so it is audited as permission_denied WITH auth
        # attribution -- not a generic E500 error.
        denied_rows = log_model.search(
            [
                ("event_type", "=", "permission_denied"),
                ("model_name", "=", "res.country"),
                ("operation", "=", "create"),
                ("user_id", "=", self.mcp_user.id),
            ]
        )
        self.assertTrue(
            denied_rows,
            "expected a permission_denied audit row for the blocked create",
        )
        self.assertEqual(denied_rows[0].auth_method, "api_key")
        e500_rows = log_model.search(
            [
                ("event_type", "=", "error"),
                ("model_name", "=", "res.country"),
                ("operation", "=", "create"),
                ("user_id", "=", self.mcp_user.id),
            ]
        )
        self.assertFalse(
            e500_rows, "the blocked create must not also be logged as an E500 error"
        )

    def test_audit_records_ids_and_real_method_name(self):
        """A write logs its record_ids; call_model_method logs the real method."""
        # A write (update_record) must record the touched record id.
        upd = self._call_tool(
            "update_record",
            {
                "model": "res.partner",
                "record_id": self.partner.id,
                "values": {"comment": "audited"},
            },
        )
        self.assertFalse(upd["isError"], msg=upd)

        # call_model_method must log the ACTUAL business method (message_post),
        # not the literal tool name, mirroring the legacy XML-RPC proxy.
        self._set_method_calls(True)
        called = self._call_tool(
            "call_model_method",
            {
                "model": "res.partner",
                "method": "message_post",
                "record_ids": [self.partner.id],
                "kwargs": {"body": "audited method call"},
            },
        )
        self.assertFalse(called["isError"], msg=called)

        self.env.invalidate_all()
        log_model = self.env["mcp.log"].sudo()

        write_row = log_model.search(
            [
                ("event_type", "=", "model_access"),
                ("model_name", "=", "res.partner"),
                ("operation", "=", "write"),
                ("user_id", "=", self.mcp_user.id),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(write_row, "expected a model_access row for the update")
        self.assertEqual(write_row.record_ids, str(self.partner.id))
        # The row is self-describing: which tool, how it authenticated, the MCP
        # client, the argument keys and a result-size summary (metadata only --
        # no raw field values).
        self.assertEqual(write_row.tool_name, "update_record")
        self.assertEqual(write_row.auth_method, "api_key")
        self.assertTrue(write_row.user_agent)
        self.assertIn("values", write_row.request_data)
        self.assertEqual(write_row.response_data, "1 record(s)")

        method_row = log_model.search(
            [
                ("event_type", "=", "model_access"),
                ("model_name", "=", "res.partner"),
                ("operation", "=", "message_post"),
                ("user_id", "=", self.mcp_user.id),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(
            method_row,
            "call_model_method must log the real method name as the operation",
        )
        self.assertEqual(method_row.record_ids, str(self.partner.id))

    # ------------------------------------------------------------------
    # Rate limiting primitives (endpoint enforcement covered in test_mcp_rate_limit)
    # ------------------------------------------------------------------
    def test_rate_limit_primitives_trip_at_threshold(self):
        """record_api_request + check_rate_limit deny once the limit is reached."""
        rate_limiting._api_limiter.clear()
        uid = self.mcp_user.id
        dbname = self.env.cr.dbname
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "11"
        )

        mock_request = MagicMock()
        mock_request.env = self.env
        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            for _ in range(10):
                rate_limiting.record_api_request(uid, dbname)
            # 10 recorded requests stay under the limit of 11.
            self.assertTrue(rate_limiting.check_rate_limit(uid, dbname))

            # The 11th request hits the threshold -> subsequent checks deny.
            rate_limiting.record_api_request(uid, dbname)
            self.assertFalse(rate_limiting.check_rate_limit(uid, dbname))

    # ------------------------------------------------------------------
    # post_message (-> message_post, gated as a write op)
    # ------------------------------------------------------------------
    def test_post_message_success_creates_mail_message(self):
        """post_message on a chatter model creates a mail.message."""
        result = self._call_tool(
            "post_message",
            {
                "model": "res.partner",
                "record_id": self.partner.id,
                "body": "Hello from MCP",
            },
        )
        self.assertFalse(result["isError"], msg=result)
        message_id = result["structuredContent"]["message_id"]
        self.assertTrue(message_id)

        self.env.invalidate_all()
        message = self.env["mail.message"].sudo().browse(message_id).exists()
        self.assertTrue(message, "post_message must create a mail.message row")
        self.assertEqual(message.model, "res.partner")
        self.assertEqual(message.res_id, self.partner.id)
        self.assertIn("Hello from MCP", message.body or "")

    def test_post_message_non_chatter_model_is_clean_error(self):
        """post_message on a model without chatter errors cleanly (no traceback)."""
        # res.country has no mail.thread; enable it for write so the per-op gate
        # passes and we reach the missing-chatter guard.
        self._enable_model("base.model_res_country", allow_read=True, allow_write=True)
        utils.clear_mcp_caches()
        result = self._call_tool(
            "post_message",
            {"model": "res.country", "record_id": 1, "body": "nope"},
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("chatter", text.lower())
        self.assertNotIn("Traceback", text)

    def test_post_message_invalid_subtype_is_clean_error(self):
        """post_message with an unknown subtype errors cleanly."""
        result = self._call_tool(
            "post_message",
            {
                "model": "res.partner",
                "record_id": self.partner.id,
                "body": "Hi",
                "subtype": "bogus",
            },
        )
        self.assertTrue(result["isError"])
        self.assertIn("subtype", result["content"][0]["text"].lower())

    # ------------------------------------------------------------------
    # Savepoint rollback: mutate-then-raise leaves NO partial row
    # ------------------------------------------------------------------
    @mute_logger(
        "odoo.addons.mcp_server.controllers.error_sanitizer",
        "odoo.addons.mcp_server.controllers.mcp",
        "odoo.sql_db",
    )
    def test_create_record_savepoint_rolls_back_partial_writes(self):
        """A create that inserts a parent then fails on a child must persist nothing.

        The nested child carries a bad ``country_id`` foreign key: Odoo creates
        the parent row first, then the child INSERT trips the FK constraint. The
        dispatcher's savepoint must roll back the already-inserted parent, so no
        orphan record survives (and the request returns a sanitized failure, not
        a 500).
        """
        marker = "MCP Savepoint Orphan %s" % int(time.time() * 1000000)
        response = self._post_rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "create_record",
                    "arguments": {
                        "model": "res.partner",
                        "values": {
                            "name": marker,
                            "child_ids": [
                                [0, 0, {"name": "child", "country_id": 999999999}]
                            ],
                        },
                    },
                },
            }
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        # The call must fail -- either as a JSON-RPC invalid/internal error or a
        # sanitized isError tool result -- but never report success.
        if "error" in payload:
            self.assertIn(payload["error"]["code"], (-32602, -32603))
        else:
            self.assertTrue(payload["result"]["isError"], msg=payload)

        # The partial parent insert must have been rolled back by the savepoint.
        self.env.invalidate_all()
        orphan = self.env["res.partner"].search([("name", "=", marker)])
        self.assertFalse(orphan, "savepoint must roll back the partial parent insert")

    @mute_logger(
        "odoo.addons.mcp_server.controllers.error_sanitizer",
        "odoo.addons.mcp_server.controllers.mcp",
    )
    def test_savepoint_rolls_back_valid_write_on_non_db_error(self):
        """The controller savepoint rolls back a VALID write when the tool raises.

        Unlike the FK test above -- whose IntegrityError poisons the entire
        request transaction, so it would roll back even with the savepoint
        removed -- here the tool performs a real, VALID ``write`` on an existing
        record and then raises a NON-DB ``UserError``, which does NOT poison the
        cursor. That write happens inside the ``cr.savepoint()`` in
        ``_tools_call``; the savepoint rolls it back before the request returns
        the sanitized ``isError`` result. Remove that savepoint and the service
        layer would flush+commit the valid write, persisting it -- so this test
        fails if the savepoint is removed.

        Patching targets the registry class (``type(env['mcp.mixin'])``) because
        recordset methods are read-only on instances; the ``/mcp`` handler
        runs in-process under HttpCase and shares that class, so the patch binds.
        """
        marker = "MCP Savepoint Valid Write %s" % int(time.time() * 1000000)
        partner_id = self.partner.id

        def fake_update_record(mixin_self, model, record_id, values):
            # A real, valid write inside the controller's savepoint...
            mixin_self.env["res.partner"].browse(int(record_id)).write({"ref": marker})
            # ...then a non-DB error that leaves the cursor usable.
            raise UserError(  # pylint: disable=translation-required
                "Intentional post-write failure for savepoint test"
            )

        mixin_cls = type(self.env["mcp.mixin"])
        with patch.object(mixin_cls, "update_record", fake_update_record):
            result = self._call_tool(
                "update_record",
                {
                    "model": "res.partner",
                    "record_id": partner_id,
                    "values": {"name": "ignored"},
                },
            )

        # The tool raised -> sanitized isError result (HTTP 200), not a 500.
        self.assertTrue(result["isError"], msg=result)
        self.assertNotIn("Traceback", result["content"][0]["text"])

        # The valid write must have been rolled back by the controller savepoint.
        self.env.invalidate_all()
        self.assertNotEqual(
            self.env["res.partner"].browse(partner_id).ref,
            marker,
            "controller savepoint must roll back the valid write on tool error",
        )

    @mute_logger(
        "odoo.addons.mcp_server.controllers.error_sanitizer",
        "odoo.addons.mcp_server.controllers.mcp",
    )
    def test_malformed_tool_return_rolls_back_and_is_error(self):
        """A tool returning a non-dict after a valid write -> isError + rollback.

        Covers the ``_ToolResultError`` branch in ``_tools_call``: normalizing
        the tool output (``dict(tool_output)``) fails, so the malformed return is
        re-raised INSIDE the savepoint. Two things must hold: the partial write
        is rolled back (not flushed+committed), and the failure is classified as
        an ``isError`` tool result -- NOT a ``-32602`` invalid-params client
        error (``_call_tool`` asserts the response carries no ``error`` envelope,
        so simply reaching its ``result`` proves the distinction).
        """
        marker = "MCP Malformed Return %s" % int(time.time() * 1000000)
        partner_id = self.partner.id

        def fake_update_record(mixin_self, model, record_id, values):
            # A real, valid write inside the controller's savepoint...
            mixin_self.env["res.partner"].browse(int(record_id)).write({"ref": marker})
            # ...then a malformed (non-dict) return the controller can't normalize.
            return "not-a-dict"

        mixin_cls = type(self.env["mcp.mixin"])
        with patch.object(mixin_cls, "update_record", fake_update_record):
            result = self._call_tool(
                "update_record",
                {
                    "model": "res.partner",
                    "record_id": partner_id,
                    "values": {"name": "ignored"},
                },
            )

        # Classified as a tool error (isError result), not a -32602 protocol error.
        self.assertTrue(result["isError"], msg=result)
        self.assertNotIn("Traceback", result["content"][0]["text"])

        # The valid write must have been rolled back by the controller savepoint.
        self.env.invalidate_all()
        self.assertNotEqual(
            self.env["res.partner"].browse(partner_id).ref,
            marker,
            "controller savepoint must roll back the write on a malformed return",
        )

    # ------------------------------------------------------------------
    # update_record / delete_record -- gating denial + missing record
    # ------------------------------------------------------------------
    def test_update_on_write_disabled_model_is_blocked(self):
        """update_record on a read-only-via-MCP model is refused by the gate."""
        country = self.env.ref("base.us")
        result = self._call_tool(
            "update_record",
            {
                "model": "res.country",
                "record_id": country.id,
                "values": {"name": "MCP Renamed"},
            },
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("via MCP", text)
        self.assertNotIn("Traceback", text)
        # The gate fired before any ORM write -> the name is untouched.
        self.env.invalidate_all()
        self.assertNotEqual(country.name, "MCP Renamed")

    def test_delete_on_unlink_disabled_model_is_blocked(self):
        """delete_record on a model without MCP unlink is refused by the gate."""
        country = self.env.ref("base.us")
        result = self._call_tool(
            "delete_record",
            {"model": "res.country", "record_id": country.id},
        )
        self.assertTrue(result["isError"])
        self.assertIn("via MCP", result["content"][0]["text"])
        self.env.invalidate_all()
        self.assertTrue(country.exists(), "the gate must block the unlink")

    def test_update_missing_record_returns_missing_error(self):
        """update_record on a non-existent id yields a clean MissingError."""
        result = self._call_tool(
            "update_record",
            {
                "model": "res.partner",
                "record_id": 999999999,
                "values": {"name": "x"},
            },
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("not found", text.lower())
        self.assertNotIn("Traceback", text)

    def test_delete_missing_record_returns_missing_error(self):
        """delete_record on a non-existent id yields a clean MissingError."""
        result = self._call_tool(
            "delete_record",
            {"model": "res.partner", "record_id": 999999999},
        )
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("not found", text.lower())
        self.assertNotIn("Traceback", text)
