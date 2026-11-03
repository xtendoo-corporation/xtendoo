"""Validate a receipt or a delivery (wave 2B, ANALISIS_PERMISOS §4 Inventario).

N2 card with the stock effects when the company turned it on, N3 (open the
transfer, «solo falta Validar») otherwise. Only complete, ready transfers:
anything that would need a wizard (backorder, lots or serial numbers, a
partial quantity) is refused clearly and left to the user. Validating moves
stock and its valuation: it cannot be undone from the chat (a return is made
in XTD).
"""

from odoo import models
from odoo.tools.float_utils import float_compare

from odoo.addons.xtd_ai.tools import XtdAiToolError, unlock, xtd_ai_tool

from .xtd_ai_toolbox_stock import STOCK_GROUPS, _obj

_PICKING = {
    "type": "string",
    "minLength": 1,
    "maxLength": 100,
    "description": "Id numérico (preferible) o referencia del albarán (WH/IN/00004).",
}


class XtdAiToolboxStock(models.AbstractModel):
    _inherit = "xtd.ai.toolbox.stock"

    def _xtd_ai_validatable(self, ref):
        """The transfer, if it can be validated as is; ``XtdAiToolError`` with
        the reason (and the button the user has to press) otherwise."""
        picking = self._xtd_ai_resolve("stock.picking", ref)
        picking.check_access("write")
        env = self.env
        if picking.picking_type_id.code not in ("incoming", "outgoing"):
            raise XtdAiToolError(
                "validation",
                env._("Solo se validan recepciones y entregas, no %s.", picking.name),
            )
        if picking.state != "assigned":
            raise XtdAiToolError(
                "validation",
                env._(
                    "%(name)s no está preparado (estado: %(state)s): hazlo en XTD.",
                    name=picking.name,
                    state=picking.state,
                ),
            )
        moves = picking.move_ids.filtered(lambda m: m.state not in ("cancel", "done"))
        tracked = moves.filtered(lambda m: m.product_id.tracking != "none")
        if tracked:
            raise XtdAiToolError(
                "needs_user",
                env._(
                    "%s lleva productos con lote o número de serie: valídalo en XTD "
                    "para indicarlos.",
                    picking.name,
                ),
            )
        partial = moves.filtered(
            lambda m: float_compare(
                m.quantity, m.product_uom_qty, precision_rounding=m.product_uom.rounding
            )
            != 0
        )
        if partial:
            raise XtdAiToolError(
                "needs_user",
                env._(
                    "%(name)s no está completo (%(product)s: %(qty)g de %(demand)g). "
                    "Valídalo en XTD para decidir si queda un pedido pendiente.",
                    name=picking.name,
                    product=partial[0].product_id.display_name,
                    qty=partial[0].quantity,
                    demand=partial[0].product_uom_qty,
                ),
            )
        return picking

    def _xtd_ai_sends_confirmation(self, picking):
        return bool(
            picking.picking_type_id.code == "outgoing"
            and picking.company_id.stock_move_email_validation
            and picking.company_id.stock_mail_confirmation_template_id
        )

    @xtd_ai_tool(
        name="validate_picking",
        title="Validar recepción o entrega",
        description=(
            "Valida una recepción o una entrega que esté preparada y completa: "
            "mueve el stock (y su valoración). Si falta cantidad, lleva lotes o "
            "series o pide decidir un pedido pendiente, no se hace: lo valida el "
            "usuario en XTD. Úsala siempre que el usuario pida validar un albarán "
            "concreto; XTD decide si queda una tarjeta o si se abre en pantalla. "
            "Uno por llamada; nunca valides otros que no haya pedido el usuario."
        ),
        input_schema=_obj({"picking": _PICKING}, ["picking"]),
        kind="draft",
        skill="inventario",
        groups=STOCK_GROUPS,
        op_class="validate_picking",
        preview="_xtd_ai_preview_validate_picking",
        handoff="_xtd_ai_handoff_validate_picking",
        unlocks=("stock.picking.button_validate", "stock.picking.send_email"),
    )
    def tool_validate_picking(self, args):
        picking = self._xtd_ai_validatable(args["picking"])
        methods = ["button_validate"]
        if self._xtd_ai_sends_confirmation(picking):
            methods.append("send_email")  # the card showed the recipient
        unlock(picking, *methods).button_validate()
        picking.invalidate_recordset()
        if picking.state != "done":
            # Odoo asked for a wizard (backorder, confirmation...): nothing done
            raise XtdAiToolError(
                "needs_user",
                self.env._(
                    "XTD pide confirmar algo más para validar %s: hazlo en XTD.",
                    picking.name,
                ),
            )
        return {
            "data": {"id": picking.id, "name": picking.name, "state": picking.state},
            "records": [self._xtd_ai_ref(picking)],
        }

    def _xtd_ai_preview_validate_picking(self, args):
        picking = self._xtd_ai_validatable(args["picking"])
        env = self.env
        incoming = picking.picking_type_id.code == "incoming"
        moves = picking.move_ids.filtered(lambda m: m.state not in ("cancel", "done"))
        lines = [
            {
                "field": env._("Proveedor") if incoming else env._("Cliente"),
                "value": picking.partner_id.display_name or "-",
            },
            {
                "field": env._("Movimiento"),
                "value": f"{picking.location_id.display_name} → "
                f"{picking.location_dest_id.display_name}",
            },
        ]
        lines += [
            {
                "field": move.product_id.display_name[:60],
                "value": f"{move.quantity:g} {move.product_uom.name}",
            }
            for move in moves[:15]
        ]
        if len(moves) > 15:
            lines.append(
                {"field": "…", "value": env._("y %s productos más", len(moves) - 15)}
            )
        effects = [
            env._("Entrará el stock en el almacén y se valorará.")
            if incoming
            else env._("Saldrá el stock del almacén y se valorará."),
        ]
        if self._xtd_ai_sends_confirmation(picking):
            effects.append(
                env._(
                    "Escribirá a %s (correo de confirmación de entrega de la "
                    "compañía).",
                    picking.partner_id.email or picking.partner_id.display_name,
                )
            )
        else:
            effects.append(env._("No escribe a nadie."))
        effects.append(env._("No crea pedidos pendientes: el albarán está completo."))
        lines += [{"field": env._("Efecto"), "value": e} for e in effects]
        return {
            "summary": env._(
                "Validar %(name)s (%(count)s producto(s))",
                name=picking.name,
                count=len(moves),
            ),
            "lines": lines,
            "confirm_label": env._("Validar"),
            "irreversible": True,
        }

    def _xtd_ai_handoff_validate_picking(self, args):
        picking = self._xtd_ai_resolve("stock.picking", args["picking"])
        picking.check_access("read")
        return picking, self.env._("Validar")
