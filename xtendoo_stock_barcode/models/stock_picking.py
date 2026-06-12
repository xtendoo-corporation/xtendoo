# -*- coding: utf-8 -*-

import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "barcodes.barcode_events_mixin"]

    xt_barcode_mode = fields.Selection(
        selection=[
            ("product", "Producto"),
            ("source", "Ubicación origen"),
            ("destination", "Ubicación destino"),
            ("lot", "Lote/serie"),
            ("package", "Paquete"),
        ],
        string="Modo de escaneo",
        default="product",
        copy=False,
    )
    xt_barcode_current_line_id = fields.Many2one(
        "stock.move.line",
        string="Línea actual de escaneo",
        copy=False,
    )
    xt_barcode_source_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación origen escaneada",
        copy=False,
        domain="[('usage', '!=', 'view')]",
    )
    xt_barcode_destination_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación destino escaneada",
        copy=False,
        domain="[('usage', '!=', 'view')]",
    )
    xt_barcode_last_scan = fields.Char(string="Último código escaneado", copy=False)
    xt_barcode_last_message = fields.Text(string="Último mensaje de escaneo", copy=False)
    xt_barcode_current_package_id = fields.Many2one(
        "stock.package",
        string="Paquete actual de escaneo",
        copy=False,
    )
    xt_barcode_pending_tracking_count = fields.Integer(
        string="Líneas con lote/serie pendiente",
        compute="_compute_xt_barcode_pending_counts",
    )
    xt_barcode_pending_destination_count = fields.Integer(
        string="Líneas con destino pendiente",
        compute="_compute_xt_barcode_pending_counts",
    )
    xt_barcode_pending_package_count = fields.Integer(
        string="Líneas con paquete pendiente",
        compute="_compute_xt_barcode_pending_counts",
    )
    xt_barcode_supported = fields.Boolean(
        string="Barcode clásico disponible",
        compute="_compute_xt_barcode_supported",
    )
    xt_barcode_expected_move_count = fields.Integer(
        string="Líneas esperadas",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_checked_move_count = fields.Integer(
        string="Líneas completas",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_pending_move_count = fields.Integer(
        string="Líneas pendientes",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_excess_move_count = fields.Integer(
        string="Líneas con exceso",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_compare_state = fields.Selection(
        selection=[
            ("empty", "Sin líneas"),
            ("pending", "Pendiente"),
            ("partial", "Parcial"),
            ("complete", "Completo"),
            ("excess", "Con exceso"),
        ],
        string="Estado de comprobación",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_progress_percent = fields.Float(
        string="Progreso PDA",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_has_scanned_products = fields.Boolean(
        string="Escaneo PDA iniciado",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_next_step = fields.Char(
        string="Siguiente paso",
        compute="_compute_xt_barcode_guidance",
    )
    xt_barcode_zero_scan_message = fields.Char(
        string="Mensaje inicial PDA",
        compute="_compute_xt_barcode_guidance",
    )
    xt_barcode_pending_summary = fields.Text(
        string="Resumen de pendientes",
        compute="_compute_xt_barcode_guidance",
    )
    xt_barcode_pending_move_ids = fields.Many2many(
        "stock.move",
        string="Productos pendientes PDA",
        compute="_compute_xt_barcode_check_summary",
    )
    xt_barcode_focus_move_id = fields.Many2one(
        "stock.move",
        string="Movimiento foco PDA",
        compute="_compute_xt_barcode_guidance",
    )
    xt_barcode_focus_product_label = fields.Char(
        string="Producto foco PDA",
        compute="_compute_xt_barcode_guidance",
    )
    xt_barcode_focus_quantity_label = fields.Char(
        string="Resumen foco PDA",
        compute="_compute_xt_barcode_guidance",
    )
    xt_barcode_excess_confirmed_product_ids = fields.Many2many(
        "product.product",
        string="Productos con exceso confirmado",
        copy=False,
    )

    def _compute_xt_barcode_supported(self):
        allowed_codes = set(self._barcode_scan_supported_operation_codes())
        for picking in self:
            picking.xt_barcode_supported = (
                picking.picking_type_code in allowed_codes
                and picking.state not in ("done", "cancel")
            )

    def _compute_xt_barcode_pending_counts(self):
        for picking in self:
            lines = picking._get_relevant_barcode_lines()
            picking.xt_barcode_pending_tracking_count = len(
                lines.filtered(lambda line: picking._line_requires_tracking_scan(line))
            )
            picking.xt_barcode_pending_destination_count = len(
                lines.filtered(lambda line: picking._line_requires_destination_scan(line))
            )
            picking.xt_barcode_pending_package_count = len(
                lines.filtered(lambda line: picking._line_requires_package_scan(line))
            )

    def _get_expected_barcode_moves(self):
        self.ensure_one()
        return self.move_ids.filtered(
            lambda move: move.state != "cancel"
            and move.product_id
            and (move.product_uom_qty or move.quantity)
        )

    def _get_pending_barcode_moves(self):
        self.ensure_one()
        state_order = {"excess": 0, "partial": 1, "pending": 2, "complete": 3}
        return self._get_expected_barcode_moves().filtered(
            lambda move: move.xt_barcode_check_state in ("pending", "partial", "excess")
        ).sorted(
            key=lambda move: (
                state_order.get(move.xt_barcode_check_state, 99),
                -(move.xt_barcode_remaining_qty or 0.0),
                move.product_id.display_name or "",
                move.id,
            )
        )

    def _compute_xt_barcode_check_summary(self):
        for picking in self:
            moves = picking._get_expected_barcode_moves()
            pending_moves = picking._get_pending_barcode_moves()
            picking.xt_barcode_has_scanned_products = bool(
                moves.filtered(lambda move: move.xt_barcode_scanned_qty > 0)
            )
            picking.xt_barcode_expected_move_count = len(moves)
            picking.xt_barcode_checked_move_count = len(
                moves.filtered(lambda move: move.xt_barcode_check_state == "complete")
            )
            picking.xt_barcode_pending_move_count = len(
                moves.filtered(lambda move: move.xt_barcode_check_state in ("pending", "partial"))
            )
            picking.xt_barcode_excess_move_count = len(
                moves.filtered(lambda move: move.xt_barcode_check_state == "excess")
            )
            picking.xt_barcode_pending_move_ids = pending_moves
            has_progress = bool(
                moves.filtered(
                    lambda move: move.xt_barcode_check_state in ("partial", "complete")
                )
            )
            if not moves:
                picking.xt_barcode_compare_state = "empty"
            elif picking.xt_barcode_excess_move_count:
                picking.xt_barcode_compare_state = "excess"
            elif picking.xt_barcode_pending_move_count and has_progress:
                picking.xt_barcode_compare_state = "partial"
            elif picking.xt_barcode_pending_move_count:
                picking.xt_barcode_compare_state = "pending"
            else:
                picking.xt_barcode_compare_state = "complete"
            if picking.xt_barcode_expected_move_count:
                picking.xt_barcode_progress_percent = (
                    picking.xt_barcode_checked_move_count / picking.xt_barcode_expected_move_count
                ) * 100.0
            else:
                picking.xt_barcode_progress_percent = 0.0

    def _compute_xt_barcode_guidance(self):
        for picking in self:
            current_line = picking.xt_barcode_current_line_id
            current_product = current_line.product_id.display_name if current_line else False
            pending_moves = picking._get_pending_barcode_moves()
            zero_scan_message = False
            focus_move = self.env["stock.move"]
            if (
                current_line
                and current_line.move_id.picking_id == picking
                and current_line.move_id.state not in ("done", "cancel")
                and current_line.move_id.xt_barcode_check_state != "complete"
            ):
                focus_move = current_line.move_id
            elif pending_moves:
                focus_move = pending_moves[0]

            if picking.xt_barcode_compare_state not in ("empty", "complete") and not picking.xt_barcode_has_scanned_products:
                zero_scan_message = _("Aún no se ha escaneado ningún producto.")

            if zero_scan_message and focus_move:
                focus_quantity_label = _(
                    "Pendiente inicial: %s de %s %s.",
                    focus_move.xt_barcode_remaining_qty,
                    focus_move.product_uom_qty,
                    focus_move.product_uom.display_name,
                )
            elif focus_move:
                focus_quantity_label = _(
                    "Faltan %s de %s %s · ya llevas %s escaneadas",
                    focus_move.xt_barcode_remaining_qty,
                    focus_move.product_uom_qty,
                    focus_move.product_uom.display_name,
                    focus_move.xt_barcode_scanned_qty,
                )
            else:
                focus_quantity_label = _("Sin producto pendiente en foco.")

            if picking.xt_barcode_compare_state == "complete":
                next_step = _("Movimiento comprobado. Ya puedes validar.")
            elif picking.xt_barcode_mode == "source":
                next_step = _("Escanea la ubicación de origen para empezar.")
            elif picking.xt_barcode_mode == "destination":
                next_step = _("Escanea la ubicación de destino.")
            elif picking.xt_barcode_mode == "lot":
                next_step = (
                    _("Escanea el lote o serie de %s.", current_product)
                    if current_product
                    else _("Escanea el lote o serie de la línea actual.")
                )
            elif picking.xt_barcode_mode == "package":
                next_step = _("Escanea el paquete de destino.")
            elif picking.xt_barcode_compare_state == "empty":
                next_step = _("No hay líneas útiles para comprobar en este movimiento.")
            elif focus_move:
                next_step = (
                    _(
                        "Escanea %s para empezar.",
                        focus_move.product_id.display_name,
                    )
                    if zero_scan_message
                    else _(
                        "Escanea ahora %s para seguir completando el picking.",
                        focus_move.product_id.display_name,
                    )
                )
            else:
                next_step = _("Escanea el siguiente producto del movimiento.")

            pending_parts = []
            if zero_scan_message:
                pending_parts.append(
                    _(
                        "Pendiente de iniciar · %s líneas por revisar",
                        picking.xt_barcode_pending_move_count
                        or picking.xt_barcode_expected_move_count,
                    )
                )
            elif picking.xt_barcode_pending_move_count:
                pending_parts.append(
                    _("Productos pendientes: %s", picking.xt_barcode_pending_move_count)
                )
            if picking.xt_barcode_pending_tracking_count:
                pending_parts.append(
                    _("Lotes/series pendientes: %s", picking.xt_barcode_pending_tracking_count)
                )
            if picking.xt_barcode_pending_destination_count:
                pending_parts.append(
                    _("Destinos por confirmar: %s", picking.xt_barcode_pending_destination_count)
                )
            if picking.xt_barcode_pending_package_count:
                pending_parts.append(
                    _("Paquetes pendientes: %s", picking.xt_barcode_pending_package_count)
                )
            if picking.xt_barcode_excess_move_count:
                pending_parts.append(
                    _("Líneas con exceso: %s", picking.xt_barcode_excess_move_count)
                )

            picking.xt_barcode_focus_move_id = focus_move
            if zero_scan_message and focus_move:
                picking.xt_barcode_focus_product_label = _(
                    "Primer producto: %s", focus_move.product_id.display_name
                )
            else:
                picking.xt_barcode_focus_product_label = (
                    focus_move.product_id.display_name if focus_move else _("Sin pendientes")
                )
            picking.xt_barcode_focus_quantity_label = focus_quantity_label
            picking.xt_barcode_zero_scan_message = zero_scan_message
            picking.xt_barcode_next_step = next_step
            picking.xt_barcode_pending_summary = (
                " · ".join(pending_parts)
                if pending_parts
                else _("Sin incidencias pendientes por barcode.")
            )

    def _barcode_scan_allowed_states(self):
        return {"draft", "waiting", "confirmed", "assigned"}

    def _barcode_scan_supported_operation_codes(self):
        return ("incoming", "outgoing", "internal")

    def _barcode_scan_log_prefix(self):
        self.ensure_one()
        return f"[xtendoo_stock_barcode] [{self.name or self.id or 'new'}]"



