"""Write-side MCP tools.

Contributes the write tools to :class:`McpMixin` via ``_inherit = 'mcp.mixin'``:
``create_record``, ``update_record``, ``delete_record`` and the
method-call escape hatch ``call_model_method`` plus ``post_message``.

Every tool routes through the mixin chokepoints: :meth:`McpMixin._resolve_model`
applies the coarse model gate, then :meth:`McpMixin._check_op` applies the
per-operation (``create``/``write``/``unlink``) gate. The ORM call then runs as
the calling user (``self.env`` is already user-scoped, no ``sudo``),
so Odoo's ``ir.model.access``, record rules and required-field validation remain
the real enforcement boundary.

``call_model_method`` is the one exception to the per-operation gate: the
business-method escape hatch, gated instead by the per-model
``allow_method_calls`` opt-in flag (see :meth:`_validate_method_call` for the
boundary it enforces). ``post_message`` maps to ``message_post`` and is gated as
a plain **write** operation, not via ``allow_method_calls``.
"""

import json
import logging

from odoo import _, api, models
from odoo.exceptions import AccessError, MissingError, UserError

from ..controllers import utils
from .mcp_mixin import mcp_tool
from .mcp_tools_read import MAX_LIMIT, _tool_result

_logger = logging.getLogger(__name__)

# Essential fields read back after a create/update -- universally available
# (not every model has ``name``).
_ESSENTIAL_FIELDS = ["id", "display_name"]

# ``post_message`` subtype -> mail subtype XML id.
_SUBTYPE_XMLID = {"note": "mail.mt_note", "comment": "mail.mt_comment"}

# ORM CRUD / data-access / privilege methods that ``call_model_method`` refuses
# even when ``allow_method_calls`` is on -- otherwise the business-method hatch
# would silently grant full CRUD, bypassing the per-operation MCP gates
# (allow_read/create/write/unlink). CRUD goes through the dedicated
# create/update/delete tools.
#
# ``_validate_method_call`` already refuses the whole generic ORM surface via a
# ``hasattr(models.BaseModel, method)`` check. This explicit set is the backstop
# for what that check misses: (1) the core CRUD primitives (belt-and-suspenders)
# and (2) public data-access methods the *web* addon contributes onto ``base``
# (``read_progress_bar``, ``search_panel_*``, ``formatted_read_group*``) which
# are not ``BaseModel`` attributes. The public ``web_*`` family is covered by a
# dedicated prefix check, not listed here.
_BLOCKED_METHOD_CALLS = frozenset(
    {
        "create",
        "write",
        "unlink",
        "read",
        "search",
        "search_read",
        "search_count",
        "search_fetch",
        "fetch",
        "read_group",
        "formatted_read_group",
        "formatted_read_grouping_sets",
        "read_progress_bar",
        "name_search",
        "search_panel_select_range",
        "search_panel_select_multi_range",
        "copy",
        "browse",
        "_write",
        "sudo",
        "with_user",
        "with_env",
        "with_context",
        "fields_get",
        "load",
        "export_data",
        "name_create",
        # Self-escalating primitives: ir.actions.server.run() executes
        # server-action Python as superuser (``for action in self.sudo()``) and
        # ir.cron.method_direct_trigger runs the cron job as its own (often
        # privileged) user -- either voids the calling-user boundary the hatch
        # rests on. Blocked wholesale at the model level too (see
        # ``_METHOD_CALL_BLOCKED_MODELS``); listed here as a method-name backstop.
        "run",
        "method_direct_trigger",
    }
)

# Models whose public methods are self-elevating and are refused by
# ``call_model_method`` regardless of ``allow_method_calls``. ir.actions.* (esp.
# ir.actions.server.run) and ir.cron (method_direct_trigger) run code with
# elevated privileges, so exposing their methods would bypass the calling-user
# ACL/record-rule boundary. Scoped to these prefixes on purpose -- other ir.*
# models (ir.attachment, ...) stay callable; no blanket ir.% block.
_METHOD_CALL_BLOCKED_MODELS = ("ir.actions", "ir.cron")


