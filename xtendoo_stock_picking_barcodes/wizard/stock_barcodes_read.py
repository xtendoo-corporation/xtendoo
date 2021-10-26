# Copyright 2021 Manuel Calero - https://xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.tools import float_repr, float_round


class WizStockBarcodesRead(models.AbstractModel):
    _name = "wiz.stock.barcodes.read"
    _inherit = "barcodes.barcode_events_mixin"
    _description = "Wizard to read barcode"
    _transient_max_hours = 48

    barcode = fields.Char()
    res_model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
    )
    res_id = fields.Integer(
        index=True
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
    )
    product_tracking = fields.Selection(
        related="product_id.tracking",
        readonly=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.production.lot",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
    )
    product_qty = fields.Float(
        digits=(16, 2),
        default=1,
    )
    manual_entry = fields.Boolean(
        string="Manual entry data",
    )
    message_type = fields.Selection(
        [
            ("error", "Barcode not read correctly"),
            ("success", "Barcode read correctly"),
        ],
        readonly=True,
    )
    message = fields.Char(
        readonly=True,
    )

    def _get_product_qty(self):
        return float(float_repr(self.product_qty, 3))

    @api.onchange("location_id")
    def onchange_location_id(self):
        self.product_id = False

    def _is_product_lot_valid(self, product, line, lot_name=False):
        if product.tracking == "none":
            return True

        if not lot_name:
            lot = line.get_lot()
        else:
            lot = (
                self.env["stock.production.lot"]
                .sudo()
                .search([("product_id", "=", product.id), ("name", "=", lot_name)], limit=1)
            )

        if not lot:
            self._set_message_error("Lote %s no encontrado" % lot)
            return False

        if lot.locked:
            self._set_message_error("El lote %s esta bloqueado" % lot)
            return False
        self.lot_id = lot
        return True

    def _get_line_to_assign(self, product):
        if product.uom_qty > 0:
            self.product_qty = product.uom_qty

        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == product
        )
        if not lines:
            self._set_message_error("No hay líneas para asignar al producto %s" % product.name)
            return False

        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == product
            and l.product_uom_qty >= l.quantity_done + self._get_product_qty()
        )
        if lines:
            return lines[0]
        # not enough quantity
        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == product and l.product_uom_qty >= l.quantity_done
        ).sorted(
            key=lambda l: l.product_uom_qty - l.quantity_done, reverse=True,
        )
        if not lines:
            self._set_message_error(
                "No hay líneas para asignar al producto")
            return False

        self.product_qty = lines[0].product_uom_qty - lines[0].quantity_done
        return lines[0]

    def process_barcode(self, barcode):
        self.barcode = barcode
        product = self.env["product.product"].search([("barcode", "=", barcode)])
        if not product:
            self._set_message_error("Código de barras %s no encontrado" % barcode)
            return

        if len(product) > 1:
            self._set_message_error("Más de un producto encontrado")
            return

        self.action_post_product_scanned(product)

        line = self._get_line_to_assign(product)
        if not line:
            return

        if not self._is_product_lot_valid(product, line):
            return

        self.action_done()

    def on_barcode_scanned(self, barcode):
        self._reset_wizard()
        self.process_barcode(barcode)

    def check_done_conditions(self):
        if not self.product_id:
            self._set_message_error("Producto no encontrado")
            return False

        if not self.product_qty:
            self._set_message_error("Esperando cantidades")
            return False

        if self.product_id.tracking != "none" and not self.lot_id:
            self._set_message_error("Esperando lote")
            return False

        return True

    def action_done(self):
        if self.check_done_conditions():
            self.candidate_picking_ids.scan_count += 1

    def action_cancel(self):
        return True

    def _set_product_quantity(self):
        self.product_qty = 0.0 if self.manual_entry else 1.0

    def action_post_product_scanned(self, product):
        if self.product_id != product:
            self.product_id = product
            self.lot_id = False
        self._set_product_quantity()

    def _reset_lot(self):
        self.lot_id = False

    def _reset_wizard(self):
        self.product_qty = 0.0 if self.manual_entry else 1.0
        self.message_type = ""
        self.message = ""

    def _reset_product(self):
        self.product_id = False

    def _set_message_success(self, message):
        self.message_type = "success"
        if self.barcode:
            self.message = "Código de barras: {} ({})".format(self.barcode, message)
        else:
            self.message = "%s" % message

    def _set_message_error(self, message):
        self.message_type = "error"
        if self.barcode:
            self.message = "¡Error! Código de barras: {} ({})".format(
                self.barcode, message
            )
        else:
            self.message = "¡Error! %s" % message

