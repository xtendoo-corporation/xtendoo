"""Sales transitions of wave 2B (ANALISIS_PERMISOS §4 Ventas, §6.1).

Confirm a quotation, send it by email and cancel it. Always a card (N2) with a
faithful preview and its effects, or N3 (prepare and open the order, «solo
falta Confirmar») when the company has not turned the transition on. Each tool
unlocks only its own operation on its one order (§6.5).
"""

from odoo import models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext

from odoo.addons.xtd_ai.tools import XtdAiToolError, unlock, xtd_ai_tool

from .xtd_ai_toolbox_sale import SALES_GROUPS, _schema

_ORDER = {
    "type": "string",
    "minLength": 1,
    "maxLength": 100,
    "description": "Id numérico (preferible) o referencia del presupuesto (S00007).",
}
_DELIVERY_STEPS = {"ship_only": 1, "pick_ship": 2, "pick_pack_ship": 3}


class XtdAiToolboxSale(models.AbstractModel):
    _inherit = "xtd.ai.toolbox.sale"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _xtd_ai_open_quotation(self, ref, states=("draft", "sent")):
        order = self._xtd_ai_resolve("sale.order", ref)
        order.check_access("write")
        if order.state not in states:
            raise XtdAiToolError(
                "validation",
                self.env._(
                    "%(name)s no es un presupuesto abierto (estado: %(state)s).",
                    name=order.name,
                    state=dict(
                        order._fields["state"]._description_selection(self.env)
                    ).get(order.state, order.state),
                ),
            )
        return order

    def _xtd_ai_line_goods(self, order):
        return order.order_line.filtered(
            lambda line: not line.display_type
            and line.product_id
            and line.product_id.type == "consu"
            and line.product_uom_qty > 0
        )

    def _xtd_ai_confirm_effects(self, order):
        """What confirming ``order`` does, computed from the order and the
        configuration (the preview never runs the confirmation)."""
        env = self.env
        effects = []
        goods = self._xtd_ai_line_goods(order)
        warehouse = "warehouse_id" in order._fields and order.warehouse_id
        if goods and warehouse:
            steps = _DELIVERY_STEPS.get(warehouse.delivery_steps, 1)
            effects.append(
                env._(
                    "Creará %(count)s transferencia(s) de salida para %(partner)s "
                    "(%(lines)s línea(s) de producto).",
                    count=steps,
                    partner=order.partner_shipping_id.display_name,
                    lines=len(goods),
                )
            )
            short = []
            for line in goods.filtered(lambda line: line.product_id.is_storable):
                free = line.product_id.with_context(warehouse_id=warehouse.id).free_qty
                qty = line.product_uom_id._compute_quantity(
                    line.product_uom_qty, line.product_id.uom_id
                )
                if free + 1e-6 < qty:
                    short.append(f"{line.product_id.display_name} ({free:g}/{qty:g})")
            effects.append(
                env._("Reservará el stock disponible.")
                if not short
                else env._(
                    "Sin stock suficiente (libre/pedido): %s. Esa parte quedará "
                    "en espera.",
                    ", ".join(short[:5]),
                )
            )
            mto = env.ref("stock.route_warehouse0_mto", raise_if_not_found=False)
            if mto and goods.filtered(
                lambda line: mto in (line.route_ids or line.product_id.route_ids)
            ):
                effects.append(
                    env._(
                        "Algún producto se pide bajo pedido: puede crear una "
                        "petición de compra o de fabricación."
                    )
                )
        elif goods:
            effects.append(env._("Productos físicos sin almacén: no crea entregas."))
        if "service_tracking" in env["product.template"]._fields:
            tasks = order.order_line.filtered(
                lambda line: line.product_id.service_tracking not in (False, "no", None)
            )
            if tasks:
                effects.append(
                    env._(
                        "Creará proyecto o tareas para %s línea(s) de servicio.",
                        len(tasks),
                    )
                )
        threshold = (
            env["xtd.ai.policy"]
            .with_company(order.company_id or env.company)
            ._xtd_ai_discount_threshold()
        )
        high = order.order_line.filtered(lambda line: line.discount > threshold)
        if high:
            effects.append(
                env._(
                    "Descuento por encima del %(limit)g %%: %(lines)s.",
                    limit=threshold,
                    lines=", ".join(
                        f"{line.product_id.display_name} {line.discount:g} %"
                        for line in high[:5]
                    ),
                )
            )
        if order.partner_credit_warning:
            effects.append(order.partner_credit_warning[:200])
        if env["res.groups"]._is_feature_enabled("sale.group_auto_done_setting"):
            effects.append(env._("El pedido quedará bloqueado al confirmarlo."))
        effects.append(env._("No escribe al cliente (sin correo de confirmación)."))
        return effects

    def _xtd_ai_order_lines_preview(self, order):
        lines = [
            {"field": self.env._("Cliente"), "value": order.partner_id.display_name},
            {
                "field": self.env._("Importe"),
                "value": self.env._(
                    "%(untaxed)s sin impuestos · %(total)s total",
                    untaxed=self._xtd_ai_money_fmt(
                        order.amount_untaxed, order.currency_id
                    ),
                    total=self._xtd_ai_money_fmt(order.amount_total, order.currency_id),
                ),
            },
        ]
        if self._xtd_ai_multi():
            lines.append(
                {"field": self.env._("Compañía"), "value": order.company_id.name}
            )
        return lines

    # ------------------------------------------------------------------
    # Confirm a quotation
    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="confirm_sale_order",
        title="Confirmar presupuesto",
        description=(
            "Confirma un presupuesto de venta (borrador o enviado) y lo convierte en "
            "pedido: puede crear entregas y reservar stock. Úsala siempre que el "
            "usuario pida confirmar un presupuesto concreto; XTD decide si queda una "
            "tarjeta con los efectos o si el presupuesto se abre en pantalla para "
            "que el usuario pulse Confirmar. Un presupuesto por llamada; nunca "
            "confirmes otros que no haya pedido el usuario."
        ),
        input_schema=_schema({"order": _ORDER}, ["order"]),
        kind="draft",
        skill="ventas",
        groups=SALES_GROUPS,
        op_class="confirm_sale",
        company="_xtd_ai_order_company",
        preview="_xtd_ai_preview_confirm_sale_order",
        handoff="_xtd_ai_handoff_confirm_sale_order",
        unlocks=("sale.order.action_confirm",),
    )
    def tool_confirm_sale_order(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        if not order.order_line.filtered(lambda line: not line.display_type):
            raise XtdAiToolError(
                "validation", self.env._("El presupuesto no tiene líneas.")
            )
        before = order.state
        unlock(order, "action_confirm").action_confirm()
        order.invalidate_recordset()
        data = self._xtd_ai_order_row(order)
        if "picking_ids" in order._fields:
            data["deliveries"] = [p.name for p in order.picking_ids]
        return {
            "data": data,
            "records": [
                self._xtd_ai_ref(order)
                | {
                    "undo_edit": {
                        "before": {"state": before},
                        "after": {"state": order.state},
                        "transition": "sale_confirm",
                    }
                }
            ],
        }

    def _xtd_ai_preview_confirm_sale_order(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        lines = self._xtd_ai_order_lines_preview(order)
        lines += [
            {"field": self.env._("Efecto"), "value": effect}
            for effect in self._xtd_ai_confirm_effects(order)
        ]
        return {
            "summary": self.env._(
                "Confirmar %(name)s de %(partner)s (%(total)s)",
                name=order.name,
                partner=(order.partner_id.display_name or "")[:60],
                total=self._xtd_ai_money_fmt(order.amount_total, order.currency_id),
            ),
            "lines": lines,
            "confirm_label": self.env._("Confirmar"),
        }

    def _xtd_ai_handoff_confirm_sale_order(self, args):
        return self._xtd_ai_open_quotation(args["order"]), self.env._("Confirmar")

    # ------------------------------------------------------------------
    # Send the quotation by email (standard template)
    # ------------------------------------------------------------------
    def _xtd_ai_quotation_composer(self, order):
        """The composer of «Enviar por correo» with the standard template, as
        the button builds it. Needs the ``send_email`` unlock (tool body) or a
        rolled-back preview; nothing the model writes reaches it."""
        if not order.partner_id.email:
            raise XtdAiToolError(
                "validation",
                self.env._(
                    "%s no tiene correo electrónico: añádelo en su ficha.",
                    order.partner_id.display_name,
                ),
            )
        template = order._find_mail_template()
        if not template:
            raise XtdAiToolError(
                "validation", self.env._("No hay plantilla de correo de presupuesto.")
            )
        # the same context as the «Enviar» button (sale.order.action_quotation_send)
        context = {
            "default_model": "sale.order",
            "default_res_ids": order.ids,
            "default_composition_mode": "comment",
            "default_email_layout_xmlid": (
                "mail.mail_notification_layout_with_responsible_signature"
            ),
            "email_notification_allow_footer": True,
            "force_email": True,
            "default_template_id": template.id,
            "mark_so_as_sent": True,
        }
        return order.env["mail.compose.message"].with_context(**context).create({})

    def _xtd_ai_followers_notified(self, order, exclude):
        subtype = self.env.ref("mail.mt_comment")
        followers = order.message_follower_ids.filtered(
            lambda f: f.partner_id
            and f.partner_id not in exclude
            and f.partner_id != self.env.user.partner_id
            and subtype in f.subtype_ids
        )
        return followers.partner_id

    def _xtd_ai_email_preview(self, order, composer):
        recipients = composer.partner_ids
        lines = [
            {
                "field": self.env._("Para"),
                "value": ", ".join(
                    f"{p.display_name} <{p.email or '-'}>" for p in recipients
                ),
            },
        ]
        followers = self._xtd_ai_followers_notified(order, recipients)
        if followers:
            lines.append(
                {
                    "field": self.env._("Seguidores avisados"),
                    "value": ", ".join(
                        f"{p.display_name} <{p.email or '-'}>" for p in followers[:5]
                    ),
                }
            )
        lines += [
            {"field": self.env._("Asunto"), "value": composer.subject or ""},
            {
                "field": self.env._("Texto"),
                "value": html2plaintext(composer.body or "").strip()[:280],
            },
            {
                "field": self.env._("Adjuntos"),
                "value": ", ".join(composer.attachment_ids.mapped("name"))
                or self.env._("el PDF del presupuesto"),
            },
            {
                "field": self.env._("Efecto"),
                "value": self.env._(
                    "Sale un correo real al cliente (plantilla estándar) y el "
                    "presupuesto pasa a «enviado»."
                ),
            },
        ]
        return lines

    @xtd_ai_tool(
        name="send_quotation_email",
        title="Enviar presupuesto por correo",
        description=(
            "Envía un presupuesto de venta (borrador o enviado) por correo al "
            "cliente del propio presupuesto, con la plantilla estándar de XTD y su "
            "PDF. El destinatario es siempre el cliente del presupuesto (no se "
            "puede cambiar ni añadir otro) y el texto lo pone la plantilla, nunca "
            "tú. Queda una tarjeta con destinatario, asunto y texto."
        ),
        input_schema=_schema({"order": _ORDER}, ["order"]),
        kind="draft",
        skill="ventas",
        groups=SALES_GROUPS,
        op_class="send_external",
        company="_xtd_ai_order_company",
        preview="_xtd_ai_preview_send_quotation_email",
        handoff="_xtd_ai_handoff_send_quotation_email",
        unlocks=("sale.order.send_email",),
    )
    def tool_send_quotation_email(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        order = unlock(order, "send_email")
        composer = self._xtd_ai_quotation_composer(order)
        to = composer.partner_ids
        composer.action_send_mail()
        order.invalidate_recordset()
        data = self._xtd_ai_order_row(order) | {
            "sent_to": [p.email for p in to],
            "undo": self.env._("Un correo enviado no se puede retirar."),
        }
        return {
            "data": data,
            "records": [self._xtd_ai_ref(order) | {"undo_edit": {"before": {}}}],
        }

    def _xtd_ai_preview_send_quotation_email(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        composer = self._xtd_ai_quotation_composer(order)
        return {
            "summary": self.env._(
                "Enviar %(name)s por correo a %(partner)s",
                name=order.name,
                partner=(order.partner_id.display_name or "")[:60],
            ),
            "lines": self._xtd_ai_order_lines_preview(order)
            + self._xtd_ai_email_preview(order, composer),
            "confirm_label": self.env._("Enviar"),
            "irreversible": True,
        }

    def _xtd_ai_handoff_send_quotation_email(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        return order, self.env._("Enviar")

    # ------------------------------------------------------------------
    # Cancel a quotation (draft or sent; never a confirmed order)
    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="cancel_sale_quotation",
        title="Cancelar presupuesto",
        description=(
            "Cancela un presupuesto de venta en borrador o enviado (no un pedido "
            "confirmado). Queda una tarjeta; se puede deshacer (vuelve a borrador)."
        ),
        input_schema=_schema({"order": _ORDER}, ["order"]),
        kind="draft",
        skill="ventas",
        groups=SALES_GROUPS,
        op_class="transition_internal",
        company="_xtd_ai_order_company",
        preview="_xtd_ai_preview_cancel_sale_quotation",
        unlocks=("sale.order.action_cancel",),
    )
    def tool_cancel_sale_quotation(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        before = order.state
        unlock(order, "action_cancel").action_cancel()
        return {
            "data": self._xtd_ai_order_row(order),
            "records": [
                self._xtd_ai_ref(order)
                | {
                    "undo_edit": {
                        "before": {"state": before},
                        "after": {"state": "cancel"},
                        "transition": "sale_cancel",
                    }
                }
            ],
        }

    def _xtd_ai_preview_cancel_sale_quotation(self, args):
        order = self._xtd_ai_open_quotation(args["order"])
        return {
            "summary": self.env._(
                "Cancelar el presupuesto %(name)s de %(partner)s",
                name=order.name,
                partner=(order.partner_id.display_name or "")[:60],
            ),
            "lines": self._xtd_ai_order_lines_preview(order)
            + [
                {
                    "field": self.env._("Efecto"),
                    "value": self.env._(
                        "Pasa a cancelado; no escribe al cliente. Se puede volver "
                        "a borrador."
                    ),
                }
            ],
            "confirm_label": self.env._("Cancelar presupuesto"),
        }


class XtdAiUndo(models.AbstractModel):
    """Undo of the sales transitions, from the user's session with their rights."""

    _inherit = "xtd.ai.undo"

    def _xtd_ai_sale_confirm_blocker(self, order):
        if order.state != "sale" or order.locked:
            return self.env._("El pedido ya no está confirmado y abierto.")
        if order.invoice_ids:
            return self.env._("El pedido ya tiene facturas.")
        if "picking_ids" in order._fields and order.picking_ids.filtered(
            lambda p: p.state == "done"
        ):
            return self.env._("Ya hay entregas hechas.")
        if "purchase_order_count" in order._fields:
            try:
                purchases = order.purchase_order_count
            except AccessError:
                # no purchase rights: only made-to-order products create them
                mto = self.env.ref(
                    "stock.route_warehouse0_mto", raise_if_not_found=False
                )
                purchases = mto and order.order_line.filtered(
                    lambda line: mto in (line.route_ids or line.product_id.route_ids)
                )
            if purchases:
                return self.env._("Puede haber generado compras: cancélalo en XTD.")
        return None

    def _xtd_ai_transition_sale_confirm_reason(self, order, edit):
        return self._xtd_ai_sale_confirm_blocker(order)

    def _xtd_ai_transition_sale_confirm_done(self, order, edit):
        return order.state in ("draft", "cancel") and (
            (edit.get("after") or {}).get("state") == "sale"
        )

    def _xtd_ai_transition_sale_confirm_apply(self, order, edit):
        # cancel (it cancels the pending deliveries) and back to quotation
        order._action_cancel()
        order.action_draft()

    def _xtd_ai_transition_sale_cancel_reason(self, order, edit):
        if order.state != "cancel":
            return self.env._("El presupuesto ya no está cancelado.")
        return None

    def _xtd_ai_transition_sale_cancel_done(self, order, edit):
        return order.state in ("draft", "sent")

    def _xtd_ai_transition_sale_cancel_apply(self, order, edit):
        order.action_draft()
