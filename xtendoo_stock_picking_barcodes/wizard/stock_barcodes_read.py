# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models


class WizStockBarcodesRead(models.AbstractModel):
    _name = 'wiz.stock.barcodes.read'

    _inherit = 'barcodes.barcode_events_mixin'

    _description = 'Wizard to read barcode'
    # To prevent remove the record wizard until 2 days old
    _transient_max_hours = 48

    barcode = fields.Char()
    res_model_id = fields.Many2one(
        comodel_name='ir.model',
        index=True,
    )
    res_id = fields.Integer(
        index=True
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
    )
    product_tracking = fields.Selection(
        related='product_id.tracking',
        readonly=True,
    )
    lot_id = fields.Many2one(
        comodel_name='stock.production.lot',
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
    )
    packaging_id = fields.Many2one(
        comodel_name='product.packaging',
    )
    packaging_qty = fields.Float(
        string='Package Qty',
        digits='Product Unit of Measure',
    )
    product_qty = fields.Float(
        digits='Product Unit of Measure',
        default=1,
    )
    manual_entry = fields.Boolean(
        string='Manual entry data',
    )
    message_type = fields.Selection([
        ('info', 'Barcode read with additional info'),
        ('not_found', 'No barcode found'),
        ('more_match', 'More than one matches found'),
        ('success', 'Barcode read correctly'),
        ],
        readonly=True
    )
    message = fields.Char(
        readonly=True
    )

    @api.onchange('location_id')
    def onchange_location_id(self):
        self.packaging_id = False
        self.product_id = False

    @api.onchange('packaging_qty')
    def onchange_packaging_qty(self):
        if self.packaging_id:
            self.product_qty = self.packaging_qty * self.packaging_id.qty

    def process_barcode(self, barcode):
        domain = [('barcode', '=', barcode)]

        print("domain :::", domain)

        product = self.env['product.product'].search(domain)
        if product:
            self.action_product_scaned_post(product)
        else:
            self.env.user.notify_danger(
                message='Barcode for product not found')
            return

        if len(product) > 1:
            self.env.user.notify_danger(
                message='More than one product found')
            return

        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == self.product_id and l.product_uom_qty >= l.quantity_done + self.product_qty
        )
        if not lines:
            self.env.user.notify_danger(
                message="There are no lines to assign that quantity")
            return

        if self.env.user.has_group('product.group_stock_packaging'):
            packaging = self.env['product.packaging'].search(domain)
            if packaging:
                if len(packaging) > 1:
                    self.env.user.notify_danger(
                        message='More than one package found')
                    return
                self.action_packaging_scaned_post(packaging)
                self.action_done()
                return

        if self.env.user.has_group('stock.group_production_lot'):
            lot_domain = [('name', '=', barcode)]
            if self.product_id:
                lot_domain.append(('product_id', '=', self.product_id.id))
            lot = self.env['stock.production.lot'].search(lot_domain)
            if len(lot) == 1:
                self.product_id = lot.product_id
            if lot:
                self.action_lot_scaned_post(lot)
                self.action_done()
                return
        location = self.env['stock.location'].search(domain)
        if location:
            self.location_id = location
            self.env.user.notify_danger(
                message='Waiting product')
            return

        self.action_done()

    def _barcode_domain(self, barcode):
        return [('barcode', '=', barcode)]

    def on_barcode_scanned(self, barcode):
        self.barcode = barcode
        self.reset_qty()
        self.process_barcode(barcode)

    def check_done_conditions(self):
        if not self.product_qty:
            self.env.user.notify_danger(
                message='Waiting quantities')
            return False
        if self.manual_entry:
            self.env.user.notify_success(
                message='Manual entry OK')
        return True

    def action_done(self):
        return self.check_done_conditions()

    def action_cancel(self):
        return True

    def action_product_scaned_post(self, product):
        self.packaging_id = False
        if self.product_id != product:
            self.lot_id = False
        self.product_id = product
        self.product_qty = 0.0 if self.manual_entry else 1.0

    def action_packaging_scaned_post(self, packaging):
        self.packaging_id = packaging
        if self.product_id != packaging.product_id:
            self.lot_id = False
        self.product_id = packaging.product_id
        self.packaging_qty = 0.0 if self.manual_entry else 1.0
        self.product_qty = packaging.qty * self.packaging_qty

    def action_lot_scaned_post(self, lot):
        self.lot_id = lot
        self.product_qty = 0.0 if self.manual_entry else 1.0

    def action_clean_lot(self):
        self.lot_id = False

    def reset_qty(self):
        self.product_qty = 0
        self.packaging_qty = 0

