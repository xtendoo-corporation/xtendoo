# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = ["barcodes.barcode_events_mixin", "stock.picking"]
    _name = "stock.picking"

    def on_barcode_scanned(self, barcode):

        # print("self location_id", self.location_id)
        print("self.id", self.id)
        print("dict context",dict(self.env.context))

        StockPickingBarcodesRead = self.env["stock.picking.barcodes.read"]
        # StockPickingBarcodesRead.picking_id = self.id
        StockPickingBarcodesRead.with_context({'picking_id':self.id}).on_barcode_scanned(barcode)

    def action_done(self):
        if self.check_done_conditions():
            res = self._process_stock_move_line()
            if res:
                self._add_read_log(res)
                self.candidate_picking_ids.scan_count += 1


    def action_barcode_scan(self):
        out_picking = self.picking_type_code == "outgoing"
        location = self.location_id if out_picking else self.location_dest_id
        action = self.env.ref(
            "stock_barcodes.action_stock_barcodes_read_picking"
        ).read()[0]
        action["context"] = {
            "default_location_id": location.id,
            "default_partner_id": self.partner_id.id,
            "default_picking_id": self.id,
            "default_res_model_id": self.env.ref("stock.model_stock_picking").id,
            "default_res_id": self.id,
            "default_picking_type_code": self.picking_type_code,
        }
        return action


