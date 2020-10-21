# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, models


class WizStockBarcodesRead(models.AbstractModel):
    _inherit = 'wiz.stock.barcodes.read'

    def process_barcode(self, barcode):
        """ Only has been implemented AI (01, 02, 10, 37), so is possible that
        scanner reads a barcode ok but this one is not precessed.
        """
        barcode="8429359001452;LOT0001"
        self.product_qty = 1

        print("Barcode::::::::::::::",barcode)
        try:
            index = barcode.find(';')
            if index == -1:
                return super().process_barcode(barcode)
            product_barcode = barcode[:index]
            lot_barcode = barcode[index+1:]

            print("Product_barcode:::::::", product_barcode)
            print("lot_barcode:::::::", lot_barcode)

        except Exception:
            print("Salida por Exception::::::::::::::", barcode)

        processed = False

        if product_barcode:
            product = self.env['product.product'].search(
                [('barcode', '=', product_barcode)]
            )
            if not product:
                self.env.user.notify_danger(
                    message='Barcode for product not found')
                return False
            else:
                processed = True
                self.action_product_scaned_post(product)

        if lot_barcode and product.tracking != 'none':
            lot = self.env['stock.production.lot'].search([
                ('product_id', '=', product.id),
                ('name', '=', lot_barcode),
            ])
            if not lot:
                self.env.user.notify_danger(
                    message='Lot for product not found')
                return False
            self.lot_id = lot
            processed = True
        if processed:
            self.action_done()
            return True
        return super().process_barcode(barcode)
