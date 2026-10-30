"""Generic tools ``create_record`` and ``update_record`` (§6.5).

Both work only on what ``xtd.ai.record.registry`` declares, with the user's
own ORM rights and record rules. The level of each call (do it and offer
"Deshacer", or a card) comes from the risk of the fields it touches.
"""

from odoo import models

from ..tools import xtd_ai_tool
from ..tools.errors import XtdAiToolError
from .xtd_ai_policy import max_level


def _changes_schema(toolbox, operation):
    registry = toolbox.env["xtd.ai.record.registry"]
    specs = registry._xtd_ai_specs()
    allowed = registry._xtd_ai_models(operation)
    is_update = operation == "update"
    hint = "; ".join(
        f"{model}: {', '.join(registry._xtd_ai_allowed(specs[model], is_update))}"
        for model in allowed
    )
    item = {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": f"Nombre técnico del campo. Permitidos: {hint}.",
            },
            "value": {
                "type": "string",
                "description": (
                    "Valor como texto: número con punto, fecha AAAA-MM-DD, sí/no, "
                    "nombre o id para relaciones; listas separadas por comas "
                    "(«+X» añade, «-X» quita). Vacío para borrar el valor."
                ),
            },
        },
        "required": ["field", "value"],
        "additionalProperties": False,
    }
    return allowed, {"type": "array", "items": item, "minItems": 1, "maxItems": 15}


def _create_schema(toolbox):
    allowed, changes = _changes_schema(toolbox, "create")
    specs = toolbox.env["xtd.ai.record.registry"]._xtd_ai_specs()
    properties = {
        "model": {"type": "string", "enum": allowed or ["product.template"]},
        "values": changes,
    }
    with_attachment = [m for m in allowed if specs[m].get("attachment")]
    if with_attachment:
        properties["attachment_id"] = {
            "type": "integer",
            "description": (
                "Id del adjunto del chat ([Adjunto: … (id N)]) que se guarda en el "
                f"registro nuevo. Solo para: {', '.join(with_attachment)}."
            ),
        }
    return {
        "type": "object",
        "properties": properties,
        "required": ["model", "values"],
        "additionalProperties": False,
    }


def _update_schema(toolbox):
    allowed, changes = _changes_schema(toolbox, "update")
    return {
        "type": "object",
        "properties": {
            "model": {"type": "string", "enum": allowed or ["res.partner"]},
            "record": {
                "type": "string",
                "description": "Id del registro (preferible) o su nombre exacto.",
            },
            "changes": changes,
        },
        "required": ["model", "record", "changes"],
        "additionalProperties": False,
    }


