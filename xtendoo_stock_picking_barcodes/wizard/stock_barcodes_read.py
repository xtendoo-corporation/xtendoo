# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models


class WizStockBarcodesRead(models.AbstractModel):
    _name = 'wiz.stock.barcodes.read'
    _inherit = 'barcodes.barcode_events_mixin'
    _description = 'Wizard to read barcode'
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
        ('error', 'Barcode not read correctly'),
        ('success', 'Barcode read correctly'),
        ],
        readonly=True,
    )
    message = fields.Char(
        readonly=True,
    )

    @api.onchange('location_id')
    def onchange_location_id(self):
        self.packaging_id = False
        self.product_id = False

    @api.onchange('packaging_qty')
    def onchange_packaging_qty(self):
        if self.packaging_id:
            self.product_qty = self.packaging_qty * self.packaging_id.qty

    @api.onchange('message_type')
    def onchange_message_type(self):
        self.message = self.message_type

    def process_barcode(self, barcode):
        domain = [('barcode', '=', barcode)]
        product = self.env['product.product'].search(domain)
        if product:
            self.action_product_scaned_post(product)
        else:
            self._set_message_error('Código de barras para producto no encontrado')
            return

        if len(product) > 1:
            self._set_message_error('Mas de un producto encontrado')
            return

        lines = self.line_picking_ids.filtered(
            lambda l: l.product_id == self.product_id and l.product_uom_qty >= l.quantity_done + self.product_qty
        )
        if not lines:
            self._set_message_error('No hay líneas para asignar este producto')
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
            self._set_message_error('No hay almacen asignado')
            return

        self.action_done()

    def on_barcode_scanned(self, barcode):
        self.barcode = barcode
        self.reset_qty()
        self.process_barcode(barcode)

    def check_done_conditions(self):
        if not self.product_id:
            self._set_message_error('Producto no encontrado')
            return False

        if not self.product_qty:
            self._set_message_error('Esperando cantidades')
            return False

        if self.manual_entry:
            self._set_message_success('Entrada correcta')
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

    def _set_message_success(self, message):
        self.message_type = 'success'
        if self.barcode:
            self.message = _("Código de barras: %s (%s)") % (self.barcode, message)
        else:
            self.message = "%s" % message

    def _set_message_error(self, message):
        self.message_type = 'error'
        if self.barcode:
            self.message = _("¡Error! Código de barras: %s (%s)") % (self.barcode, message)
        else:
            self.message = "¡Error! %s" % message
