# -*- coding: utf-8 -*-

import logging
from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools import _

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _check_barcode_excess_demand(self, product, quantity):
        self.ensure_one()

        # Si ya ha sido confirmado el exceso para este producto en este picking, no volvemos a preguntar
        if product.id in self.xt_barcode_excess_confirmed_product_ids.ids:
            return False

        product_moves = self.move_ids.filtered(lambda m: m.product_id == product and m.state not in ("done", "cancel"))
        total_demand = sum(product_moves.mapped("product_uom_qty"))
        total_scanned = sum(product_moves.mapped("xt_barcode_scanned_qty"))

        if total_demand > 0 and total_scanned + quantity > total_demand:
            return _("Has superado la demanda inicial para %s (%s pedidas). ¿Deseas añadir unidades extra?", product.display_name, total_demand)
        return False

    def _get_barcode_excess_message(self, product):
        self.ensure_one()
        product_moves = self.move_ids.filtered(lambda m: m.product_id == product and m.state not in ("done", "cancel"))
        total_demand = sum(product_moves.mapped("product_uom_qty"))
        total_scanned = sum(product_moves.mapped("xt_barcode_scanned_qty"))

        if total_demand > 0 and total_scanned > total_demand:
            excess_qty = total_scanned - total_demand
            return _("Producto %s se ha excedido de la cantidad original en %s unidades.", product.display_name, excess_qty)
        return False

    def _set_barcode_feedback(self, barcode, message):
        self.ensure_one()
        self.xt_barcode_last_scan = barcode
        self.xt_barcode_last_message = message
        _logger.info("%s %s", self._barcode_scan_log_prefix(), message)

    def _barcode_scan_warning(self, barcode, message, *, raise_on_error=False):
        self.ensure_one()
        self._set_barcode_feedback(barcode, message)
        if raise_on_error:
            raise UserError(message)
        return {
            "warning": {
                "title": _("Escaneo de código de barras"),
                "message": message,
            }
        }

    def _barcode_scan_success(self, barcode, message):
        self.ensure_one()
        self._set_barcode_feedback(barcode, message)
        return False

    def _is_barcode_scan_allowed(self):
        self.ensure_one()
        return (
            self.id
            and self.state in self._barcode_scan_allowed_states()
            and self.picking_type_code in self._barcode_scan_supported_operation_codes()
        )

    def _get_barcode_company_domain(self):
        self.ensure_one()
        return [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]

    def _barcode_allow_extra_product(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_allow_extra_product

    def _barcode_source_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_scan_source_location or "no"

    def _barcode_destination_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_scan_dest_location or "no"

    def _barcode_tracking_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_scan_tracking_number or "optional"

    def _barcode_package_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_put_in_pack or "no"

    def _barcode_destination_validation_required(self):
        self.ensure_one()
        policy = self._barcode_destination_scan_policy()
        return policy == "mandatory" or (
            policy == "optional" and self.picking_type_id.xt_barcode_validation_after_dest_location
        )

    def _barcode_package_validation_required(self):
        self.ensure_one()
        policy = self._barcode_package_scan_policy()
        return policy == "mandatory" or (
            policy == "optional" and self.picking_type_id.xt_barcode_validation_all_product_packed
        )

    @api.model
    def _xt_barcode_search_normalized_records(self, model_name, field_name, barcode, limit=2, extra_domain=None, company_domain=False):
        if not barcode:
            return self.env[model_name]

        normalized_barcode = barcode.replace("-", "").replace(" ", "").replace("/", "").lower()
        chars = list(normalized_barcode)
        wildcard_pattern = "%" + "%".join(chars) + "%"

        domain = [(field_name, "=ilike", wildcard_pattern)]
        if extra_domain:
            domain.extend(extra_domain)
        if company_domain:
            if self:
                domain.extend(self._get_barcode_company_domain())
            else:
                domain.extend(self._xt_barcode_main_menu_company_domain())

        records = self.env[model_name].search(domain)
        if not records:
            return records

        def is_match(record):
            record_barcode = getattr(record, field_name)
            if not record_barcode:
                return False
            normalized_record_barcode = str(record_barcode).replace("-", "").replace(" ", "").replace("/", "").lower()
            return normalized_barcode == normalized_record_barcode

        matched_records = records.filtered(is_match)
        if limit:
            return matched_records[:limit]
        return matched_records

    def _find_product_from_barcode(self, barcode):
        self.ensure_one()
        products = self.env["product.product"].search(
            [("barcode", "=ilike", barcode), ("type", "!=", "service")],
            limit=2,
        )
        if not products:
            products = self._xt_barcode_search_normalized_records(
                "product.product",
                "barcode",
                barcode,
                limit=2,
                extra_domain=[("type", "!=", "service")],
                company_domain=False,
            )
        if products:
            return products
        packagings = self.env["product.uom"].search(
            [("barcode", "=ilike", barcode)],
            limit=2,
        )
        if not packagings:
            packagings = self._xt_barcode_search_normalized_records(
                "product.uom",
                "barcode",
                barcode,
                limit=2,
                company_domain=True,
            )
        return packagings.product_id.filtered(lambda product: product.type != "service")

    def _find_location_from_barcode(self, barcode):
        self.ensure_one()
        domain = [("barcode", "=ilike", barcode), ("usage", "!=", "view")]
        company_domain = self._get_barcode_company_domain()
        if self.company_id:
            domain.extend(company_domain)
        locations = self.env["stock.location"].search(domain, limit=2)
        if not locations:
            locations = self._xt_barcode_search_normalized_records(
                "stock.location",
                "barcode",
                barcode,
                limit=2,
                extra_domain=[("usage", "!=", "view")],
                company_domain=True,
            )
        return locations

    def _find_lot_from_barcode(self, product, barcode):
        self.ensure_one()
        domain = [("product_id", "=", product.id), ("name", "=ilike", barcode)]
        domain.extend(self._get_barcode_company_domain())
        lots = self.env["stock.lot"].search(domain, limit=2)
        if not lots:
            lots = self._xt_barcode_search_normalized_records(
                "stock.lot",
                "name",
                barcode,
                limit=2,
                extra_domain=[("product_id", "=", product.id)],
                company_domain=True,
            )
        return lots

    def _find_package_from_barcode(self, barcode):
        self.ensure_one()
        packages = self.env["stock.package"].search([("name", "=ilike", barcode)], limit=2)
        if not packages:
            packages = self._xt_barcode_search_normalized_records(
                "stock.package",
                "name",
                barcode,
                limit=2,
                company_domain=True,
            )
        return packages

    def _get_scan_source_location(self):
        self.ensure_one()
        return self.xt_barcode_source_location_id or self.location_id

    def _get_scan_destination_location(self):
        self.ensure_one()
        return self.xt_barcode_destination_location_id or self.location_dest_id

    def _get_current_barcode_line(self):
        self.ensure_one()
        line = self.xt_barcode_current_line_id
        if line and line.picking_id == self and line.state not in ("done", "cancel"):
            return line
        return self.env["stock.move.line"]

    def _get_relevant_barcode_lines(self):
        self.ensure_one()
        return self.move_line_ids.filtered(
            lambda line: line.state not in ("done", "cancel")
            and (
                line.xt_barcode_product_scanned
                or line.xt_barcode_source_scanned
                or line.xt_barcode_tracking_scanned
                or line.xt_barcode_destination_scanned
                or line.xt_barcode_package_scanned
            )
        )

    def _line_requires_tracking_scan(self, line):
        self.ensure_one()
        return (
            line.picking_id == self
            and line.product_id.tracking != "none"
            and not line.xt_barcode_tracking_scanned
        )

    def _line_requires_destination_scan(self, line):
        self.ensure_one()
        return (
            line.picking_id == self
            and self._barcode_destination_validation_required()
            and not line.xt_barcode_destination_scanned
        )

    def _line_requires_package_scan(self, line):
        self.ensure_one()
        return (
            line.picking_id == self
            and self._barcode_package_validation_required()
            and not line.xt_barcode_package_scanned
        )

    def _line_followup_mode(self, line):
        self.ensure_one()
        if not line:
            return "product"
        if self._line_requires_tracking_scan(line):
            return "lot"
        if self._barcode_destination_scan_policy() == "mandatory" and not line.xt_barcode_destination_scanned:
            return "destination"
        if self._barcode_package_scan_policy() == "mandatory" and not line.xt_barcode_package_scanned:
            return "package"
        return "product"

    def _get_new_line_barcode_flags(self, product):
        self.ensure_one()
        return {
            "xt_barcode_product_scanned": True,
            "xt_barcode_source_scanned": self._barcode_source_scan_policy() != "mandatory"
            or bool(self.xt_barcode_source_location_id),
            "xt_barcode_destination_scanned": self._barcode_destination_scan_policy() == "no",
            "xt_barcode_tracking_scanned": product.tracking == "none",
            "xt_barcode_package_scanned": self._barcode_package_scan_policy() == "no",
        }

    def _get_pending_line_warning(self, line, barcode, *, raise_on_error=False):
        self.ensure_one()
        next_mode = self._line_followup_mode(line)
        if next_mode == "lot":
            return self._barcode_scan_warning(
                barcode,
                _(
                    "La línea actual de %s requiere completar antes el lote o la serie.",
                    line.product_id.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        if next_mode == "destination":
            return self._barcode_scan_warning(
                barcode,
                _(
                    "La línea actual de %s requiere confirmar antes la ubicación destino.",
                    line.product_id.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        if next_mode == "package":
            return self._barcode_scan_warning(
                barcode,
                _(
                    "La línea actual de %s requiere escanear antes el paquete de destino.",
                    line.product_id.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        return False

    def _get_candidate_move(self, product, location_id, location_dest_id):
        self.ensure_one()
        return self.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
            and move.product_id == product
            and move.location_id == location_id
            and move.location_dest_id == location_dest_id
        )[:1]

    def _get_candidate_move_anywhere(self, product):
        self.ensure_one()
        return self.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
            and move.product_id == product
        )[:1]

    def _get_candidate_line_for_untracked(self, product, location_id, location_dest_id):
        self.ensure_one()
        expected_package = self.xt_barcode_current_package_id
        current_line = self._get_current_barcode_line()
        if (
            current_line
            and current_line.product_id == product
            and current_line.location_id == location_id
            and current_line.location_dest_id == location_dest_id
            and not current_line.lot_id
            and not current_line.lot_name
            and current_line.result_package_id == expected_package
        ):
            return current_line
        return self.move_line_ids.filtered(
            lambda line: line.state not in ("done", "cancel")
            and line.product_id == product
            and line.location_id == location_id
            and line.location_dest_id == location_dest_id
            and not line.lot_id
            and not line.lot_name
            and line.result_package_id == expected_package
        )[:1]

    def _create_barcode_move(self, product, location_id, location_dest_id, quantity):
        self.ensure_one()
        move = self.env["stock.move"].create(
            {
                "picking_id": self.id,
                "picking_type_id": self.picking_type_id.id,
                "company_id": self.company_id.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": quantity,
                "location_id": location_id.id,
                "location_dest_id": location_dest_id.id,
            }
        )
        if self.state != "draft":
            move._action_confirm()
        return move

    def _sync_move_demand_with_lines(self, move):
        self.ensure_one()
        total_done_qty = sum(move.move_line_ids.mapped("quantity"))
        if total_done_qty > move.product_uom_qty:
            move.product_uom_qty = total_done_qty

    def _create_barcode_move_line(self, move, product, location_id, location_dest_id, quantity, barcode_flags=None):
        self.ensure_one()
        values = {
            "picking_id": self.id,
            "move_id": move.id,
            "company_id": self.company_id.id,
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "location_id": location_id.id,
            "location_dest_id": location_dest_id.id,
            "quantity": quantity,
            "picked": bool(quantity),
        }
        if barcode_flags:
            values.update(barcode_flags)
        line = self.env["stock.move.line"].create(values)
        self._sync_move_demand_with_lines(move)
        return line

    def _increase_line_quantity(self, line, quantity, barcode_flags=None):
        self.ensure_one()
        # Si la línea no ha sido escaneada aún (es una reserva), reseteamos a 0
        # para que el primer escaneo/ajuste sume sobre 0 y no sobre la reserva de Odoo.
        current_qty = line.quantity or 0.0
        if quantity > 0 and not line.xt_barcode_product_scanned:
            current_qty = 0.0

        values = {"quantity": current_qty + quantity, "xt_barcode_product_scanned": True, "picked": True}
        if barcode_flags:
            values.update(barcode_flags)
        line.write(values)
        self._sync_move_demand_with_lines(line.move_id)
        return line

    def _set_current_line(self, line):
        self.ensure_one()
        self.xt_barcode_current_line_id = line
        return line

    def _apply_current_package_to_line(self, line):
        self.ensure_one()
        package = self.xt_barcode_current_package_id
        if not package:
            return line
        if line.result_package_id != package:
            line.action_put_in_pack(package_id=package.id)
        line.xt_barcode_package_scanned = True
        return line

    def _scan_source_location(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        locations = self._find_location_from_barcode(barcode)
        if not locations:
            return self._barcode_scan_warning(
                barcode,
                _("No se ha encontrado ninguna ubicación con el código '%s'.", barcode),
                raise_on_error=raise_on_error,
            )
        if len(locations) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varias ubicaciones.", barcode),
                raise_on_error=raise_on_error,
            )
        location = locations[0]
        self.xt_barcode_source_location_id = location
        current_line = self._get_current_barcode_line()
        if current_line and current_line.state not in ("done", "cancel"):
            current_line.write(
                {
                    "location_id": location.id,
                    "xt_barcode_source_scanned": True,
                }
            )
        self.xt_barcode_mode = "product"
        return self._barcode_scan_success(
            barcode,
            _("Ubicación origen seleccionada: %s", location.display_name),
        )

    def _scan_destination_location(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        locations = self._find_location_from_barcode(barcode)
        if not locations:
            return self._barcode_scan_warning(
                barcode,
                _("No se ha encontrado ninguna ubicación con el código '%s'.", barcode),
                raise_on_error=raise_on_error,
            )
        if len(locations) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varias ubicaciones.", barcode),
                raise_on_error=raise_on_error,
            )
        location = locations[0]
        self.xt_barcode_destination_location_id = location
        current_line = self._get_current_barcode_line()
        if current_line and current_line.state not in ("done", "cancel"):
            current_line.write(
                {
                    "location_dest_id": location.id,
                    "xt_barcode_destination_scanned": True,
                }
            )
            self.xt_barcode_mode = self._line_followup_mode(current_line)
        else:
            self.xt_barcode_mode = "product"
        return self._barcode_scan_success(
            barcode,
            _("Ubicación destino seleccionada: %s", location.display_name),
        )

    def _scan_package(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        packages = self._find_package_from_barcode(barcode)
        if len(packages) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varios paquetes.", barcode),
                raise_on_error=raise_on_error,
            )
        package = packages[:1]
        if not package:
            package = self.env["stock.package"].create({"name": barcode})

        self.xt_barcode_current_package_id = package
        current_line = self._get_current_barcode_line()
        if current_line:
            self._apply_current_package_to_line(current_line)
            self.xt_barcode_mode = self._line_followup_mode(current_line)
            return self._barcode_scan_success(
                barcode,
                _(
                    "Línea actual añadida al paquete %s.",
                    package.display_name,
                ),
            )
        self.xt_barcode_mode = "product"
        return self._barcode_scan_success(
            barcode,
            _("Paquete activo seleccionado: %s", package.display_name),
        )

    def _scan_product(self, barcode, quantity=1.0, gs1_barcode=False, *, raise_on_error=False, force_excess=False):
        self.ensure_one()
        pending_line = self._get_current_barcode_line()
        if pending_line:
            pending_warning = self._get_pending_line_warning(
                pending_line,
                barcode,
                raise_on_error=raise_on_error,
            )
            if pending_warning:
                return pending_warning

        if self._barcode_source_scan_policy() == "mandatory" and not self.xt_barcode_source_location_id:
            return self._barcode_scan_warning(
                barcode,
                _("Debes escanear primero la ubicación origen antes de procesar productos."),
                raise_on_error=raise_on_error,
            )

        products = self._find_product_from_barcode(barcode)
        if not products:
            return self._barcode_scan_warning(
                barcode,
                _("No se ha encontrado ningún producto almacenable o consumible con el código '%s'.", barcode),
                raise_on_error=raise_on_error,
            )
        if len(products) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varios productos.", barcode),
                raise_on_error=raise_on_error,
            )
        product = products[0]
        source = self._get_scan_source_location()
        destination = self._get_scan_destination_location()
        if not source or not destination:
            return self._barcode_scan_warning(
                barcode,
                _("El picking debe tener ubicaciones origen y destino definidas antes de escanear productos."),
                raise_on_error=raise_on_error,
            )

        tracking = product.tracking
        line = self.env["stock.move.line"]
        barcode_flags = self._get_new_line_barcode_flags(product)

        exact_move = self._get_candidate_move(product, source, destination)
        existing_move = exact_move or self._get_candidate_move_anywhere(product)

        # Bloquear exceso de demanda si no se permiten productos extra
        if not force_excess:
            excess_error = self._check_barcode_excess_demand(product, quantity)
            if excess_error:
                return {
                    "warning": {
                        "title": _("Exceso de cantidad"),
                        "message": excess_error,
                        "type": "excess_confirmation",
                        "product_name": product.display_name,
                    }
                }

        if not self._barcode_allow_extra_product() and not existing_move and not force_excess:
            return self._barcode_scan_warning(
                barcode,
                _(
                    "El producto %s no estaba previsto en esta operación y la configuración no permite añadir productos extra.",
                    product.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        if existing_move and not exact_move and not self._barcode_allow_extra_product():
            source = existing_move.location_id
            destination = existing_move.location_dest_id

        if tracking == "serial":
            move = exact_move or existing_move or self._create_barcode_move(product, source, destination, quantity)
            line = self._create_barcode_move_line(
                move,
                product,
                source,
                destination,
                quantity,
                barcode_flags=barcode_flags,
            )
            self._set_current_line(line)
            self.xt_barcode_mode = self._line_followup_mode(line)
            return self._barcode_scan_success(
                barcode,
                _("Serie pendiente para %s.", product.display_name),
            )

        candidate_line = self._get_candidate_line_for_untracked(product, source, destination)
        if candidate_line:
            line = self._increase_line_quantity(candidate_line, quantity, barcode_flags=barcode_flags)
        else:
            move = exact_move or existing_move or self._create_barcode_move(
                product,
                source,
                destination,
                quantity,
            )
            line = self._create_barcode_move_line(
                move,
                product,
                source,
                destination,
                quantity,
                barcode_flags=barcode_flags,
            )

        if self.xt_barcode_current_package_id and self._barcode_package_scan_policy() != "mandatory":
            self._apply_current_package_to_line(line)

        self._set_current_line(line)
        if tracking == "lot":
            self.xt_barcode_mode = self._line_followup_mode(line)
            return self._barcode_scan_success(
                barcode,
                _("Lote pendiente para %s.", product.display_name),
            )
        self.xt_barcode_mode = self._line_followup_mode(line)
        return self._barcode_scan_success(
            barcode,
            _(
                "Producto %s actualizado. Cantidad actual en la línea: %s",
                product.display_name,
                line.quantity,
            ),
        )

    def _scan_lot_or_serial(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        line = self._get_current_barcode_line()
        if not line:
            return self._barcode_scan_warning(
                barcode,
                _("No hay ninguna línea activa. Escanea primero un producto."),
                raise_on_error=raise_on_error,
            )
        product = line.product_id
        if product.tracking == "none":
            return self._barcode_scan_warning(
                barcode,
                _("La línea actual no requiere lote ni serie."),
                raise_on_error=raise_on_error,
            )

        lots = self._find_lot_from_barcode(product, barcode)
        if len(lots) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varios lotes/series para el producto actual.", barcode),
                raise_on_error=raise_on_error,
            )

        if product.tracking == "serial" and line.quantity > 1:
            return self._barcode_scan_warning(
                barcode,
                _("Una línea con seguimiento por serie no puede tener cantidad mayor que 1."),
                raise_on_error=raise_on_error,
            )

        duplicate_serial_line = self.move_line_ids.filtered(
            lambda other: other.id != line.id
            and other.product_id == product
            and (
                (other.lot_id and lots and other.lot_id == lots[0])
                or (other.lot_name and other.lot_name == barcode)
            )
        )[:1]
        if product.tracking == "serial" and duplicate_serial_line:
            return self._barcode_scan_warning(
                barcode,
                _("La serie '%s' ya está usada en otra línea del picking.", barcode),
                raise_on_error=raise_on_error,
            )

        values = {"picked": True, "xt_barcode_tracking_scanned": True}
        if lots:
            values.update({"lot_id": lots[0].id, "lot_name": False})
            message = _(
                "Lote/serie %s asignado a %s.",
                lots[0].display_name,
                product.display_name,
            )
        elif self.use_create_lots:
            values.update({"lot_id": False, "lot_name": barcode})
            message = _(
                "Nuevo lote/serie %s asignado a %s.",
                barcode,
                product.display_name,
            )
        else:
            return self._barcode_scan_warning(
                barcode,
                _(
                    "No existe un lote/serie '%s' para %s y este tipo de operación no permite crear uno nuevo.",
                    barcode,
                    product.display_name,
                ),
                raise_on_error=raise_on_error,
            )

        line.write(values)
        if self.xt_barcode_current_package_id and self._barcode_package_scan_policy() != "mandatory":
            self._apply_current_package_to_line(line)
        self.xt_barcode_mode = self._line_followup_mode(line)
        return self._barcode_scan_success(barcode, message)

    def _get_barcode_validation_errors(self):
        self.ensure_one()
        errors = []
        lines = self._get_relevant_barcode_lines()
        if not self.picking_type_id.xt_barcode_validation_full and not lines:
            errors.append(
                _("Debes trabajar al menos una línea con barcode antes de validar esta operación.")
            )

        pending_tracking = lines.filtered(lambda line: self._line_requires_tracking_scan(line))
        if pending_tracking and self._barcode_tracking_scan_policy() == "mandatory":
            errors.append(
                _(
                    "Hay líneas con lote/serie pendiente: %s",
                    ", ".join(pending_tracking.mapped("product_id.display_name")),
                )
            )

        pending_destination = lines.filtered(lambda line: self._line_requires_destination_scan(line))
        if pending_destination:
            errors.append(
                _(
                    "Hay líneas con destino pendiente de confirmar: %s",
                    ", ".join(pending_destination.mapped("product_id.display_name")),
                )
            )

        pending_package = lines.filtered(lambda line: self._line_requires_package_scan(line))
        if pending_package:
            errors.append(
                _(
                    "Hay líneas pendientes de paquete: %s",
                    ", ".join(pending_package.mapped("product_id.display_name")),
                )
            )
        return errors

    def _scan_gs1_data(self, gs1_data, barcode, *, raise_on_error=False):
        self.ensure_one()
        if "location" in gs1_data:
            res = self._scan_source_location(gs1_data["location"], raise_on_error=raise_on_error)
            if res and "warning" in res:
                return res
        if "location_dest" in gs1_data:
            res = self._scan_destination_location(gs1_data["location_dest"], raise_on_error=raise_on_error)
            if res and "warning" in res:
                return res

        if "product" in gs1_data:
            quantity = gs1_data.get("product_qty", 1.0)
            res = self._scan_product(gs1_data["product"], quantity=quantity, gs1_barcode=barcode, raise_on_error=raise_on_error)
            if res and "warning" in res:
                return res

        if "lot" in gs1_data:
            res = self._scan_lot_or_serial(gs1_data["lot"], raise_on_error=raise_on_error)
            if res and "warning" in res:
                return res

        if "package" in gs1_data:
            res = self._scan_package(gs1_data["package"], raise_on_error=raise_on_error)
            if res and "warning" in res:
                return res

        return self._barcode_scan_success(barcode, _("Código GS1 procesado correctamente."))

    def _apply_scanned_barcode(self, barcode, *, raise_on_error=False, force_excess=False):
        self.ensure_one()
        barcode = (barcode or "").strip()
        if not barcode:
            return {"status": "ignored"}

        if not self.id:
            return self._barcode_scan_warning(
                barcode,
                _("Guarda el picking antes de empezar a escanear."),
                raise_on_error=raise_on_error,
            )

        if not self._is_barcode_scan_allowed():
            return self._barcode_scan_warning(
                barcode,
                _("El picking no está en un estado compatible con el escaneo clásico."),
                raise_on_error=raise_on_error,
            )

        gs1_data = self.env["barcode.gs1.parser"].parse_gs1_barcode(barcode)
        if gs1_data:
            return self._scan_gs1_data(gs1_data, barcode, raise_on_error=raise_on_error)

        mode = self.xt_barcode_mode or "product"
        if mode == "source":
            return self._scan_source_location(barcode, raise_on_error=raise_on_error)
        if mode == "destination":
            return self._scan_destination_location(barcode, raise_on_error=raise_on_error)
        if mode == "lot":
            return self._scan_lot_or_serial(barcode, raise_on_error=raise_on_error)
        if mode == "package":
            return self._scan_package(barcode, raise_on_error=raise_on_error)
        return self._scan_product(barcode, quantity=1.0, raise_on_error=raise_on_error, force_excess=force_excess)

    def _xt_barcode_get_onchange_target(self):
        self.ensure_one()
        if self.id:
            return self
        if self._origin and self._origin.id:
            return self._origin

        params = self.env.context.get("params") or {}
        picking_id = (
            self.env.context.get("active_id")
            or self.env.context.get("id")
            or params.get("id")
            or params.get("resId")
        )
        if picking_id:
            picking = self.env["stock.picking"].browse(picking_id).exists()
            if picking:
                return picking
        return self

    def _xt_barcode_sync_onchange_state(self, persisted_picking):
        self.ensure_one()
        persisted_picking.ensure_one()
        if persisted_picking == self:
            return
        self.update(
            {
                "xt_barcode_mode": persisted_picking.xt_barcode_mode,
                "xt_barcode_current_line_id": persisted_picking.xt_barcode_current_line_id.id,
                "xt_barcode_source_location_id": persisted_picking.xt_barcode_source_location_id.id,
                "xt_barcode_destination_location_id": persisted_picking.xt_barcode_destination_location_id.id,
                "xt_barcode_last_scan": persisted_picking.xt_barcode_last_scan,
                "xt_barcode_last_message": persisted_picking.xt_barcode_last_message,
                "xt_barcode_current_package_id": persisted_picking.xt_barcode_current_package_id.id,
                "xt_barcode_pending_tracking_count": persisted_picking.xt_barcode_pending_tracking_count,
                "xt_barcode_pending_destination_count": persisted_picking.xt_barcode_pending_destination_count,
                "xt_barcode_pending_package_count": persisted_picking.xt_barcode_pending_package_count,
                "xt_barcode_expected_move_count": persisted_picking.xt_barcode_expected_move_count,
                "xt_barcode_checked_move_count": persisted_picking.xt_barcode_checked_move_count,
                "xt_barcode_pending_move_count": persisted_picking.xt_barcode_pending_move_count,
                "xt_barcode_excess_move_count": persisted_picking.xt_barcode_excess_move_count,
                "xt_barcode_compare_state": persisted_picking.xt_barcode_compare_state,
                "xt_barcode_progress_percent": persisted_picking.xt_barcode_progress_percent,
                "xt_barcode_has_scanned_products": persisted_picking.xt_barcode_has_scanned_products,
                "xt_barcode_next_step": persisted_picking.xt_barcode_next_step,
                "xt_barcode_zero_scan_message": persisted_picking.xt_barcode_zero_scan_message,
                "xt_barcode_pending_summary": persisted_picking.xt_barcode_pending_summary,
                "xt_barcode_pending_move_ids": [(6, 0, persisted_picking.xt_barcode_pending_move_ids.ids)],
                "xt_barcode_focus_move_id": persisted_picking.xt_barcode_focus_move_id.id,
                "xt_barcode_focus_product_label": persisted_picking.xt_barcode_focus_product_label,
                "xt_barcode_focus_quantity_label": persisted_picking.xt_barcode_focus_quantity_label,
            }
        )

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        picking = self._xt_barcode_get_onchange_target()
        result = picking._apply_scanned_barcode(barcode, raise_on_error=False)
        self._xt_barcode_sync_onchange_state(picking)
        return result

    def action_scan_barcode(self, barcode):
        self.ensure_one()
        return self._apply_scanned_barcode(barcode, raise_on_error=True)

    def action_xt_barcode_validate(self):
        self.ensure_one()
        errors = self._get_barcode_validation_errors()
        if errors:
            raise UserError("\n".join(errors))

        # Odoo 19: Asegurar que todas las líneas escaneadas están marcadas como "picked"
        # y que la demanda se ajusta si se ha escaneado más de la cuenta.
        for move in self.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            if move.xt_barcode_scanned_qty > move.product_uom_qty:
                move.write({'product_uom_qty': move.xt_barcode_scanned_qty})

            # Marcamos las líneas escaneadas como 'picked' para que Odoo no las ignore
            scanned_lines = move.move_line_ids.filtered(lambda ml: ml.xt_barcode_product_scanned)
            if scanned_lines:
                scanned_lines.write({'picked': True})

        # Almacenamos IDs de movimientos para buscar destinos después
        move_ids = self.move_ids.ids

        res = self.button_validate()

        if res is True:
            # Buscamos pickings que se hayan confirmado/asignado a raíz de esta validación
            following_pickings = self.env["stock.move"].browse(move_ids).move_dest_ids.picking_id.filtered(
                lambda p: p.state in ("assigned", "confirmed")
            )

            # En caso de entrada, interna o salida, mostramos los pickings relacionados
            # Si hay pickings confirmados a raíz de esta acción, los priorizamos
            # Si no, mostramos el picking que se acaba de validar
            pickings_to_show = following_pickings or self

            if self.picking_type_code in ("incoming", "internal", "outgoing"):
                return {
                    "name": _("Pickings confirmados") if following_pickings else _("Picking validado"),
                    "type": "ir.actions.act_window",
                    "res_model": "stock.picking",
                    "view_mode": "list,form",
                    "views": [[False, "list"], [False, "form"]],
                    "domain": [("id", "in", pickings_to_show.ids)],
                    "target": "current",
                    "context": self.env.context,
                }
        return res