class XtdAiToolboxRecords(models.AbstractModel):
    _name = "xtd.ai.toolbox.records"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: generic create and update"

    _xtd_ai_skills = {"productos": "data/skills/productos.md"}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="create_record",
        title="Crear registro",
        description=(
            "Crea un registro permitido: productos (product.template; antes "
            "search_products), tareas (project.task), partes de horas PROPIOS "
            "(account.analytic.line) y gastos PROPIOS (hr.expense), según lo "
            "instalado. Pasa los campos en `values` como pares campo/valor. Si "
            "puede estar repetido, lleva impuestos o es un gasto, queda una "
            "tarjeta para confirmar; si no, se crea y el usuario puede deshacerlo. "
            "Carga antes la skill del área."
        ),
        input_schema=_create_schema,
        kind="create",
        preview="_xtd_ai_preview_create_record",
        policy="_xtd_ai_policy_create_record",
        visible="_xtd_ai_visible_create_record",
    )
    def tool_create_record(self, args):
        registry = self.env["xtd.ai.record.registry"]
        model = args["model"]
        attachment = self._xtd_ai_record_attachment(model, args)
        vals, _info = registry._xtd_ai_prepare(model, args["values"])
        record = self.env[model].create(vals)
        if attachment:
            # a copy linked to the new record: the chat keeps its own
            attachment.copy({"res_model": model, "res_id": record.id})
        return {
            "data": {
                "model": model,
                "id": record.id,
                "name": self._xtd_ai_text(record.display_name),
            },
            "records": record,
        }

    def _xtd_ai_record_attachment(self, model, args):
        """The chat attachment ``attachment_id`` for a model that accepts one."""
        if args.get("attachment_id") in (None, False):
            return None
        spec = self.env["xtd.ai.record.registry"]._xtd_ai_spec(model, "create")
        if not spec.get("attachment"):
            raise XtdAiToolError(
                "validation",
                self.env._("Este tipo de registro no admite adjuntos."),
            )
        return self._xtd_ai_conversation_attachment(args["attachment_id"])

    def _xtd_ai_visible_create_record(self):
        return bool(self.env["xtd.ai.record.registry"]._xtd_ai_models("create"))

    def _xtd_ai_policy_create_record(self, args):
        registry = self.env["xtd.ai.record.registry"]
        model = args["model"]
        spec = registry._xtd_ai_spec(model, "create")
        vals, info = registry._xtd_ai_prepare(model, args["values"])
        policy = self.env["xtd.ai.policy"]
        level = policy._xtd_ai_level(spec.get("create_class") or "create_master")
        if any(i["risk"] == "money" for i in info.values()):
            level = max_level(level, policy._xtd_ai_level("edit_money"))
        if registry._xtd_ai_duplicates(model, spec, vals):
            level = max_level(level, "N2")
        if self._xtd_ai_record_attachment(model, args):
            # the values were read from a document: text from outside (§6.1)
            level = max_level(level, "N2")
        return level

    def _xtd_ai_preview_create_record(self, args):
        registry = self.env["xtd.ai.record.registry"]
        model = args["model"]
        spec = registry._xtd_ai_spec(model, "create")
        vals, info = registry._xtd_ai_prepare(model, args["values"])
        attachment = self._xtd_ai_record_attachment(model, args)
        duplicates = registry._xtd_ai_duplicates(model, spec, vals)
        name = vals.get("name") or ""
        summary = self.env._(
            "Crear %(label)s «%(name)s»", label=spec["label"], name=name
        )
        if duplicates:
            summary += " - " + self.env._("posibles duplicados: %s", len(duplicates))
        lines = [
            {
                "field": item["label"],
                "value": self._xtd_ai_text(
                    registry._xtd_ai_display(model, fname, item["value"])
                ),
            }
            for fname, item in info.items()
        ]
        if attachment:
            lines.append(
                {
                    "field": self.env._("Adjunto"),
                    "value": self._xtd_ai_text(attachment.name),
                }
            )
        lines += [
            {
                "field": self.env._("Ya existe"),
                "value": self._xtd_ai_text(f"{dup.display_name} (id {dup.id})"),
            }
            for dup in duplicates
        ]
        lines += [
            {"field": self.env._("Efecto"), "value": effect}
            for effect in registry._xtd_ai_effects(spec, self.env[model], vals)
        ]
        return {
            "summary": summary,
            "lines": lines,
            "duplicates": [{"id": d.id, "name": d.display_name} for d in duplicates],
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="update_record",
        title="Modificar registro",
        description=(
            "Modifica campos permitidos de un registro existente: productos, "
            "contactos (no bancos ni datos fiscales sin tarjeta), oportunidades "
            "abiertas (crm.lead), tareas y partes de horas propios, gastos "
            "propios en borrador y borradores de pedidos, facturas, asientos y "
            "sus líneas (solo en borrador). Usa el "
            "id que devuelven get_* o search_*. Los cambios de bajo riesgo se "
            "hacen y el usuario puede deshacerlos; precios, descuentos altos, "
            "impuestos, NIF y email piden confirmación con «antes → después». "
            "Un campo no permitido se rechaza."
        ),
        input_schema=_update_schema,
        kind="draft",
        preview="_xtd_ai_preview_update_record",
        policy="_xtd_ai_policy_update_record",
        visible="_xtd_ai_visible_update_record",
    )
    def tool_update_record(self, args):
        registry = self.env["xtd.ai.record.registry"]
        model = args["model"]
        record = self._xtd_ai_update_target(model, args["record"])
        vals, _info = registry._xtd_ai_prepare(model, args["changes"], record)
        fnames = list(vals)
        before = registry._xtd_ai_snapshot(record, fnames)
        # write() may add keys to the dict it receives: give it a copy
        record.with_context(_xtd_ai_registry_write=True).write(dict(vals))
        after = registry._xtd_ai_snapshot(record, fnames)
        changed = [
            f
            for f in fnames
            if not registry._xtd_ai_same(model, f, before[f], after[f])
        ]
        rows = [
            {
                "field": fname,
                "before": self._xtd_ai_text(
                    registry._xtd_ai_display(model, fname, before[fname])
                ),
                "after": self._xtd_ai_text(
                    registry._xtd_ai_display(model, fname, after[fname])
                ),
            }
            for fname in changed
        ]
        # always present (maybe empty): the record was edited, not created
        ref = self._xtd_ai_ref(record) | {
            "undo_edit": {
                "before": {f: before[f] for f in changed},
                "after": {f: after[f] for f in changed},
            }
        }
        return {
            "data": {
                "model": model,
                "id": record.id,
                "changed": rows,
                "unchanged": [f for f in fnames if f not in changed],
            },
            "records": [ref],
        }

    def _xtd_ai_visible_update_record(self):
        return bool(self.env["xtd.ai.record.registry"]._xtd_ai_models("update"))

    def _xtd_ai_update_target(self, model, name_or_id):
        registry = self.env["xtd.ai.record.registry"]
        spec = registry._xtd_ai_spec(model, "update")
        domain = registry._xtd_ai_record_domain(model, spec)
        try:
            record = self._xtd_ai_resolve(model, name_or_id, domain)
        except XtdAiToolError as exc:
            if exc.code != "not_found" or not domain:
                raise
            if self._xtd_ai_resolve_or_none(model, name_or_id):
                raise XtdAiToolError(
                    "forbidden",
                    self.env._(
                        "Ese %s no se puede modificar desde el agente (solo "
                        "borradores y datos permitidos).",
                        spec["label"],
                    ),
                ) from None
            raise
        record.check_access("write")
        return record

    def _xtd_ai_resolve_or_none(self, model, name_or_id):
        try:
            return self._xtd_ai_resolve(model, name_or_id)
        except XtdAiToolError:
            return None

    def _xtd_ai_policy_update_record(self, args):
        registry = self.env["xtd.ai.record.registry"]
        model = args["model"]
        spec = registry._xtd_ai_spec(model, "update")
        record = self._xtd_ai_update_target(model, args["record"])
        vals, info = registry._xtd_ai_prepare(model, args["changes"], record)
        policy = self.env["xtd.ai.policy"]
        money = any(i["risk"] == "money" for i in info.values())
        level = policy._xtd_ai_level("edit_money" if money else "edit_low")
        if registry._xtd_ai_duplicates(model, spec, vals, record):
            level = max_level(level, "N2")
        if registry._xtd_ai_is_external(model, record):
            level = max_level(level, "N2")
        return level

    def _xtd_ai_preview_update_record(self, args):
        registry = self.env["xtd.ai.record.registry"]
        model = args["model"]
        spec = registry._xtd_ai_spec(model, "update")
        record = self._xtd_ai_update_target(model, args["record"])
        vals, info = registry._xtd_ai_prepare(model, args["changes"], record)
        before = registry._xtd_ai_snapshot(record, list(vals))
        duplicates = registry._xtd_ai_duplicates(model, spec, vals, record)
        summary = self.env._(
            "Modificar %(label)s «%(name)s»",
            label=spec["label"],
            name=(record.display_name or "")[:80],
        )
        lines = [
            {
                "field": item["label"],
                "value": self._xtd_ai_text(
                    registry._xtd_ai_display(model, fname, before[fname])
                    + " → "
                    + registry._xtd_ai_display(model, fname, item["value"])
                ),
            }
            for fname, item in info.items()
        ]
        lines += [
            {
                "field": self.env._("Ya existe"),
                "value": self._xtd_ai_text(f"{dup.display_name} (id {dup.id})"),
            }
            for dup in duplicates
        ]
        lines += [
            {"field": self.env._("Efecto"), "value": effect}
            for effect in registry._xtd_ai_effects(spec, record, vals)
        ]
        return {"summary": summary, "lines": lines}
