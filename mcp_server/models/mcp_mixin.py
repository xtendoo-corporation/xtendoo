"""Transport-agnostic MCP tool layer.

MCP tools live as ordinary methods on the :class:`McpMixin` ``AbstractModel``,
each tagged with the :func:`mcp_tool` decorator. The actual tool methods live
in separate files via ``_inherit = 'mcp.mixin'`` -- because Odoo
composes every ``_inherit`` contribution into a single registry class, an MRO
scan of the live ``mcp.mixin`` class discovers them all, no central list to
keep in sync.

Two concerns are centralised here:

* **Discovery** -- :meth:`McpMixin._get_mcp_tools` builds (and caches) the tool
  index the ``/mcp`` controller serves as ``tools/list`` and dispatches on.
* **Gating** -- :meth:`McpMixin._resolve_model` is the single chokepoint that
  validates a model name and applies the coarse MCP model gate; tools then call
  :meth:`McpMixin._check_op` for their per-operation gate. Odoo's own ACLs and
  record rules remain the real enforcement boundary.
"""

import base64

from odoo import _, api, models
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.tools import ormcache
from odoo.tools.mimetypes import guess_mimetype

from ..controllers import utils
from ..tools.uri_schema import URIParseError, parse_attachment_uri, parse_field_uri

# Mimetypes that carry textual payloads -- returned inline as ``text`` in a
# ``resources/read`` content entry instead of a base64 ``blob``. Everything
# else (images, audio, PDFs, archives, ...) is returned as a blob.
_TEXT_MIMETYPES = frozenset(
    {
        "application/json",
        "application/ld+json",
        "application/xml",
        "application/javascript",
        "application/ecmascript",
        "application/csv",
        "application/yaml",
        "application/x-yaml",
        "application/x-sh",
        "application/sql",
        "application/graphql",
        "image/svg+xml",
    }
)

# Binary-bearing field types eligible for the record-field resource scheme.
_BINARY_FIELD_TYPES = ("binary", "image")


def mcp_tool(
    name, description, input_schema, operation=None, title=None, **annotations
):
    """Mark a method as an MCP tool by attaching its metadata.

    The decorator does not wrap the method -- it only stamps a ``_mcp_tool``
    dict onto it, which :meth:`McpMixin._get_mcp_tools` later reads during the
    MRO scan. Apply it as the *outermost* decorator so the metadata lands on the
    object stored in the class ``__dict__``::

        @mcp_tool(
            name="search_records",
            title="Search Records",
            description="Search for records in a model.",
            input_schema={...},
            operation="read",
            readOnlyHint=True,
        )
        @api.model
        def search_records(self, **params):
            ...

    :param name: the MCP tool name exposed to clients.
    :param description: human/LLM-facing tool description.
    :param input_schema: explicit JSON-Schema dict for the tool's arguments.
    :param operation: model operation this tool performs, one of
        ``read``/``create``/``write``/``unlink``, or ``None`` when the tool is
        not gated on a single model operation (e.g. ``list_models``).
    :param title: optional human-readable display title surfaced top-level in
        ``tools/list``.
    :param annotations: optional MCP tool annotations (``readOnlyHint``,
        ``destructiveHint``, ...) forwarded verbatim to ``tools/list``.
    """

    def decorator(method):
        method._mcp_tool = {
            "name": name,
            "title": title,
            "description": description,
            "input_schema": input_schema,
            "operation": operation,
            "annotations": dict(annotations),
        }
        return method

    return decorator


