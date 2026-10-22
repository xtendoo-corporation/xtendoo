import re
from contextlib import suppress

from odoo import api, models, tools
from odoo.exceptions import AccessError, MissingError
from odoo.tools import file_open

from ..tools.errors import XtdAiToolError
from ..tools.schema import check_tool_schema

TEXT_LIMIT = 300
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class XtdAiToolbox(models.AbstractModel):
    """Base of every AI toolbox (CONTRACT §6).

    Modules add tools by defining an abstract model that inherits from this one
    and decorating methods with ``@xtd_ai_tool``. This class holds the registry
    and the helpers; it defines no tool itself.
    """

    _name = "xtd.ai.toolbox"
    _description = "AI tools: base"

    # {"skill_name": "data/skills/skill_name.md"}, relative to the declaring module.
    _xtd_ai_skills = {}
    # Test-only toolboxes are registered only with --test-enable.
    _xtd_ai_test_only = False

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------
    def _register_hook(self):
        super()._register_hook()
        # Build the registry once at startup: duplicated tool names or invalid
        # declarations must block the boot with a clear error.
        self._xtd_ai_tools()

    @api.model
    def _xtd_ai_tools(self):
        """Return ``{tool_name: meta}`` of every installed tool (cached per
        registry)."""
        cache = getattr(self.pool, "_xtd_ai_tool_cache", None)
        if cache is not None:
            return cache
        base = self.pool["xtd.ai.toolbox"]
        found = {}
        for model_name in sorted(self.pool.keys()):
            cls = self.pool[model_name]
            if model_name == "xtd.ai.toolbox" or not issubclass(cls, base):
                continue
            if cls._xtd_ai_test_only and not tools.config["test_enable"]:
                continue
            seen_attrs = set()
            for klass in cls.__mro__:
                for attr, member in vars(klass).items():
                    meta = getattr(member, "_xtd_ai_tool", None)
                    if meta is None or attr in seen_attrs:
                        continue
                    seen_attrs.add(attr)
                    previous = found.get(meta["name"])
                    if previous is not None:
                        if previous["_func"] is member:
                            continue  # same function seen through another toolbox model
                        raise ValueError(
                            f"Duplicated AI tool name {meta['name']!r}: "
                            f"{previous['model']}.{previous['attr']} and "
                            f"{model_name}.{attr}"
                        )
                    found[meta["name"]] = meta | {
                        "model": model_name,
                        "attr": attr,
                        "_func": member,
                    }
        self.pool._xtd_ai_tool_cache = found
        return found

    @api.model
    def _xtd_ai_skill_files(self):
        """Return ``{skill: (module, relative_path)}`` for the installed skills."""
        base = self.pool["xtd.ai.toolbox"]
        result = {}
        for model_name in sorted(self.pool.keys()):
            cls = self.pool[model_name]
            if not issubclass(cls, base) or model_name == "xtd.ai.toolbox":
                continue
            if cls._xtd_ai_test_only and not tools.config["test_enable"]:
                continue
            for klass in cls.__mro__:
                skills = vars(klass).get("_xtd_ai_skills")
                parts = klass.__module__.split(".")
                if skills and len(parts) > 2 and parts[:2] == ["odoo", "addons"]:
                    for skill, path in skills.items():
                        result.setdefault(skill, (parts[2], path))
        return result

    @api.model
    def _xtd_ai_read_skill(self, skill):
        files = self._xtd_ai_skill_files()
        if skill not in files:
            raise XtdAiToolError(
                "not_found", self.env._("Skill desconocida: %s", skill)
            )
        module, path = files[skill]
        if ".." in path or path.startswith("/"):
            raise XtdAiToolError("internal", "Invalid skill path")
        with file_open(f"{module}/{path}", "r", filter_ext=(".md",)) as handle:
            return handle.read()

    @api.model
    def _xtd_ai_schema(self, tool):
        schema = tool["input_schema"]
        if callable(schema):
            schema = schema(self)
            check_tool_schema(tool["name"], schema)
        return schema

    @api.model
    def _xtd_ai_tool_visible(self, tool):
        for model in tool["requires"]:
            if model not in self.env:
                return False
        groups = tool["groups"]
        if not groups:
            return True
        user = self.env.user
        for group in groups:
            try:
                if user.has_group(group):
                    return True
            except Exception:  # group not installed: ignore it
                continue
        return False

    @api.model
    def _xtd_ai_visible_tools(self):
        return {
            name: tool
            for name, tool in sorted(self._xtd_ai_tools().items())
            if self._xtd_ai_tool_visible(tool)
        }

    @api.model
    def _xtd_ai_tool_descriptor(self, tool):
        """MCP ``Tool`` object for ``tools/list``."""
        return {
            "name": tool["name"],
            "title": tool["title"],
            "description": tool["description"],
            "inputSchema": self._xtd_ai_schema(tool),
            "annotations": {
                "readOnlyHint": tool["kind"] == "read",
                "destructiveHint": False,
                "xtdKind": tool["kind"],
                "xtdSkill": tool["skill"],
            },
        }

    # ------------------------------------------------------------------
    # Execution (shared by direct calls and confirmed pending actions)
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_exec_context(self, run_id, cids, lang=None, tz=None):
        """Context of every tool execution (CONTRACT §3 and §7)."""
        context = {
            "allowed_company_ids": list(cids),
            "xtd_ai_run": run_id,
            "mail_auto_subscribe_no_notify": True,
            "mail_notify_force_send": False,
        }
        if lang:
            context["lang"] = lang
        if tz:
            context["tz"] = tz
        return context

    @api.model
    def _xtd_ai_execute(self, tool, args):
        """Run a tool body in a savepoint and normalise its result.

        Exceptions propagate after rolling the savepoint back.
        """
        if self.env.su:
            raise RuntimeError("AI tools must never run in superuser mode")
        if not self.env.context.get("xtd_ai_run"):
            raise RuntimeError("AI tools must run with xtd_ai_run in the context")
        toolbox = self.env[tool["model"]]
        with self.env.cr.savepoint():
            result = getattr(toolbox, tool["attr"])(args)
        return self._xtd_ai_normalize_result(result)

    @api.model
    def _xtd_ai_preview(self, tool, args):
        """Run the preview (reads only): any side effect is rolled back."""
        toolbox = self.env[tool["model"]]
        sentinel = _PreviewDone()
        preview = None
        with suppress(_PreviewDone), self.env.cr.savepoint():
            preview = getattr(toolbox, tool["preview"])(args)
            raise sentinel
        if not isinstance(preview, dict) or not isinstance(preview.get("summary"), str):
            raise XtdAiToolError("internal", "Invalid preview")
        preview.setdefault("lines", [])
        return preview

    @api.model
    def _xtd_ai_ref(self, record):
        try:
            name = (record.display_name or "")[:100]
        except Exception:
            name = ""
        return {"model": record._name, "id": record.id, "name": name}

    @api.model
    def _xtd_ai_normalize_result(self, result):
        if not isinstance(result, dict):
            result = {"data": result}
        refs = []
        records = result.get("records") or []
        if isinstance(records, models.BaseModel):
            records = [records]
        for item in records:
            if isinstance(item, models.BaseModel):
                refs.extend(self._xtd_ai_ref(r) for r in item if r.id)
            elif isinstance(item, dict) and "model" in item and "id" in item:
                refs.append(
                    {
                        "model": item["model"],
                        "id": item["id"],
                        "name": item.get("name", ""),
                    }
                )
        return {"data": result.get("data", {}), "records": refs}

    # ------------------------------------------------------------------
    # Helpers for tools (CONTRACT §6)
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_text(self, value):
        """Wrap free text coming from records as untrusted data, cut to 300 chars."""
        if value is None or value is False:
            return None
        text = str(value)
        return {
            "untrusted_text": text[:TEXT_LIMIT],
            "truncated": len(text) > TEXT_LIMIT,
        }

    @api.model
    def _xtd_ai_money(self, amount, currency):
        """``{"amount": 123.45, "currency": "EUR"}``; ``currency`` is a record or a
        code."""
        if isinstance(currency, models.BaseModel):
            digits = currency.decimal_places if currency else 2
            code = currency.name if currency else None
        else:
            digits, code = 2, currency
        return {"amount": round(float(amount or 0.0), digits), "currency": code}

    @api.model
    def _xtd_ai_limit(self, value=None):
        """Clamp a requested row limit to ``1..200`` (default 50)."""
        if not isinstance(value, int) or isinstance(value, bool):
            return DEFAULT_LIMIT
        return max(1, min(value, MAX_LIMIT))

    @api.model
    def _xtd_ai_list(self, rows, total=None, limit=None):
        """Cap a list for ``data``: ``{"items": [...], "truncated": bool, "total":
        N}``."""
        limit = self._xtd_ai_limit(limit)
        total = len(rows) if total is None else total
        return {"items": list(rows)[:limit], "truncated": total > limit, "total": total}

    @api.model
    def _xtd_ai_resolve(self, model, name_or_id, domain=None):
        """Return the single record matching an id or a name.

        Uses the user's ORM rights. Raises ``XtdAiToolError`` ``not_found`` or
        ``ambiguous`` (``data.candidates`` with id and name).
        """
        env_model = self.env[model]
        domain = list(domain or [])
        if isinstance(name_or_id, bool) or name_or_id in (None, ""):
            raise XtdAiToolError(
                "not_found", self.env._("Falta el identificador o nombre.")
            )
        if isinstance(name_or_id, int) or (
            isinstance(name_or_id, str)
            and re.fullmatch(r"\d{1,12}", name_or_id.strip())
        ):
            record = env_model.search([("id", "=", int(name_or_id))] + domain, limit=1)
            if not record:
                raise XtdAiToolError(
                    "not_found",
                    self.env._("No se ha encontrado el registro %s.", name_or_id),
                )
            return record
        name = str(name_or_id).strip()
        candidates = env_model.search(
            domain + [("display_name", "ilike", name)], limit=6, order="id"
        )
        if not candidates:
            raise XtdAiToolError(
                "not_found", self.env._("No se ha encontrado «%s».", name)
            )
        if len(candidates) > 1:
            exact = candidates.filtered(
                lambda r: (r.display_name or "").lower() == name.lower()
            )
            if len(exact) == 1:
                return exact
            raise XtdAiToolError(
                "ambiguous",
                self.env._(
                    "Hay varios resultados para «%s». Pregunta al usuario cuál es.",
                    name,
                ),
                data={
                    "candidates": [
                        {"id": c.id, "name": self._xtd_ai_text(c.display_name)}
                        for c in candidates[:5]
                    ]
                },
            )
        return candidates

    @api.model
    def _xtd_ai_conversation_attachment(self, att_id):
        """The chat attachment ``att_id`` of the current run's conversation.

        For write tools that accept ``attachment_id`` (CONTRACT §14). Uses the
        user's environment (the ORM rules already limit messages and
        conversations to the user's own); raises ``not_found`` for anything
        that is not an attachment linked to a message of this conversation.
        """
        not_found = XtdAiToolError(
            "not_found", self.env._("No se ha encontrado el adjunto %s.", att_id)
        )
        run_id = self.env.context.get("xtd_ai_run")
        if not run_id or isinstance(att_id, bool) or not isinstance(att_id, int):
            raise not_found
        conversation = self.env["xtd.ai.run"].browse(run_id).conversation_id
        attachment = self.env["ir.attachment"].browse(att_id)
        try:
            ok = (
                conversation
                and attachment.exists()
                and attachment.res_model == "xtd.ai.conversation"
                and attachment.res_id == conversation.id
                and self.env["xtd.ai.message"].search_count(
                    [
                        ("conversation_id", "=", conversation.id),
                        ("attachment_ids", "in", [att_id]),
                    ]
                )
            )
            if ok:
                attachment.check_access("read")
        except (AccessError, MissingError):
            ok = False
        if not ok:
            raise not_found
        return attachment


class _PreviewDone(Exception):
    """Internal sentinel used to roll a preview savepoint back."""
