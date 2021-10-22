# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, models


class WizStockBarcodesRead(models.AbstractModel):
    _inherit = "wiz.stock.barcodes.read"

    def process_barcode(self, barcode_lot):
        index = barcode_lot.find(";")
        if index == -1:
            return super().process_barcode(barcode_lot)

        barcode = barcode_lot[:index]
        lot = barcode_lot[index + 1:]

        if not barcode:
            self._set_message_error("Código de barras no valido")
            return

        if not lot:
            self._set_message_error("Lote no valido")
            return

        self.barcode = barcode
        product = self.env["product.product"].search(
            [("barcode", "=", barcode)]
        )
        if not product:
            self._set_message_error("Código de barras no encontrado")
            return

        if len(product) > 1:
            self._set_message_error("Más de un producto encontrado")
            return

        self.action_post_product_scanned(product)

        line = self._get_line_to_assign(product)
        if not line:
            return

        if not self._is_product_lot_valid(product, line, lot):
            return

        self.action_done()