def _json_safe(value, max_records=MAX_LIMIT):
    """Coerce a method return value into MCP-serializable JSON.

    ``call_model_method`` can return anything a public Odoo method returns:
    recordsets, action dicts, dates, bytes, etc. Recordsets become a list of
    ``{id, display_name}``; containers recurse; JSON primitives pass through;
    everything else (dates, datetimes, bytes, ...) degrades to ``str`` so the
    result always serializes and never leaks a non-JSON object to the client.

    A recordset return is capped at ``max_records`` (the read ``MAX_LIMIT`` by
    default) -- both at the top level and nested inside containers -- so a method
    returning a huge recordset cannot serialize one ``display_name`` per record
    unbounded (an authenticated output-size DoS).
    """
    if isinstance(value, models.BaseModel):
        # Recordset -> id/display_name pairs; fall back to bare ids when
        # display_name can't be computed (e.g. a record rule on a related field).
        capped = value[:max_records]
        try:
            out = [{"id": rec.id, "display_name": rec.display_name} for rec in capped]
        except Exception:  # noqa: BLE001 - best-effort; keep ids on failure
            _logger.debug(
                "call_model_method: display_name unavailable for %s", value._name
            )
            out = list(capped.ids)
        if len(value) > max_records:
            out.append(
                _(
                    "... [truncated: %(shown)d of %(total)d records shown]",
                    shown=max_records,
                    total=len(value),
                )
            )
        return out
    if isinstance(value, dict):
        return {str(key): _json_safe(val, max_records) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, max_records) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