class McpMixin(models.AbstractModel):
    """Registry + chokepoint for the native MCP tool layer."""

    _name = "mcp.mixin"
    _description = "MCP Tool Mixin"

    @api.model
    @ormcache()
    def _get_mcp_tools(self):
        """Return the tool index ``{tool_name: {...metadata}}``.

        Scans the MRO of the live ``mcp.mixin`` registry class, so tool methods
        contributed by other modules via ``_inherit = 'mcp.mixin'`` are picked
        up automatically. The first definition encountered (most-derived class)
        wins, allowing overrides.

        Cached on the registry's default ``ormcache`` pool (v18 has no ``stable``
        cache): tool definitions are code, so they only change on a module
        upgrade -- a registry-wide ``clear_cache()`` also drops them, costing
        only a cheap MRO re-scan. The returned dict holds plain metadata (no
        recordsets) and must be treated as read-only by callers.
        """
        index = {}
        seen = set()
        for klass in type(self).mro():
            for method_name, attr in vars(klass).items():
                meta = getattr(attr, "_mcp_tool", None)
                if meta is None or method_name in seen:
                    continue
                seen.add(method_name)
                if meta["name"] in index:
                    continue
                index[meta["name"]] = {
                    "method_name": method_name,
                    "title": meta.get("title"),
                    "description": meta["description"],
                    "input_schema": meta["input_schema"],
                    "operation": meta["operation"],
                    "annotations": meta["annotations"],
                }
        return index

    def _resolve_model(self, model):
        """Validate ``model`` and apply the coarse MCP model gate.

        The single chokepoint every tool routes through. Raises before any data
        is touched when the model is unknown or not MCP-enabled; per-operation
        gating is the caller's job via :meth:`_check_op`.

        :param model: technical model name (e.g. ``res.partner``).
        :return: an empty recordset for ``model`` bound to the calling user's
            environment.
        :raises UserError: when ``model`` is not a known model.
        :raises AccessError: when ``model`` is not enabled for MCP access.
        """
        if not model or model not in self.env:
            raise UserError(_("Unknown model: %s", model))
        if not utils.is_model_mcp_enabled(self.env, model):
            raise AccessError(_("Model '%s' is not enabled for MCP access.", model))
        return self.env[model]

    def _check_op(self, model, operation):
        """Apply the per-operation MCP gate for ``model``.

        Coarse opt-in check only; Odoo's ORM still enforces ``ir.model.access``
        and record rules when the operation actually runs.

        :param model: technical model name.
        :param operation: one of ``read``/``create``/``write``/``unlink``.
        :raises AccessError: when the operation is not allowed via MCP.
        """
        if not utils.check_model_operation_allowed(self.env, model, operation):
            raise AccessError(
                _(
                    "Operation '%(operation)s' is not allowed on model "
                    "'%(model)s' via MCP.",
                    operation=operation,
                    model=model,
                )
            )

    def _browse_record_or_raise(self, model, model_rs, record_id):
        """Browse a single record by id or raise a uniform ``MissingError``.

        Shared by every single-record tool (get/update/delete/post_message and
        the record-field resource) so a missing id always surfaces the same
        ``MissingError`` -- not a mix of ``UserError``/``MissingError``.
        """
        record = model_rs.browse(int(record_id)).exists()
        if not record:
            raise MissingError(
                _(
                    "Record not found: %(model)s with ID %(id)s",
                    model=model,
                    id=record_id,
                )
            )
        return record

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------
    def _read_resource(self, uri):
        """Resolve an ``odoo://`` resource URI to an MCP content entry.

        Two native schemes are supported (the ones tool output emits in place
        of inline base64):

        * ``odoo://record/{model}/{id}/{field}`` -- a binary/image field on a
          record. Gated through :meth:`_resolve_model` + :meth:`_check_op`
          (``read``); the field read runs as the calling user, so Odoo's ACLs
          and record rules still apply.
        * ``odoo://attachment/{id}`` -- an ``ir.attachment``. Gated by the MCP
          allow-list (see :meth:`_check_attachment_allowed`) *and* read as the
          calling user (no ``sudo``), so ir.attachment's own access checks bind
          it too.

        :return: a single ``resources/read`` content entry, either
            ``{uri, mimeType, text}`` (textual mimetype) or
            ``{uri, mimeType, blob}`` (base64, everything else).
        :raises UserError: unknown/unsupported URI, model or field; empty field.
        :raises MissingError: the record or attachment does not exist.
        :raises AccessError: the model/field is not MCP-enabled or ACL denies it.
        """
        if not isinstance(uri, str) or not uri.startswith("odoo://"):
            raise UserError(_("Invalid resource URI: %s", uri))

        try:
            ref = parse_field_uri(uri)
        except URIParseError:
            ref = None
        if ref is not None:
            return self._read_record_field(uri, ref)

        try:
            attachment_id = parse_attachment_uri(uri)
        except URIParseError as err:
            raise UserError(_("Unsupported resource URI: %s", uri)) from err
        return self._read_attachment(uri, attachment_id)

    def _read_record_field(self, uri, ref):
        """Read a binary/image field via the ``odoo://record/...`` scheme."""
        model_rs = self._resolve_model(ref.model)
        self._check_op(ref.model, "read")

        field = model_rs._fields.get(ref.field)
        if field is None:
            raise UserError(
                _(
                    "Unknown field '%(field)s' on model '%(model)s'.",
                    field=ref.field,
                    model=ref.model,
                )
            )
        if field.type not in _BINARY_FIELD_TYPES:
            raise UserError(
                _(
                    "Field '%(field)s' on '%(model)s' is not a binary field.",
                    field=ref.field,
                    model=ref.model,
                )
            )

        record = self._browse_record_or_raise(ref.model, model_rs, ref.record_id)

        # Runs as the calling user -> ORM enforces read ACLs / record rules.
        value = record.read([ref.field])[0].get(ref.field)
        if not value:
            raise MissingError(
                _(
                    "Field '%(field)s' on %(model)s/%(id)s holds no data.",
                    field=ref.field,
                    model=ref.model,
                    id=ref.record_id,
                )
            )

        raw = base64.b64decode(value)
        mimetype = self._record_field_mimetype(ref.model, ref.record_id, ref.field, raw)
        return self._build_content_entry(uri, mimetype, raw)

    def _read_attachment(self, uri, attachment_id):
        """Read an ``ir.attachment`` via the ``odoo://attachment/...`` scheme."""
        # No sudo: ir.attachment's own access checks bind the read to the user.
        attachment = self.env["ir.attachment"].browse(attachment_id).exists()
        if not attachment:
            raise MissingError(_("Attachment not found: %s", attachment_id))

        # MCP allow-list gate on top of Odoo's ACL (below): without this an rpc
        # key could read any attachment beyond the configured models.
        self._check_attachment_allowed(attachment)

        # Reading a stored field forces the attachment ACL check (AccessError
        # when the user may not read it).
        mimetype = attachment.mimetype
        raw = attachment.raw or b""
        if not mimetype:
            mimetype = guess_mimetype(raw, default="application/octet-stream")
        return self._build_content_entry(uri, mimetype, raw)

    def _check_attachment_allowed(self, attachment):
        """Enforce the MCP allow-list for an attachment read.

        Keeps attachment access inside the per-model opt-in: the read is
        permitted only when *either* ``ir.attachment`` itself is MCP-enabled
        for read (expose attachments broadly), *or* the attachment's parent
        record model (``res_model``) is MCP-enabled for read (the attachment
        rides its parent's exposure). Odoo's own ACL still applies on top.

        :raises AccessError: when neither rule grants access.
        """
        if utils.check_model_operation_allowed(self.env, "ir.attachment", "read"):
            return
        res_model = attachment.res_model
        if res_model and utils.check_model_operation_allowed(
            self.env, res_model, "read"
        ):
            return
        raise AccessError(
            _(
                "Attachment access via MCP requires 'ir.attachment' or the "
                "attachment's parent model to be MCP-enabled for read."
            )
        )

    def _record_field_mimetype(self, model, record_id, field, raw):
        """Best-effort mimetype for a record binary field.

        Prefer the backing ``ir.attachment`` (for attachment-stored fields such
        as ``image_1920``); otherwise sniff the bytes. The explicit ``res_field``
        condition disables the ORM's default res_field filtering, and the search
        runs as the user (field access already granted by the field read).
        """
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", model),
                ("res_id", "=", record_id),
                ("res_field", "=", field),
            ],
            limit=1,
        )
        if attachment and attachment.mimetype:
            return attachment.mimetype
        return guess_mimetype(raw, default="application/octet-stream")

    def _build_content_entry(self, uri, mimetype, raw):
        """Build one ``resources/read`` content entry from raw bytes.

        Textual mimetypes are decoded inline as ``text``; everything else
        (images, audio, PDFs, ...) is returned as a base64 ``blob``.
        """
        mimetype = mimetype or "application/octet-stream"
        if self._is_text_mimetype(mimetype):
            return {
                "uri": uri,
                "mimeType": mimetype,
                "text": raw.decode("utf-8", errors="replace"),
            }
        return {
            "uri": uri,
            "mimeType": mimetype,
            "blob": base64.b64encode(raw).decode("ascii"),
        }

    @staticmethod
    def _is_text_mimetype(mimetype):
        """Whether ``mimetype`` denotes textual (inline-able) content."""
        base = (mimetype or "").split(";", 1)[0].strip().lower()
        if not base:
            return False
        if base.startswith("text/"):
            return True
        if base in _TEXT_MIMETYPES:
            return True
        return base.endswith("+json") or base.endswith("+xml")
