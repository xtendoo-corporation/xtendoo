import logging

from odoo import _, models
from odoo.exceptions import UserError
from odoo.fields import Command

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "barcodes.barcode_events_mixin"]

    def _barcode_scan_log_prefix(self):
        self.ensure_one()
        order_ref = self.name or f"sale.order({self.id or 'new'})"
        return f"[sale_barcode_scanner] [{order_ref}]"

    def _barcode_scan_warning(self, message, *, raise_on_error=False):
        self.ensure_one()
        _logger.warning("%s %s", self._barcode_scan_log_prefix(), message)
        if raise_on_error:
            raise UserError(message)
        return {
            "warning": {
                "title": _("Escaneo de código de barras"),
                "message": message,
            }
        }

    def _barcode_scan_allowed_states(self):
        return {"draft", "sent"}

    def _is_barcode_scan_allowed(self):
        self.ensure_one()
        return self.state in self._barcode_scan_allowed_states()

    def _get_barcode_scan_product_domain(self, barcode):
        self.ensure_one()
        return [("barcode", "=", barcode), ("sale_ok", "=", True)]

    def _find_barcode_scan_products(self, barcode):
        self.ensure_one()
        return self.env["product.product"].search(
            self._get_barcode_scan_product_domain(barcode),
            limit=2,
        )

    def _get_existing_scanned_product_line(self, product):
        self.ensure_one()
        return self.order_line.sorted(lambda line: (line.sequence, line.id)).filtered(
            lambda line: not line.display_type and line.product_id == product
        )[:1]

    def _prepare_scanned_order_line_values(self, product):
        self.ensure_one()
        return {
            "product_id": product.id,
            "product_uom_qty": 1.0,
            "sequence": self._get_new_line_sequence("order_line", False),
        }

    def _apply_scanned_barcode(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        barcode = (barcode or "").strip()
        if not barcode:
            return {"status": "ignored"}

        _logger.info("%s Escaneo recibido: %s", self._barcode_scan_log_prefix(), barcode)

        if not self._is_barcode_scan_allowed():
            return self._barcode_scan_warning(
                _(
                    "El pedido no es editable. No se pueden añadir productos por código de barras."
                ),
                raise_on_error=raise_on_error,
            )

        products = self._find_barcode_scan_products(barcode)
        if not products:
            return self._barcode_scan_warning(
                _(
                    "No se ha encontrado ningún producto vendible con el código de barras '%(barcode)s'.",
                    barcode=barcode,
                ),
                raise_on_error=raise_on_error,
            )
        if len(products) > 1:
            return self._barcode_scan_warning(
                _(
                    "Se han encontrado varios productos vendibles con el código de barras '%(barcode)s'. No se añadirá ningún producto automáticamente.",
                    barcode=barcode,
                ),
                raise_on_error=raise_on_error,
            )

        product = products[0]
        existing_line = self._get_existing_scanned_product_line(product)
        if existing_line:
            if existing_line.product_uom_id != product.uom_id:
                return self._barcode_scan_warning(
                    _(
                        "El producto '%(product)s' ya existe en una línea con una unidad de medida distinta ('%(uom)s'). No se puede incrementar automáticamente.",
                        product=product.display_name,
                        uom=existing_line.product_uom_id.display_name,
                    ),
                    raise_on_error=raise_on_error,
                )

            existing_line.product_uom_qty += 1.0
            _logger.info(
                "%s Línea existente incrementada para %s. Nueva cantidad: %s",
                self._barcode_scan_log_prefix(),
                product.display_name,
                existing_line.product_uom_qty,
            )
            return {
                "status": "incremented",
                "product_id": product.id,
                "line_id": existing_line.id or False,
                "quantity": existing_line.product_uom_qty,
            }

        self.update(
            {
                "order_line": [
                    Command.create(self._prepare_scanned_order_line_values(product))
                ]
            }
        )
        new_line = self.order_line.sorted(lambda line: (line.sequence, line.id)).filtered(
            lambda line: not line.display_type and line.product_id == product
        )[-1:]
        _logger.info(
            "%s Nueva línea creada para %s.",
            self._barcode_scan_log_prefix(),
            product.display_name,
        )
        return {
            "status": "created",
            "product_id": product.id,
            "line_id": new_line.id or False,
            "quantity": new_line.product_uom_qty if new_line else 1.0,
        }

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        result = self._apply_scanned_barcode(barcode, raise_on_error=False)
        if result.get("warning"):
            return result
        return False

    def action_scan_barcode(self, barcode):
        self.ensure_one()
        return self._apply_scanned_barcode(barcode, raise_on_error=True)