class McpToolsWrite(models.AbstractModel):
    """Write tools contributed to the ``mcp.mixin`` tool layer."""

    # Split from the read-tool layer on purpose (write tools are gated
    # separately); both legitimately contribute to the same mixin.
    _inherit = "mcp.mixin"  # pylint: disable=consider-merging-classes-inherited

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _record_web_url(self, model, record_id):
        """Best-effort web URL to a record.

        Returns ``""`` when no base URL is configured, else the modern
        ``/odoo/{model}/{id}`` web path.
        """
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()  # sudo: read system web.base.url param (not user data)
            .get_param("web.base.url")
        )
        if not base_url:
            return ""
        return f"{base_url}/odoo/{model}/{record_id}"

    @staticmethod
    def _format_write_text(message, record, url):
        """Render a concise confirmation block for create/update."""
        lines = [message]
        display_name = record.get("display_name")
        if display_name:
            lines.append(_("Name: %s", display_name))
        if url:
            lines.append(_("URL: %s", url))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # create_record
    # ------------------------------------------------------------------
    @mcp_tool(
        name="create_record",
        title="Create Record",
        description=(
            "Create a new record in a model. Pass 'values' as a field->value "
            "mapping. Runs as the calling user, so Odoo's access rights, record "
            "rules and required-field validation apply."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name (e.g. 'res.partner').",
                },
                "values": {
                    "type": "object",
                    "description": (
                        'Field values for the new record, e.g. {"name": "ACME"}.'
                    ),
                },
            },
            "required": ["model", "values"],
            "additionalProperties": False,
        },
        operation="create",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
    @api.model
    def create_record(self, model, values):
        """Create one record as the calling user and confirm it."""
        model_rs = self._resolve_model(model)
        self._check_op(model, "create")

        if not isinstance(values, dict) or not values:
            raise UserError(_("No values provided for record creation."))

        # Runs as the calling user -> ORM enforces create ACLs, record rules
        # and required-field validation.
        record = model_rs.create(values)
        message = _(
            "Successfully created %(model)s record with ID %(id)s",
            model=model,
            id=record.id,
        )
        return self._write_confirmation(model, record, message)

    # ------------------------------------------------------------------
    # update_record
    # ------------------------------------------------------------------
    @mcp_tool(
        name="update_record",
        title="Update Record",
        description=(
            "Update an existing record by ID. Pass 'values' as a field->value "
            "mapping. Runs as the calling user, so Odoo's access rights and "
            "record rules apply."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name (e.g. 'res.partner').",
                },
                "record_id": {
                    "type": "integer",
                    "description": "The record ID to update.",
                },
                "values": {
                    "type": "object",
                    "description": (
                        'Field values to update, e.g. {"name": "New name"}.'
                    ),
                },
            },
            "required": ["model", "record_id", "values"],
            "additionalProperties": False,
        },
        operation="write",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
    @api.model
    def update_record(self, model, record_id, values):
        """Update one record as the calling user and confirm it."""
        model_rs = self._resolve_model(model)
        self._check_op(model, "write")

        if not isinstance(values, dict) or not values:
            raise UserError(_("No values provided for record update."))

        record = self._browse_record_or_raise(model, model_rs, record_id)

        # Runs as the calling user -> ORM enforces write ACLs / record rules.
        record.write(values)
        message = _(
            "Successfully updated %(model)s record with ID %(id)s",
            model=model,
            id=record.id,
        )
        return self._write_confirmation(model, record, message)

    def _write_confirmation(self, model, record, message):
        """Read the written record back and build the confirmation tool result.

        Shared by create_record / update_record: both read the essential fields,
        build the record web URL and return the same structured confirmation --
        only ``message`` differs.
        """
        data = record.read(_ESSENTIAL_FIELDS)[0]
        url = self._record_web_url(model, record.id)
        structured = {
            "success": True,
            "record": data,
            "url": url,
            "message": message,
        }
        return _tool_result(self._format_write_text(message, data, url), structured)

    # ------------------------------------------------------------------
    # delete_record
    # ------------------------------------------------------------------
    @mcp_tool(
        name="delete_record",
        title="Delete Record",
        description=(
            "Delete a record by ID. Runs as the calling user, so Odoo's access "
            "rights and record rules apply. This action is destructive and "
            "cannot be undone."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name (e.g. 'res.partner').",
                },
                "record_id": {
                    "type": "integer",
                    "description": "The record ID to delete.",
                },
            },
            "required": ["model", "record_id"],
            "additionalProperties": False,
        },
        operation="unlink",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
    @api.model
    def delete_record(self, model, record_id):
        """Delete one record as the calling user and confirm it."""
        model_rs = self._resolve_model(model)
        self._check_op(model, "unlink")

        record = self._browse_record_or_raise(model, model_rs, record_id)

        # Capture identity before unlink; display_name may be False for models
        # without a meaningful name (e.g. mail.message).
        deleted_id = record.id
        deleted_name = record.display_name or _("ID %s", deleted_id)

        # Runs as the calling user -> ORM enforces unlink ACLs / record rules.
        record.unlink()

        message = _(
            "Successfully deleted %(model)s record '%(name)s' (ID: %(id)s)",
            model=model,
            name=deleted_name,
            id=deleted_id,
        )
        structured = {
            "success": True,
            "deleted_id": deleted_id,
            "deleted_name": deleted_name,
            "message": message,
        }
        return _tool_result(message, structured)

    # ------------------------------------------------------------------
    # call_model_method (gated by allow_method_calls)
    # ------------------------------------------------------------------
    def _validate_method_call(self, model, model_rs, method):
        """Reject anything that is not a genuine callable business method.

        Enforces the boundary for ``call_model_method``: no private
        methods, no public ``web_*`` data-access family, no hard-blocked ORM
        methods, known data-access methods stay gated by their per-op flag, and
        the rest of the generic ``BaseModel`` API is refused wholesale.
        """
        # Refuse private methods (covers dunders too -- all start with '_').
        if method.startswith("_"):
            raise UserError(_("Private methods cannot be called via MCP: %s", method))

        # Refuse method calls on the self-elevating action/cron models outright
        # (ir.actions.server.run runs server-action code as superuser; ir.cron
        # .method_direct_trigger runs a cron job as its privileged owner). These
        # stay blocked whatever ``allow_method_calls`` says; other ir.* models
        # (ir.attachment, ...) remain callable.
        if any(
            model == blocked or model.startswith(blocked + ".")
            for blocked in _METHOD_CALL_BLOCKED_MODELS
        ):
            raise AccessError(
                _(
                    "Method calls on '%s' are not permitted via MCP: its methods "
                    "run with elevated privileges.",
                    model,
                )
            )

        # Refuse the public ``web_*`` family (web_save / web_read / web_search_read
        # / ...). Defined on ``base`` via the web addon, they perform
        # CRUD/data-access (``web_save`` writes/creates) and would bypass the
        # allow_create/write/read gates. A prefix check covers future ``web_*``
        # additions too.
        if method.startswith("web_"):
            raise AccessError(
                _(
                    "Method '%s' is a data-access method; use the dedicated CRUD "
                    "tools. call_model_method is for business methods.",
                    method,
                )
            )

        # Hard-blocked ORM CRUD / data-access methods -- see
        # ``_BLOCKED_METHOD_CALLS`` for why these stay refused even with
        # ``allow_method_calls`` on.
        if method in _BLOCKED_METHOD_CALLS:
            raise AccessError(
                _(
                    "Method '%s' is a data-access method; use the dedicated CRUD "
                    "tools. call_model_method is for business methods.",
                    method,
                )
            )

        # Two-tier boundary so ``allow_method_calls`` permits a model's OWN public
        # business methods only, never the generic ORM/data-access API:
        #
        #  * KNOWN data-access methods (in ``utils.XMLRPC_METHOD_OPERATION_MAP``)
        #    stay gated by their matching per-op flag -- e.g. ``message_post``
        #    (write), ``default_get`` (read), ``action_delete`` (unlink) obey their
        #    flag rather than slipping through on ``allow_method_calls`` alone. The
        #    if/elif matters: a mapped method that clears its per-op check is a
        #    permitted data method and must NOT fall into the generic-ORM block.
        #  * Any OTHER attribute of ``BaseModel`` *or* the ``base`` registry model
        #    is a generic ORM/CRUD/recordset helper (``update``, ``mapped``,
        #    ``browse``, ``get_views``, ...), not a business method -- refuse
        #    wholesale; a denylist can't enumerate it.
        #
        # What remains -- not private, not ``web_*``, not hard-blocked, not mapped,
        # not on ``BaseModel`` or ``base`` -- is a genuine business method (e.g.
        # ``action_confirm``), gated by ``allow_method_calls`` only, as intended.
        mapped_op = utils.map_method_to_operation(method)
        if mapped_op:
            if not utils.check_model_operation_allowed(self.env, model, mapped_op):
                raise AccessError(
                    _(
                        "Method '%(method)s' maps to the '%(op)s' operation, which "
                        "is not enabled for model '%(model)s' via MCP.",
                        method=method,
                        op=mapped_op,
                        model=model,
                    )
                )
        elif hasattr(models.BaseModel, method) or hasattr(self.env["base"], method):
            # ``self.env["base"]`` also catches generic API that addons contribute
            # to the ``base`` registry model (get_views / get_view / onchange from
            # web+base, ...) -- these are NOT ``BaseModel`` Python attributes, so
            # the ``BaseModel`` check alone misses them, yet they are cross-model
            # data access (get_views leaks field/view metadata like fields_get),
            # never per-model business methods.
            raise AccessError(
                _(
                    "Method '%s' is part of the generic ORM API, not a model "
                    "business method; use the dedicated create/update/delete/search "
                    "tools. call_model_method is for business methods.",
                    method,
                )
            )

        # The attribute must be a real callable method, not a field/property.
        attr = getattr(model_rs, method, None)
        if attr is None or not callable(attr):
            raise UserError(
                _(
                    "'%(method)s' is not a callable method on model '%(model)s'.",
                    method=method,
                    model=model,
                )
            )

    @mcp_tool(
        name="call_model_method",
        title="Call Model Method",
        description=(
            "Call a public method on a model -- the workflow escape hatch for "
            "actions not covered by CRUD (e.g. 'action_confirm'). Allowed only "
            "when the model is MCP-enabled AND its 'allow_method_calls' flag is "
            "set; private (underscore-prefixed) methods are refused. Runs as the "
            "calling user, so Odoo's access rights and record rules apply. Prefer "
            "create_record / update_record / delete_record when sufficient."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name (e.g. 'sale.order').",
                },
                "method": {
                    "type": "string",
                    "description": (
                        "Public method name to call. Private (underscore-prefixed)"
                        " methods are rejected."
                    ),
                },
                "record_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": (
                        "Record IDs to call the method on. Omit to call on the "
                        "model itself (e.g. 'default_get')."
                    ),
                },
                "args": {
                    "type": "array",
                    "description": "Positional arguments for the method.",
                },
                "kwargs": {
                    "type": "object",
                    "description": "Keyword arguments for the method.",
                },
            },
            "required": ["model", "method"],
            "additionalProperties": False,
        },
        # Not a single CRUD op: gated by allow_method_calls, not _check_op.
        operation=None,
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
    @api.model
    def call_model_method(self, model, method, record_ids=None, args=None, kwargs=None):
        """Call a public model method as the calling user."""
        model_rs = self._resolve_model(model)

        # Per-model opt-in gate: enabled AND allow_method_calls=True.
        if not utils.check_model_method_allowed(self.env, model):
            raise AccessError(
                _("Method calls are not enabled for model '%s' via MCP.", model)
            )

        if not isinstance(method, str) or not method.strip():
            raise UserError(_("No method name provided."))
        method = method.strip()
        self._validate_method_call(model, model_rs, method)

        args = args or []
        kwargs = kwargs or {}
        if not isinstance(args, list):
            raise UserError(_("'args' must be a list."))
        if not isinstance(kwargs, dict):
            raise UserError(_("'kwargs' must be an object."))
        if record_ids is not None and not isinstance(record_ids, list):
            raise UserError(_("'record_ids' must be a list."))

        if record_ids:
            try:
                record_ids = [int(rid) for rid in record_ids]
            except (TypeError, ValueError) as err:
                raise UserError(_("'record_ids' must be a list of integers.")) from err
            # Bound the batch: unlike the read tools (capped via _effective_limit),
            # this path has no size limit, so a huge id list is a large IN(...) +
            # unbounded result serialization. Reuse the read cap for consistency.
            max_ids = (
                self._mcp_int_config("mcp_server.max_limit", MAX_LIMIT) or MAX_LIMIT
            )
            if len(record_ids) > max_ids:
                raise UserError(
                    _(
                        "Too many record_ids: %(count)s (max %(max)s).",
                        count=len(record_ids),
                        max=max_ids,
                    )
                )
            target = model_rs.browse(record_ids).exists()
            # Reject the whole call if ANY requested id is missing, rather than
            # silently narrowing to the survivors and reporting success -- the
            # single-record tools raise the same way, and a partial run the caller
            # can't detect is worse than a clean error.
            existing = set(target.ids)
            missing = [rid for rid in record_ids if rid not in existing]
            if missing:
                raise MissingError(
                    _(
                        "Records not found: %(model)s with IDs %(ids)s",
                        model=model,
                        ids=missing,
                    )
                )
        else:
            target = model_rs

        # Audit what was called, not the values -- args/kwargs may carry PII.
        _logger.info(
            "call_model_method: model=%s method=%s record_count=%s",
            model,
            method,
            len(target) if record_ids else 0,
        )

        # Runs as the calling user -> Odoo ACLs / record rules apply.
        raw = getattr(target, method)(*args, **kwargs)
        result = _json_safe(raw)

        message = _(
            "Successfully called %(model)s.%(method)s",
            model=model,
            method=method,
        )
        structured = {"success": True, "result": result, "message": message}
        try:
            rendered = json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            rendered = str(result)
        text = "%s\n%s" % (message, _("Result: %s", rendered))
        return _tool_result(text, structured)

    # ------------------------------------------------------------------
    # post_message (-> message_post, gated as a write op)
    # ------------------------------------------------------------------
    @mcp_tool(
        name="post_message",
        title="Post Message",
        description=(
            "Post a message to a record's chatter (mail.thread). subtype 'note' "
            "(default) logs an internal note; 'comment' notifies followers. "
            "Gated as a write operation; runs as the calling user, so Odoo's "
            "access rights and record rules apply."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name (e.g. 'res.partner').",
                },
                "record_id": {
                    "type": "integer",
                    "description": "The record ID to post to.",
                },
                "body": {
                    "type": "string",
                    "description": (
                        "Message body (plain text by default; HTML when "
                        "body_is_html=True)."
                    ),
                },
                "subject": {
                    "type": "string",
                    "description": "Optional message subject.",
                },
                "subtype": {
                    "type": "string",
                    "enum": ["note", "comment"],
                    "description": (
                        "'note' (internal, default) or 'comment' (notifies "
                        "followers)."
                    ),
                },
                "message_type": {
                    "type": "string",
                    "enum": ["comment", "notification"],
                    "description": "Message type; defaults to 'comment'.",
                },
                "partner_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional res.partner IDs to additionally notify.",
                },
                "attachment_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional existing ir.attachment IDs to link.",
                },
                "body_is_html": {
                    "type": "boolean",
                    "description": "Treat body as HTML rather than plain text.",
                },
            },
            "required": ["model", "record_id", "body"],
            "additionalProperties": False,
        },
        operation="write",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
    @api.model
    def post_message(
        self,
        model,
        record_id,
        body,
        subject=None,
        subtype="note",
        message_type="comment",
        partner_ids=None,
        attachment_ids=None,
        body_is_html=False,
    ):
        """Post a chatter message as the calling user (gated as ``write``)."""
        model_rs = self._resolve_model(model)
        self._check_op(model, "write")

        if not isinstance(body, str) or not body.strip():
            raise UserError(_("No message body provided."))

        # Clean error (not a traceback) when the model has no chatter.
        if not hasattr(model_rs, "message_post"):
            raise UserError(
                _(
                    "Model '%s' does not support chatter "
                    "(no mail.thread inheritance).",
                    model,
                )
            )

        record = self._browse_record_or_raise(model, model_rs, record_id)

        subtype = (subtype or "note").strip().lower()
        if subtype not in _SUBTYPE_XMLID:
            raise UserError(
                _("Invalid subtype '%s'; expected 'note' or 'comment'.", subtype)
            )

        # Omit partner_ids/attachment_ids when None (empty list can mean
        # "clear all" in some chatter contexts).
        post_kwargs = {
            "body": body,
            "message_type": message_type,
            "subtype_xmlid": _SUBTYPE_XMLID[subtype],
        }
        if subject:
            post_kwargs["subject"] = subject
        if partner_ids is not None:
            post_kwargs["partner_ids"] = partner_ids
        if attachment_ids is not None:
            post_kwargs["attachment_ids"] = attachment_ids
        if body_is_html:
            # Odoo 17+ escapes a plain str body -- opt-in flag preserves HTML.
            post_kwargs["body_is_html"] = True

        # Runs as the calling user -> ORM enforces write ACLs / record rules.
        message_rec = record.message_post(**post_kwargs)

        confirmation = _(
            "Posted message %(message_id)s to %(model)s record with ID %(id)s",
            message_id=message_rec.id,
            model=model,
            id=record.id,
        )
        structured = {
            "success": True,
            "message_id": message_rec.id,
            "message": confirmation,
        }
        return _tool_result(confirmation, structured)
