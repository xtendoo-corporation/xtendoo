"""Undo of what the agent created: "Hecho · Deshacer" in the chat.

The user runs it from their web session with their own rights, like a card
confirmation: ``unlink`` of an untouched draft, never ``sudo``. A record stops
being undoable as soon as it is no longer an intact draft (posted, referenced by
other records, changed by someone else, or older than the time window).
"""

import logging
import re
from datetime import timedelta

from odoo import SUPERUSER_ID, Command, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

UNDO_MODELS = (
    "res.partner",
    "sale.order",
    "purchase.order",
    "account.move",
    "crm.lead",
    "product.template",
    "project.task",
    "account.analytic.line",
    "hr.expense",
)
UNDO_LINE_MODELS = {"sale.order": "order_line"}
DEFAULT_WINDOW_MINUTES = 120
# Users without the right to delete get the closest thing they may do: cancel the
# draft quotation, archive the contact or opportunity (still their own rights).
UNLINK_FALLBACKS = {
    "sale.order": "cancel",
    "res.partner": "archive",
    "crm.lead": "archive",
    "product.template": "archive",
    "project.task": "archive",
}
# Documents the agent creates; anything else (posted, refunds...) is not undoable
_MOVE_TYPES = ("out_invoice", "in_invoice", "entry")
# Models that point at a partner: any of them makes the contact not undoable
_PARTNER_REFERENCES = (
    ("sale.order", "partner_id"),
    ("purchase.order", "partner_id"),
    ("account.move", "partner_id"),
    ("crm.lead", "partner_id"),
    ("res.partner", "parent_id"),
)