class StockPickingBarcodesRead(models.AbstractModel):
    _name = "stock.picking.barcodes.read"
    # _inherit = 'barcodes.barcode_events_mixin'
    _description = "Stock Picking read barcode"
    # To prevent remove the record wizard until 2 days old
    _transient_max_hours = 48

    barcode = fields.Char()
    res_model_id = fields.Many2one(comodel_name="ir.model", index=True,)
    res_id = fields.Integer(index=True)
    product_id = fields.Many2one(comodel_name="product.product",)
    product_tracking = fields.Selection(related="product_id.tracking", readonly=True,)
    lot_id = fields.Many2one(comodel_name="stock.production.lot",)
    location_id = fields.Many2one(comodel_name="stock.location",)
    packaging_id = fields.Many2one(comodel_name="product.packaging",)
    packaging_qty = fields.Float(
        string="Package Qty", digits=dp.get_precision("Product Unit of Measure"),
    )
    product_qty = fields.Float(digits=dp.get_precision("Product Unit of Measure"),)
    manual_entry = fields.Boolean(string="Manual entry data",)
    # Computed field for display all scanning logs from res_model and res_id
    # when change product_id
    scan_log_ids = fields.Many2many(
        comodel_name="stock.barcodes.read.log", compute="_compute_scan_log_ids",
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        readonly=True,
    )    
    message_type = fields.Selection(
        [
            ("info", "Barcode read with additional info"),
            ("not_found", "No barcode found"),
            ("more_match", "More than one matches found"),
            ("success", "Barcode read correctly"),
        ],
        readonly=True,
    )
    message = fields.Char(readonly=True)

    @api.onchange("location_id")
    def onchange_location_id(self):
        self.packaging_id = False
        self.product_id = False

    @api.onchange("packaging_qty")
    def onchange_packaging_qty(self):
        if self.packaging_id:
            self.product_qty = self.packaging_qty * self.packaging_id.qty

    def _set_messagge_info(self, message_type, message):
        """
        Set message type and message description.
        For manual entry mode barcode is not set so is not displayed
        """
        self.message_type = message_type
        if self.barcode:
            self.message = _("Barcode: %s (%s)") % (self.barcode, message)
        else:
            self.message = "%s" % message

    def process_barcode(self, barcode):
        """ Only has been implemented AI (01, 02, 10, 37), so is possible that
        scanner reads a barcode ok but this one is not precessed.
        """

        print("process_barcode********************")
        print("picking_id*************************",self._context.get('picking_id'))

        try:
            barcode_decoded = self.env["gs1_barcode"].decode(barcode)
        except Exception:
            self.env.user.notify_danger(message=_('Barcode error formated!'))
            print("exception decode!!!!!!!!!!!!!!!!!!!!")
            return False

        print("barcode_decoded********************", barcode_decoded)

        processed = False
        package_barcode = barcode_decoded.get("01", False)
        product_barcode = barcode_decoded.get("02", False)
        if not product_barcode:
            # Sometimes the product does not yet have a GTIN. In this case
            # try the AI 240 'Additional product identification assigned
            # by the manufacturer'.
            product_barcode = barcode_decoded.get("240", False)
        lot_barcode = barcode_decoded.get("10", False)
        product_qty = barcode_decoded.get("37", False)
        if product_barcode:

            print("product_barcode**********************", product_barcode)

            product = self.env["product.product"].search(
                self._barcode_domain(product_barcode)
            )
            if not product:
                print("product_not_found**********************", product)
                self.env.user.notify_danger(message=_('Barcode for product not found'))
                return False
            else:
                processed = True
                self.action_product_scaned_post(product)
        if package_barcode:
            packaging = self.env["product.packaging"].search(
                self._barcode_domain(package_barcode)
            )
            if not packaging:
                raise ValidationError(_("Barcode for product packaging not found."))
                return False
            if len(packaging) > 1:
                raise ValidationError(_("More than one package found"))
                return False
            processed = True
            self.action_packaging_scaned_post(packaging)
        if lot_barcode and self.product_id.tracking != "none":
            print("process_lot(barcode_decoded)********************", barcode_decoded)
            self.process_lot(barcode_decoded)
            processed = True
        if product_qty:
            print("product_qty********************", product_qty)
            self.product_qty = product_qty
        if processed:

            print("action_done********************")

            self.action_done()
            self._set_messagge_info("success", _("Barcode read correctly"))
            return True
        self._set_messagge_info("not_found", _("Barcode not found"))
        return False

    def _prepare_lot_values(self, barcode_decoded):
        lot_barcode = barcode_decoded.get('10', False)
        return {
            'name': lot_barcode,
            'product_id': self.product_id.id,
        }

    def _create_lot(self, barcode_decoded):
        return self.env['stock.production.lot'].create(
            self._prepare_lot_values(barcode_decoded))

    def process_lot(self, barcode_decoded):
        lot_barcode = barcode_decoded.get('10', False)
        lot = self.env['stock.production.lot'].search([
            ('name', '=', lot_barcode),
            ('product_id', '=', self.product_id.id),
        ])
        if not lot:
            lot = self._create_lot(barcode_decoded)
        self.lot_id = lot

    def _barcode_domain(self, barcode):
        return [("barcode", "=", barcode)]

    def on_barcode_scanned(self, barcode):
        self.barcode = barcode
        self.reset_qty()
        self.process_barcode(barcode)

    def check_done_conditions(self):
        if not self.product_qty:

            print("check_done_conditions***************", self.product_qty)

            self._set_messagge_info("info", _("Waiting quantities"))
            return False
        if self.manual_entry:
            self._set_messagge_info("success", _("Manual entry OK"))
        return True

    def action_done(self):

        print("action_done**********************")

        if not self.check_done_conditions():
            return False
        self._add_read_log()
        return True

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

    def action_manual_entry(self):
        return True

    def _prepare_scan_log_values(self, log_detail=False):
        return {
            "name": self.barcode,
            "location_id": self.location_id.id,
            "product_id": self.product_id.id,
            "packaging_id": self.packaging_id.id,
            "lot_id": self.lot_id.id,
            "packaging_qty": self.packaging_qty,
            "product_qty": self.product_qty,
            "manual_entry": self.manual_entry,
            "res_model_id": self.res_model_id.id,
            "res_id": self.res_id,
        }

    def _add_read_log(self, log_detail=False):
        if self.product_qty:
            vals = self._prepare_scan_log_values(log_detail)
            self.env["stock.barcodes.read.log"].create(vals)

    @api.depends("product_id", "lot_id")
    def _compute_scan_log_ids(self):
        logs = self.env["stock.barcodes.read.log"].search(
            [
                ("res_model_id", "=", self.res_model_id.id),
                ("res_id", "=", self.res_id),
                ("location_id", "=", self.location_id.id),
                ("product_id", "=", self.product_id.id),
            ],
            limit=10,
        )
        self.scan_log_ids = logs

    def reset_qty(self):
        self.product_qty = 0
        self.packaging_qty = 0

    def action_undo_last_scan(self):
        return True
