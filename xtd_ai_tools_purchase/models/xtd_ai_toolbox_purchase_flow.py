"""Purchase transitions of wave 2B (ANALISIS_PERMISOS §4 Compras, §6.1).

Confirm an RFQ (N2 card with its effects when the company turned it on, N3
otherwise; above the purchase limit the card is reinforced with the total and
the vendor) and cancel an RFQ. Each tool unlocks only its own operation on its
one order (§6.5). Sending the RFQ to the vendor stays with the user.
"""

from odoo import models
from odoo.tools.misc import formatLang

from odoo.addons.xtd_ai.tools import XtdAiToolError, unlock, xtd_ai_tool

from .xtd_ai_toolbox_purchase import PURCHASE_GROUPS, _obj

_ORDER = {
    "type": "string",
    "minLength": 1,
    "maxLength": 100,
    "description": "Id numérico (preferible) o referencia de la RFQ (P00007).",
}
_RECEIPT_STEPS = {"one_step": 1, "two_steps": 2, "three_steps": 3}


class XtdAiToolboxPurchase(models.AbstractModel):
    _inherit = "xtd.ai.toolbox.purchase"

    def _xtd_ai_open_rfq(self, ref):
        order = self._xtd_ai_resolve("purchase.order", ref)
        order.check_access("write")
        if order.state not in ("draft", "sent"):
            raise XtdAiToolError(
                "validation",
                self.env._(
                    "%(name)s no es una petición de presupuesto abierta (estado: "
                    "%(state)s).",
                    name=order.name,
                    state=order.state,
                ),
            )
        return order

    def _xtd_ai_fmt(self, amount, currency):
        return formatLang(self.env, amount, currency_obj=currency)

    def _xtd_ai_over_limit(self, order):
        limit = self.env["xtd.ai.policy"]._xtd_ai_purchase_confirm_limit()
        total = order.currency_id._convert(
            order.amount_total,
            order.company_id.currency_id,
            order.company_id,
            order.date_order or order.create_date,
        )
        return (limit if total > limit else None), limit

    def _xtd_ai_po_effects(self, order):
        env = self.env
        effects = []
        goods = order.order_line.filtered(
            lambda line: not line.display_type
            and line.product_id.type == "consu"
            and line.product_qty > 0
        )
        if goods and "picking_type_id" in order._fields and order.picking_type_id:
            warehouse = order.picking_type_id.warehouse_id
            steps = _RECEIPT_STEPS.get(warehouse.reception_steps, 1) if warehouse else 1
            effects.append(
                env._(
                    "Creará %(count)s recepción(es) en %(type)s con %(lines)s "
                    "línea(s) de producto.",
                    count=steps,
                    type=order.picking_type_id.display_name,
                    lines=len(goods),
                )
            )
        if not order._approval_allowed():
            effects.append(
                env._(
                    "Supera el importe de doble validación: quedará «por aprobar» "
                    "hasta que lo apruebe un responsable de compras."
                )
            )
        new_vendor = order.order_line.product_id.filtered(
            lambda p: order.partner_id not in p.seller_ids.partner_id
        )
        if new_vendor:
            effects.append(
                env._(
                    "Añadirá a %(vendor)s como proveedor de %(count)s producto(s).",
                    vendor=order.partner_id.display_name,
                    count=len(new_vendor),
                )
            )
        effects.append(
            env._("No escribe al proveedor (el envío del pedido lo hace el usuario).")
        )
        return effects

    @xtd_ai_tool(
        name="confirm_purchase_order",
        title="Confirmar pedido de compra",
        description=(
            "Confirma una petición de presupuesto (RFQ) en borrador o enviada y la "
            "convierte en pedido de compra: compromiso con el proveedor y, si hay "
            "productos físicos, recepciones. Úsala siempre que el usuario pida "
            "confirmar una RFQ concreta; XTD decide si queda una tarjeta con los "
            "efectos o si se abre en pantalla para que el usuario pulse Confirmar. "
            "Una por llamada; nunca confirmes otras."
        ),
        input_schema=_obj({"order": _ORDER}, ["order"]),
        kind="draft",
        skill="compras",
        groups=PURCHASE_GROUPS,
        op_class="confirm_purchase",
        preview="_xtd_ai_preview_confirm_purchase_order",
        handoff="_xtd_ai_handoff_confirm_purchase_order",
        unlocks=("purchase.order.button_confirm",),
    )
    def tool_confirm_purchase_order(self, args):
        order = self._xtd_ai_open_rfq(args["order"])
        if not order.order_line.filtered(lambda line: not line.display_type):
            raise XtdAiToolError("validation", self.env._("La RFQ no tiene líneas."))
        before = order.state
        unlock(order, "button_confirm").button_confirm()
        order.invalidate_recordset()
        data = {
            "id": order.id,
            "name": order.name,
            "state": order.state,
            "vendor": order.partner_id.display_name,
            "amount_total": self._xtd_ai_money(order.amount_total, order.currency_id),
        }
        if "picking_ids" in order._fields:
            data["receipts"] = [p.name for p in order.picking_ids]
        return {
            "data": data,
            "records": [
                self._xtd_ai_ref(order)
                | {
                    "undo_edit": {
                        "before": {"state": before},
                        "after": {"state": order.state},
                        "transition": "purchase_confirm",
                    }
                }
            ],
        }

    def _xtd_ai_preview_confirm_purchase_order(self, args):
        order = self._xtd_ai_open_rfq(args["order"])
        total = self._xtd_ai_fmt(order.amount_total, order.currency_id)
        over, limit = self._xtd_ai_over_limit(order)
        lines = [
            {"field": self.env._("Proveedor"), "value": order.partner_id.display_name},
            {
                "field": self.env._("Importe"),
                "value": self.env._(
                    "%(untaxed)s sin impuestos · %(total)s total",
                    untaxed=self._xtd_ai_fmt(order.amount_untaxed, order.currency_id),
                    total=total,
                ),
            },
        ]
        if self._xtd_ai_multi():
            lines.append(
                {"field": self.env._("Compañía"), "value": order.company_id.name}
            )
        lines += [
            {"field": self.env._("Efecto"), "value": effect}
            for effect in self._xtd_ai_po_effects(order)
        ]
        preview = {
            "summary": self.env._(
                "Confirmar %(name)s a %(vendor)s (%(total)s)",
                name=order.name,
                vendor=(order.partner_id.display_name or "")[:60],
                total=total,
            ),
            "lines": lines,
            "confirm_label": self.env._("Confirmar compra"),
        }
        if over is not None:
            # reinforced card (§6.1): total and vendor in plain sight
            preview["warning"] = self.env._(
                "Compra de %(total)s a %(vendor)s: supera el límite de %(limit)s. "
                "Revisa importe y proveedor antes de confirmar.",
                total=total,
                vendor=order.partner_id.display_name,
                limit=self._xtd_ai_fmt(limit, order.company_id.currency_id),
            )
        return preview

    def _xtd_ai_handoff_confirm_purchase_order(self, args):
        return self._xtd_ai_open_rfq(args["order"]), self.env._("Confirmar pedido")

    @xtd_ai_tool(
        name="cancel_purchase_rfq",
        title="Cancelar petición de presupuesto",
        description=(
            "Cancela una petición de presupuesto (RFQ) en borrador o enviada (no un "
            "pedido confirmado). Queda una tarjeta; se puede deshacer (vuelve a "
            "borrador)."
        ),
        input_schema=_obj({"order": _ORDER}, ["order"]),
        kind="draft",
        skill="compras",
        groups=PURCHASE_GROUPS,
        op_class="transition_internal",
        preview="_xtd_ai_preview_cancel_purchase_rfq",
        unlocks=("purchase.order.button_cancel",),
    )
    def tool_cancel_purchase_rfq(self, args):
        order = self._xtd_ai_open_rfq(args["order"])
        before = order.state
        unlock(order, "button_cancel").button_cancel()
        return {
            "data": {"id": order.id, "name": order.name, "state": order.state},
            "records": [
                self._xtd_ai_ref(order)
                | {
                    "undo_edit": {
                        "before": {"state": before},
                        "after": {"state": "cancel"},
                        "transition": "purchase_cancel",
                    }
                }
            ],
        }

    def _xtd_ai_preview_cancel_purchase_rfq(self, args):
        order = self._xtd_ai_open_rfq(args["order"])
        return {
            "summary": self.env._(
                "Cancelar la RFQ %(name)s de %(vendor)s (%(total)s)",
                name=order.name,
                vendor=(order.partner_id.display_name or "")[:60],
                total=self._xtd_ai_fmt(order.amount_total, order.currency_id),
            ),
            "lines": [
                {
                    "field": self.env._("Efecto"),
                    "value": self.env._(
                        "Pasa a cancelada; no escribe al proveedor. Se puede volver "
                        "a borrador."
                    ),
                }
            ],
            "confirm_label": self.env._("Cancelar RFQ"),
        }


