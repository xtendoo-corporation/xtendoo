# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models


class WizStockBarcodesRead(models.AbstractModel):
    _name = "wiz.stock.barcodes.read"
    _inherit = "barcodes.barcode_events_mixin"
    _description = "Wizard to read barcode"
    _transient_max_hours = 48

    barcode = fields.Char()
    res_model_id = fields.Many2one(comodel_name="ir.model", index=True,)
    res_id = fields.Integer(index=True)
    product_id = fields.Many2one(comodel_name="product.product",)
    product_tracking = fields.Selection(related="product_id.tracking", readonly=True,)
    lot_id = fields.Many2one(comodel_name="stock.production.lot",)
    location_id = fields.Many2one(comodel_name="stock.location",)
    product_qty = fields.Float(digits="Product Unit of Measure", default=1,)
    manual_entry = fields.Boolean(string="Manual entry data",)
    message_type = fields.Selection(
        [
            ("error", "Barcode not read correctly"),
            ("success", "Barcode read correctly"),
        ],
        readonly=True,
    )
    message = fields.Char(readonly=True,)

    @api.onchange("location_id")
    def onchange_location_id(self):
        self.product_id = False

    def _is_product_lot_valid(self, product, lot=False):
        if product.tracking != "none":

            print("product :::::", product)
            print("product.id :::::", product.id)
            print("lot :::::", lot)

            lot = (
                self.env["stock.production.lot"]
                .sudo()
                .search([("product_id", "=", product.id), ("name", "=", lot),])
            )

            print("despues de buscar :::::")

            if not lot:
                self._set_message_error("Lote no encontrado")
                return False
            if lot.locked:
                self._set_message_error("El lote esta bloqueado")
                return False
            self.lot_id = lot
        return True

    def _has_lines_to_assign(self, product):
        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == product
            and l.product_uom_qty >= l.quantity_done + self.product_qty
        )
        if lines:
            return True

        self._set_message_error("No hay líneas para asignar este producto")
        return False

    def process_barcode(self, barcode):
        self.barcode = barcode
        domain = [("barcode", "=", barcode)]
        product = self.env["product.product"].search(domain)
        if not product:
            self._set_message_error("Código de barras % para producto no encontrado")
            return

        if len(product) > 1:
            self._set_message_error("Más de un producto encontrado")
            return

        if not self._has_lines_to_assign(product):
            return

        if not self._is_product_lot_valid(product):
            return

        self.action_product_scanned_post(product)

        self.action_done()

    def on_barcode_scanned(self, barcode):
        self._reset_qty()
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

        # if self.product_id.uom_qty:
        #     self.product_qty = self.product_id.uom_qty
        # else:
        #     self.product_qty = 0.0 if self.manual_entry else 1.0

    def action_product_scanned_post(self, product):
        if self.product_id != product:
            self.product_id = product
            self.lot_id = False
        self._set_product_quantity()

    def _reset_lot(self):
        self.lot_id = False

    def _reset_qty(self):
        self.product_qty = 0.0 if self.manual_entry else 1.0

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

    def _reset_message(self):
        self.message_type = ""
        self.message = ""