class XtdAiUndo(models.AbstractModel):
    _name = "xtd.ai.undo"
    _description = "AI agent undo"

    @api.model
    def _xtd_ai_undo_window(self):
        # sudo: system parameter; users cannot read ir.config_parameter
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtd_ai.undo_window_minutes", DEFAULT_WINDOW_MINUTES)
        )
        try:
            return timedelta(minutes=max(1, int(value)))
        except (TypeError, ValueError):
            return timedelta(minutes=DEFAULT_WINDOW_MINUTES)

    @api.model
    def _xtd_ai_undo_reason(self, record, since=None):
        """Why ``record`` cannot be undone, or ``None`` if it can.

        ``since``: when the run (or card) that made it started; a record created
        before it was only touched by the agent, not created, so it is not undone.
        """
        user = self.env.user
        if self.env.su or self.env.context.get("xtd_ai_run"):
            return self.env._("Operación no permitida desde el agente.")
        if record._name not in UNDO_MODELS:
            return self.env._("Este tipo de registro no se puede deshacer.")
        record = record.exists()
        if not record:
            return self.env._("Ya no existe.")
        if self._xtd_ai_undo_mode(record) is None:
            return self.env._("No tienes permiso para borrarlo.")
        # system writes (computed fields, internal syncs) are not another person
        if record.create_uid != user or record.write_uid.id not in (
            user.id,
            SUPERUSER_ID,
        ):
            return self.env._("Alguien lo ha modificado después.")
        if since and record.create_date < since:
            return self.env._("No lo ha creado el agente en esta petición.")
        if fields.Datetime.now() - record.create_date > self._xtd_ai_undo_window():
            return self.env._("Ha pasado demasiado tiempo para deshacerlo.")
        return getattr(self, f"_xtd_ai_undo_reason_{record._name.replace('.', '_')}")(
            record
        )

    @api.model
    def _xtd_ai_undo_mode(self, record):
        """``unlink``, or the fallback the user's rights allow, or ``None``."""
        try:
            record.check_access("unlink")
            return "unlink"
        except AccessError:
            mode = UNLINK_FALLBACKS.get(record._name)
        if mode:
            try:
                record.check_access("write")
                return mode
            except AccessError:
                return None
        return None

    @api.model
    def _xtd_ai_undo_done(self, record):
        """Already undone by archiving or cancelling it (it still exists)."""
        if record._name == "sale.order":
            return record.state == "cancel"
        return "active" in record._fields and not record.active

    def _xtd_ai_undo_reason_res_partner(self, partner):
        if not partner.active or partner.user_ids:
            return self.env._("El contacto ya se usa.")
        for model, field in _PARTNER_REFERENCES:
            if model not in self.env:
                continue
            try:
                used = self.env[model].search_count([(field, "=", partner.id)], limit=1)
            except AccessError:
                # not visible to the user: the database refuses the delete if used
                continue
            if used:
                return self.env._("Otros registros usan este contacto.")
        return None

    def _xtd_ai_undo_reason_sale_order(self, order):
        if order.state != "draft" or order.invoice_ids:
            return self.env._("El presupuesto ya no es un borrador intacto.")
        return None

    def _xtd_ai_undo_reason_purchase_order(self, order):
        if order.state != "draft" or order.invoice_ids:
            return self.env._("La petición de oferta ya no es un borrador intacto.")
        return None

    def _xtd_ai_undo_reason_account_move(self, move):
        if (
            move.state != "draft"
            or move.posted_before
            or move.move_type not in _MOVE_TYPES
            or move.matched_payment_ids
            or move.reversal_move_ids
        ):
            return self.env._("El asiento o la factura ya no es un borrador intacto.")
        return None

    def _xtd_ai_undo_reason_product_template(self, template):
        if not template.active:
            return self.env._("El producto ya está archivado.")
        variants = template.with_context(active_test=False).product_variant_ids
        for model in (
            "sale.order.line",
            "purchase.order.line",
            "account.move.line",
            "stock.move",
        ):
            if model not in self.env:
                continue
            try:
                used = self.env[model].search_count(
                    [("product_id", "in", variants.ids)], limit=1
                )
            except AccessError:
                continue
            if used:
                return self.env._("El producto ya se usa en otros documentos.")
        return None

    def _xtd_ai_undo_reason_crm_lead(self, lead):
        if not lead.active or ("order_ids" in lead._fields and lead.order_ids):
            return self.env._("La oportunidad ya no es un borrador intacto.")
        return None

    def _xtd_ai_undo_reason_project_task(self, task):
        if not task.active or task.child_ids:
            return self.env._("La tarea ya no es un borrador intacto.")
        if "timesheet_ids" in task._fields and task.timesheet_ids:
            return self.env._("La tarea ya tiene horas imputadas.")
        return None

    def _xtd_ai_undo_reason_account_analytic_line(self, line):
        if line.user_id != self.env.user:
            return self.env._("Ese parte no es tuyo.")
        if "validated" in line._fields and line.validated:
            return self.env._("El parte ya está validado.")
        return None

    def _xtd_ai_undo_reason_hr_expense(self, expense):
        if expense.state != "draft" or expense.account_move_id:
            return self.env._("El gasto ya no está en borrador.")
        return None

    @api.model
    def _xtd_ai_undo_lines_reason(self, order, line_ids, since=None):
        """Why the lines the agent added to ``order`` cannot be removed."""
        field = UNDO_LINE_MODELS.get(order._name)
        if not field:
            return self.env._("Este tipo de registro no se puede deshacer.")
        lines = order[field].filtered(lambda line: line.id in set(line_ids))
        if not lines or len(lines) != len(set(line_ids)):
            return self.env._("Ya no existen.")
        if order.state != "draft":
            return self.env._("El presupuesto ya no es un borrador.")
        try:
            lines.check_access("unlink")
        except AccessError:
            return self.env._("No tienes permiso para borrarlas.")
        for line in lines:
            if line.create_uid != self.env.user or line.write_uid.id not in (
                self.env.uid,
                SUPERUSER_ID,
            ):
                return self.env._("Alguien las ha modificado después.")
            if since and line.create_date < since:
                return self.env._("No las ha creado el agente en esta petición.")
            if fields.Datetime.now() - line.create_date > self._xtd_ai_undo_window():
                return self.env._("Ha pasado demasiado tiempo para deshacerlo.")
        return None

    @api.model
    def _xtd_ai_undo_state(self, model, res_id, since=None, line_ids=None):
        """``available``, ``undone`` or ``None`` (nothing to offer) for the chat."""
        if model not in UNDO_MODELS or model not in self.env:
            return None
        record = self.env[model].browse(res_id).exists()
        if not record:
            return None if line_ids else "undone"
        if not line_ids and self._xtd_ai_undo_done(record):
            return "undone"
        if line_ids:
            return (
                "available"
                if self._xtd_ai_undo_lines_reason(record, line_ids, since) is None
                else None
            )
        return "available" if self._xtd_ai_undo_reason(record, since) is None else None

    @api.model
    def _xtd_ai_undo(self, model, res_id, since=None, line_ids=None, run=None):
        """Delete the draft (or the added lines) as the session user and audit it.

        :returns: ``{"undone": True, "mode"}`` or ``{"undone": False, "reason": text}``;
            a refusal is data (not an exception) so its audit row is kept.
        :raises: ``UserError`` when the record is already gone.
        """
        record = (
            self.env[model].browse(res_id).exists() if model in UNDO_MODELS else None
        )
        if not record:
            raise UserError(self.env._("Ya no existe o no se puede deshacer."))
        reason = (
            self._xtd_ai_undo_lines_reason(record, line_ids, since)
            if line_ids
            else self._xtd_ai_undo_reason(record, since)
        )
        refs = [
            {"model": model, "id": res_id, "name": (record.display_name or "")[:100]}
        ]
        outcome, code, mode = "ok", None, "unlink"
        if not reason:
            try:
                with self.env.cr.savepoint():
                    mode = "unlink" if line_ids else self._xtd_ai_undo_mode(record)
                    target = (
                        record[UNDO_LINE_MODELS[model]].filtered(
                            lambda line: line.id in set(line_ids)
                        )
                        if line_ids
                        else record
                    )
                    if mode == "cancel":
                        target._action_cancel()
                    elif mode == "archive":
                        target.write({"active": False})
                    else:
                        if model == "purchase.order" and not line_ids:
                            # Odoo only deletes cancelled purchase orders
                            target.button_cancel()
                        target.unlink()
            except Exception as exc:  # FK or business constraint: not undoable
                _logger.info("Undo of %s,%s refused: %s", model, res_id, exc)
                reason = self.env._("Otros registros dependen de él.")
        if reason:
            outcome, code = "denied", "not_undoable"
        self.env["xtd.ai.audit"]._xtd_ai_log(
            "undo",
            outcome,
            run_id=run.id if run else None,
            user_id=self.env.uid,
            company_id=self.env.company.id,
            tool_name="undo_lines" if line_ids else "undo",
            arguments={
                "model": model,
                "id": res_id,
                "lines": line_ids or [],
                "mode": mode,
            },
            error_code=code,
            record_refs=refs,
        )
        if reason:
            return {"undone": False, "reason": reason}
        return {"undone": True, "mode": mode}

    # ------------------------------------------------------------------
    # Undo of edits: restore the values before, if nobody changed them since
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_undo_edit_reason(self, model, res_id, edit, since=None):
        """Why the edit ``edit`` (``{"before", "after"}``) of a record cannot be
        undone, or ``None``."""
        if self.env.su or self.env.context.get("xtd_ai_run"):
            return self.env._("Operación no permitida desde el agente.")
        if (edit or {}).get("transition"):
            return self._xtd_ai_transition_reason(model, res_id, edit, since)
        registry = self.env["xtd.ai.record.registry"]
        spec = registry._xtd_ai_specs().get(model)
        before = (edit or {}).get("before") or {}
        after = (edit or {}).get("after") or {}
        editable = registry._xtd_ai_editable_fields(model)
        if not spec or not before or not set(before) <= editable:
            return self.env._("Este cambio no se puede deshacer.")
        record = self.env[model].browse(res_id).exists()
        if not record:
            return self.env._("Ya no existe.")
        try:
            record.check_access("write")
        except AccessError:
            return self.env._("No tienes permiso para modificarlo.")
        domain = registry._xtd_ai_record_domain(model, spec)
        if domain and not record.filtered_domain(domain):
            return self.env._("Ya no se puede modificar (no es un borrador).")
        if since and fields.Datetime.now() - since > self._xtd_ai_undo_window():
            return self.env._("Ha pasado demasiado tiempo para deshacerlo.")
        current = registry._xtd_ai_snapshot(record, list(before))
        for fname, value in after.items():
            if fname in current and not registry._xtd_ai_same(
                model, fname, current[fname], value
            ):
                return self.env._("Alguien lo ha modificado después.")
        return None

    @api.model
    def _xtd_ai_undo_edit_done(self, model, res_id, edit):
        if (edit or {}).get("transition"):
            handler = self._xtd_ai_transition_handler(edit, "done")
            record = self.env[model].browse(res_id).exists()
            return bool(handler and record and handler(record, edit))
        registry = self.env["xtd.ai.record.registry"]
        record = self.env[model].browse(res_id).exists()
        before = (edit or {}).get("before") or {}
        after = (edit or {}).get("after") or {}
        if not record or not before:
            return False
        current = registry._xtd_ai_snapshot(record, list(before))
        return any(
            not registry._xtd_ai_same(model, f, before[f], after.get(f)) for f in before
        ) and all(
            registry._xtd_ai_same(model, f, current[f], before[f]) for f in before
        )

    @api.model
    def _xtd_ai_undo_edit_state(self, model, res_id, edit, since=None):
        """``available``, ``undone`` or ``None`` for an edited record."""
        if model not in self.env:
            return None
        if self._xtd_ai_undo_edit_done(model, res_id, edit):
            return "undone"
        reason = self._xtd_ai_undo_edit_reason(model, res_id, edit, since)
        return "available" if reason is None else None

    @api.model
    def _xtd_ai_restore_vals(self, model, before):
        """ORM values that put back the snapshot ``before``."""
        fields_map = self.env[model]._fields
        vals = {}
        for fname, value in before.items():
            field = fields_map[fname]
            if field.type in ("many2many", "one2many"):
                vals[fname] = [Command.set(value or [])]
            else:
                vals[fname] = value
        return vals

    @api.model
    def _xtd_ai_undo_edit(self, model, res_id, edit, since=None, run=None):
        """Restore the values before an edit, as the session user, and audit it."""
        reason = self._xtd_ai_undo_edit_reason(model, res_id, edit, since)
        record = self.env[model].browse(res_id).exists() if model in self.env else None
        if not record:
            raise UserError(self.env._("Ya no existe o no se puede deshacer."))
        if not reason:
            try:
                with self.env.cr.savepoint():
                    if edit.get("transition"):
                        self._xtd_ai_transition_handler(edit, "apply")(record, edit)
                    else:
                        record.write(self._xtd_ai_restore_vals(model, edit["before"]))
            except Exception as exc:  # constraint: not undoable any more
                _logger.info("Undo edit of %s,%s refused: %s", model, res_id, exc)
                reason = self.env._("No se puede volver al valor anterior.")
        self.env["xtd.ai.audit"]._xtd_ai_log(
            "undo",
            "denied" if reason else "ok",
            run_id=run.id if run else None,
            user_id=self.env.uid,
            company_id=self.env.company.id,
            tool_name="undo_edit",
            arguments={
                "model": model,
                "id": res_id,
                "mode": "transition" if edit.get("transition") else "restore",
            }
            | edit,
            error_code="not_undoable" if reason else None,
            record_refs=[
                {
                    "model": model,
                    "id": res_id,
                    "name": (record.display_name or "")[:100],
                }
            ],
        )
        if reason:
            return {"undone": False, "reason": reason}
        return {"undone": True, "mode": "restore"}

    # ------------------------------------------------------------------
    # Undo of transitions (wave 2B): confirm, cancel, move a stage, an
    # activity. ``edit["transition"]`` names the handlers
    # ``_xtd_ai_transition_<name>_{reason,done,apply}(record, edit)`` that
    # the tool modules define; anything unknown is not undoable.
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_transition_handler(self, edit, step):
        name = (edit or {}).get("transition")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z_]{1,40}", name):
            return None
        return getattr(self, f"_xtd_ai_transition_{name}_{step}", None)

    @api.model
    def _xtd_ai_transition_reason(self, model, res_id, edit, since=None):
        handler = self._xtd_ai_transition_handler(edit, "reason")
        if not handler:
            return self.env._("Este cambio no se puede deshacer.")
        record = self.env[model].browse(res_id).exists()
        if not record:
            return self.env._("Ya no existe.")
        try:
            record.check_access("write")
        except AccessError:
            return self.env._("No tienes permiso para modificarlo.")
        if since and fields.Datetime.now() - since > self._xtd_ai_undo_window():
            return self.env._("Ha pasado demasiado tiempo para deshacerlo.")
        return handler(record, edit)

    # -- an activity the agent scheduled (schedule_activity) ------------------
    def _xtd_ai_activity(self, record, edit):
        activity_id = (edit.get("after") or {}).get("activity_id")
        if not isinstance(activity_id, int) or isinstance(activity_id, bool):
            return self.env["mail.activity"]
        activity = (
            self.env["mail.activity"]
            .with_context(active_test=False)
            .browse(activity_id)
            .exists()
        )
        if activity and (activity.res_model, activity.res_id) != (
            record._name,
            record.id,
        ):
            return self.env["mail.activity"]
        return activity

    def _xtd_ai_transition_activity_reason(self, record, edit):
        activity = self._xtd_ai_activity(record, edit)
        if not activity:
            return self.env._("La actividad ya no existe.")
        if "active" in activity._fields and not activity.active:
            return self.env._("La actividad ya está hecha.")
        if activity.create_uid != self.env.user or activity.write_uid.id not in (
            self.env.uid,
            SUPERUSER_ID,
        ):
            return self.env._("Alguien la ha modificado después.")
        after = edit.get("after") or {}
        if (
            str(activity.date_deadline) != after.get("date_deadline")
            or activity.user_id.id != after.get("user_id")
            or (activity.summary or "") != after.get("summary", "")
        ):
            return self.env._("La actividad se ha modificado después.")
        try:
            activity.check_access("unlink")
        except AccessError:
            return self.env._("No tienes permiso para borrarla.")
        return None

    def _xtd_ai_transition_activity_done(self, record, edit):
        activity_id = (edit.get("after") or {}).get("activity_id")
        return bool(activity_id) and not self._xtd_ai_activity(record, edit)

    def _xtd_ai_transition_activity_apply(self, record, edit):
        self._xtd_ai_activity(record, edit).unlink()