class XtdAiUndo(models.AbstractModel):
    """Undo of the purchase transitions, from the user's session."""

    _inherit = "xtd.ai.undo"

    def _xtd_ai_transition_purchase_confirm_reason(self, order, edit):
        if order.state not in ("purchase", "to approve") or order.locked:
            return self.env._("El pedido ya no está confirmado y abierto.")
        if order.invoice_ids:
            return self.env._("El pedido ya tiene facturas de proveedor.")
        if "picking_ids" in order._fields and order.picking_ids.filtered(
            lambda p: p.state == "done"
        ):
            return self.env._("Ya hay recepciones hechas.")
        return None

    def _xtd_ai_transition_purchase_confirm_done(self, order, edit):
        return order.state in ("draft", "cancel")

    def _xtd_ai_transition_purchase_confirm_apply(self, order, edit):
        order.button_cancel()
        order.button_draft()

    def _xtd_ai_transition_purchase_cancel_reason(self, order, edit):
        if order.state != "cancel":
            return self.env._("La RFQ ya no está cancelada.")
        return None

    def _xtd_ai_transition_purchase_cancel_done(self, order, edit):
        return order.state in ("draft", "sent")

    def _xtd_ai_transition_purchase_cancel_apply(self, order, edit):
        order.button_draft()
