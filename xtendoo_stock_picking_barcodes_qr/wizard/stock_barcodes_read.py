# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, models


class WizStockBarcodesRead(models.AbstractModel):
    _inherit = 'wiz.stock.barcodes.read'

    def process_barcode(self, barcode):
        """ Only has been implemented AI (01, 02, 10, 37), so is possible that
        scanner reads a barcode ok but this one is not precessed.
        """

        barcode="790069430305;LOT0003"

        self.product_qty = 1
        index = barcode.find(';')
        if index == -1:
            return super().process_barcode(barcode)
        product_barcode = barcode[:index]
        lot_barcode = barcode[index+1:]

        if not product_barcode or not lot_barcode:
            return False

        product = self.env['product.product'].search(
            [('barcode', '=', product_barcode)]
        )
        if product:
            self.action_product_scaned_post(product)
        else:
            self.env.user.notify_danger(
                message='Barcode for product not found')
            return False

        if product.tracking != 'none':
            lot = self.env['stock.production.lot'].search([
                ('product_id', '=', product.id),
                ('name', '=', lot_barcode),
            ])
            if not lot:
                self.env.user.notify_danger(
                    message='Lot for product not found')
                return False
            if lot.locked:
                self.env.user.notify_danger(
                    message='Lot is locked')
                return False
            self.lot_id = lot

        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == self.product_id and l.product_uom_qty >= l.quantity_done + self.product_qty
        )
        if not lines:
            self.env.user.notify_danger(
                message="There are no lines to assign that quantity")
            return False

        self.action_done()
