# Copyright 2020
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare, float_repr


class WizStockBarcodesReadPicking(models.TransientModel):
    _name = "wiz.stock.barcodes.read.picking"
    _inherit = "wiz.stock.barcodes.read"
    _description = "Wizard to read barcode on picking"

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Picking",
        readonly=True,
    )
    picking_partner = fields.Many2one(
        comodel_name="res.partner",
        related="picking_id.partner_id",
        readonly=True,
        string="Partner",
    )
    picking_state = fields.Selection(
        related="picking_id.state",
        readonly=True,
    )
    picking_date = fields.Datetime(
        related="picking_id.date",
        readonly=True,
        string="Creation Date",
    )
    move_ids_without_package = fields.One2many(
        related="picking_id.move_ids_without_package",
        readonly=True,
        string="Lines",
    )
    candidate_picking_ids = fields.One2many(
        comodel_name="wiz.candidate.picking",
        inverse_name="wiz_barcode_id",
        string="Candidate pickings",
        readonly=True,
    )
    line_picking_ids = fields.One2many(
        comodel_name="wiz.line.picking",
        inverse_name="wiz_barcode_id",
        string="Line pickings",
        readonly=True,
    )
    picking_product_qty = fields.Float(
        string="Picking quantities",
        digits="Product Unit of Measure",
        readonly=True,
    )
    picking_type_code = fields.Selection(
        [
            ("incoming", "Vendors"),
            ("outgoing", "Customers"),
            ("internal", "Internal"),
        ],
        "Type of Operation",
    )

    def name_get(self):
        return [
            (
                rec.id,
                "{} - {} - {}".format(
                    _("Barcode reader"),
                    rec.picking_id.name or rec.picking_type_code,
                    self.env.user.name,
                ),
            )
            for rec in self
        ]

    def _set_default_picking(self):
        picking_id = self.env.context.get("default_picking_id", False)
        if picking_id:
            self._set_candidate_pickings(self.env["stock.picking"].browse(picking_id))

    def _set_default_message_type(self):
        message_type = self.env.context.get("default_message_type", False)
        if message_type:
            self.message_type = message_type

    def _set_default_message(self):
        message = self.env.context.get("default_message", False)
        if message:
            self.message = message

    def _set_default_manual_entry(self):
        manual_entry = self.env.context.get("default_manual_entry", False)
        if manual_entry:
            self.manual_entry = manual_entry

    @api.model
    def create(self, vals):
        # When user click any view button the wizard record is create and the
        # picking candidates have been lost, so we need set it.
        wiz = super().create(vals)
        if wiz.picking_id:
            wiz._set_candidate_pickings(wiz.picking_id)
        return wiz

    @api.onchange("picking_id")
    def onchange_picking_id(self):
        # Add to candidate pickings the default picking. We are in a wizard
        # view, so for create a candidate picking with the same default picking
        # we need create it in this onchange
        self._set_default_picking()
        self._set_default_manual_entry()
        self._set_default_message_type()
        self._set_default_message()

    def action_done(self):
        if self._process_stock_move_line():
            self._update_line_picking()
            self._clean_line_picking()

    def _get_action(self):
        if self.picking_id.picking_type_code == "outgoing":
            location = self.picking_id.location_id
        else:
            location = self.picking_id.location_dest_id
        action = self.env.ref(
            "xtendoo_stock_picking_barcodes.action_stock_barcodes_read_picking"
        ).read()[0]
        action["context"] = {
            "default_picking_id": self.picking_id.id,
            "default_manual_entry": self.manual_entry,
            "default_location_id": location.id,
            "default_message_type": self.message_type,
            "default_message": self.message,
        }
        return action

    def action_manual_entry(self):
        if not self.check_done_conditions():
            return False
        if not self.is_available_lines():
            self._set_message_error("Demasiadas unidades para asignar este producto")
            return False
        self.insert_manual_entry()

    def action_over_processed_manual_entry(self):
        if not self.check_done_conditions():
            return False
        # self.update_sale_order()
        self.insert_manual_entry()

    def action_update_sale_order(self):
        if self.picking_id.sale_id:
            move_line = self.picking_id.sale_id.order_line.filtered(
                lambda l: l.product_id == self.product_id
                and self._get_product_qty() > (l.product_uom_qty - l.qty_delivered)
            )
            if not move_line:
                return False
            move_line.product_uom_qty = self._get_product_qty()

            picking_line = self.picking_id.move_ids_without_package.filtered(
                lambda l: l.product_id == self.product_id
            )
            if picking_line:
                picking_line.product_uom_qty = self._get_product_qty()

            # picking_line = self.picking_id.move_line_ids_without_package.filtered(
            #     lambda l: l.product_id == self.product_id
            # )
            # if picking_line:
            #     picking_line.product_uom_qty = self.product_qty

            picking_line = self.line_picking_ids.filtered(
                lambda l: l.product_id == self.product_id
            )
            if picking_line:
                picking_line.product_uom_qty = self._get_product_qty()

    def insert_manual_entry(self):
        if self._process_stock_move_line():
            self._update_line_picking()
            self._set_message_success("Entrada correcta")
            self._reset_manual_entry()
            self._clean_line_picking()

    def _update_line_picking(self):
        for line in self.line_picking_ids.filtered(
            lambda l: l.product_id == self.product_id
            and l.product_uom_qty >= l.quantity_done + self._get_product_qty()
        ):
            line.quantity_done = line.quantity_done + self._get_product_qty()
            break

    def _clean_line_picking(self):
        self.line_picking_ids = [
            (2, line.id)
            for line in self.line_picking_ids.filtered(
                lambda l: l.quantity_done >= l.product_uom_qty
            )
        ]

    def _prepare_move_line_values(self, candidate_move, available_qty):
        """When we've got an out picking, the logical workflow is that
           the scanned location is the location we're getting the stock
           from"""
        out_move = candidate_move.picking_code == "outgoing"
        location_id = self.location_id if out_move else self.picking_id.location_id
        location_dest_id = (
            self.picking_id.location_dest_id if out_move else self.location_id
        )
        return {
            "picking_id": self.picking_id.id,
            "move_id": candidate_move.id,
            "qty_done": available_qty,
            "product_uom_id": self.product_id.uom_po_id.id,
            "product_id": self.product_id.id,
            "location_id": location_id.id,
            "location_dest_id": location_dest_id.id,
            "lot_id": self.lot_id.id,
            "lot_name": self.lot_id.name,
        }

    def _states_move_allowed(self):
        return ["assigned", "confirmed"]

    def _prepare_stock_moves_domain(self):
        domain = [
            ("product_id", "=", self.product_id.id),
            ("picking_id.picking_type_id.code", "=", self.picking_type_code),
            ("state", "in", self._states_move_allowed()),
        ]
        if self.picking_id:
            domain.append(("picking_id", "=", self.picking_id.id))
        return domain

    def _set_candidate_pickings(self, candidate_pickings):
        vals = [(5, 0, 0)]
        vals.extend([(0, 0, {"picking_id": p.id,}) for p in candidate_pickings])
        self.candidate_picking_ids = vals
        # Only for test
        self._set_line_pickings(candidate_pickings)

    def _set_line_pickings(self, candidate_pickings):
        vals = [(5, 0, 0)]
        for p in candidate_pickings:
            for line in p.move_ids_without_package.filtered(
                lambda l: l.product_uom_qty > l.quantity_done
            ):
                vals.extend(
                    [
                        (
                            0,
                            0,
                            {
                                "picking_id": p.id,
                                "product_id": line.product_id.id,
                                "reserved_availability": line.reserved_availability,
                                "product_uom_qty": line.product_uom_qty,
                                "quantity_done": line.quantity_done,
                            },
                        )
                    ]
                )
        self.line_picking_ids = vals

    def _search_candidate_pickings(self, moves_todo=False):
        if not moves_todo:
            moves_todo = self.env["stock.move"].search(
                self._prepare_stock_moves_domain()
            )
        if not self.picking_id:
            candidate_pickings = moves_todo.mapped("picking_id")
            candidate_pickings_count = len(candidate_pickings)
            if candidate_pickings_count > 1:
                self._set_candidate_pickings(candidate_pickings)
                return False
            if candidate_pickings_count == 1:
                self.picking_id = candidate_pickings
                self._set_candidate_pickings(candidate_pickings)
        return True

    def _process_stock_move_line(self):
        """
        Search assigned or confirmed stock moves from a picking operation type
        or a picking. If there is more than one picking with demand from
        scanned product the interface allow to select what picking to work.
        If only there is one picking the scan data is assigned to it.
        """

        moves_todo = self.env["stock.move"].search(self._prepare_stock_moves_domain())

        # if not self._search_candidate_pickings(moves_todo):
        #     return False

        lines = moves_todo.mapped("move_line_ids").filtered(
            lambda l: (
                l.picking_id == self.picking_id
                and l.product_id == self.product_id
                and l.lot_id == self.lot_id
            )
        )
        available_qty = self.product_qty

        move_lines_dic = {}

        for line in lines:
            if line.product_uom_qty:
                assigned_qty = min(
                    max(line.product_uom_qty - line.qty_done, 0.0), available_qty
                )
            else:
                assigned_qty = available_qty
            line.write({"qty_done": line.qty_done + assigned_qty})
            available_qty -= assigned_qty
            if assigned_qty:
                move_lines_dic[line.id] = assigned_qty
            if (
                float_compare(
                    available_qty, 0.0, precision_rounding=line.product_id.uom_id.rounding,
                )
                < 1
            ):
                break

        if (
            float_compare(
                available_qty, 0, precision_rounding=self.product_id.uom_id.rounding
            )
            > 0
        ):
            # Create an extra stock move line if this product has an
            # initial demand.

            moves = self.picking_id.move_lines.filtered(
                lambda m: (
                    m.product_id == self.product_id
                    and m.state in self._states_move_allowed()
                )
            )

            if not moves:
                self._set_message_error("No hay líneas para asignar este producto.")
                return False
            else:
                line = self.env["stock.move.line"].create(
                    self._prepare_move_line_values(moves[0], available_qty)
                )
                move_lines_dic[line.id] = available_qty
        self.picking_product_qty = sum(moves_todo.mapped("quantity_done"))
        return move_lines_dic

    def is_available_lines(self):
        return self.line_picking_ids.filtered(
            lambda l: l.product_id == self.product_id
            and l.product_uom_qty >= l.quantity_done + self.product_qty
        )

    def check_done_conditions(self):
        if not super().check_done_conditions():
            return False
        if not self.line_picking_ids.filtered(lambda l: l.product_id == self.product_id):
            self._set_message_error("El producto no esta presente en este albarán")
            return False
        return True

    def process_barcode(self, barcode):
        if "o.btn-validate" in barcode:
            self.action_validate_picking()
            return
        if "o.btn-manual" in barcode:
            self.action_set_manual_entry()
            return
        if "o.btn-auto" in barcode:
            self.action_quit_manual_entry()
            return
        super().process_barcode(barcode)

    def action_cancel_picking(self):
        picking = self.picking_id
        if not picking:
            return {
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'type': 'ir.actions.act_window',
            }

    def action_validate_picking(self):
        picking = self.env["stock.picking"].browse(
            self.env.context.get("picking_id", False)
        )

        if not picking:
            picking = self.picking_id

        if picking:
            picking.button_validate()
        return {
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'type': 'ir.actions.act_window',
        }

    def action_validate_print_picking(self):
        picking = self.env["stock.picking"].browse(
            self.env.context.get("picking_id", False)
        )

        if not picking:
            picking = self.picking_id

        if picking:
            context = {
                'active_ids': [picking.id],
                'res_ids': [picking.id],
                'res_model': 'stock.picking',
            }
            return {
                'type': 'ir.actions.report',
                'res_model': 'stock.picking',
                'binding_model_id': picking,
                'report_name': 'stock.action_report_picking',
                'report_type': 'qweb-pdf',
                'print_report_name': 'Picking report',
                'context': context,
            }
    def action_set_manual_entry(self):
        self.manual_entry = True
        self._reset_message()
        self._reset_manual_entry()

    def action_quit_manual_entry(self):
        self.manual_entry = False
        self._reset_message()
        self._reset_manual_entry()

    def _reset_manual_entry(self):
        self._reset_product()
        self._reset_lot()
        self._reset_qty()

    def _reset_qty(self):
        self.product_qty = 0

    def _reset_message(self):
        self.message = False
        self.message_type = False


class WizCandidatePicking(models.TransientModel):
    """
    TODO: explain
    """

    _name = "wiz.candidate.picking"
    _description = "Candidate pickings for barcode interface"
    # To prevent remove the record wizard until 2 days old
    _transient_max_hours = 48

    wiz_barcode_id = fields.Many2one(
        comodel_name="wiz.stock.barcodes.read.picking", readonly=True,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Picking", readonly=True,
    )
    wiz_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        related="wiz_barcode_id.picking_id",
        string="Wizard Picking",
        readonly=True,
    )
    name = fields.Char(
        related="picking_id.name", readonly=True, string="Candidate Picking",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="picking_id.partner_id",
        readonly=True,
        string="Partner",
    )
    state = fields.Selection(related="picking_id.state", readonly=True,)
    date = fields.Datetime(
        related="picking_id.date", readonly=True, string="Creation Date",
    )
    move_line_ids_without_package = fields.One2many(
        related="picking_id.move_line_ids_without_package",
        readonly=True,
        string="Lines",
    )
    product_qty_reserved = fields.Float(
        "Reserved",
        compute="_compute_picking_quantity",
        digits="Product Unit of Measure",
        readonly=True,
    )
    product_uom_qty = fields.Float(
        "Demand",
        compute="_compute_picking_quantity",
        digits="Product Unit of Measure",
        readonly=True,
    )
    product_qty_done = fields.Float(
        "Done",
        compute="_compute_picking_quantity",
        digits="Product Unit of Measure",
        readonly=True,
    )
    # For reload kanban view
    scan_count = fields.Integer()

    @api.depends("scan_count")
    def _compute_picking_quantity(self):
        for candidate in self:
            qty_reserved = 0
            qty_demand = 0
            qty_done = 0
            candidate.product_qty_reserved = sum(
                candidate.picking_id.mapped("move_lines.reserved_availability")
            )
            for move in candidate.picking_id.move_lines:
                qty_reserved += move.reserved_availability
                qty_demand += move.product_uom_qty
                qty_done += move.quantity_done
            candidate.update(
                {
                    "product_qty_reserved": qty_reserved,
                    "product_uom_qty": qty_demand,
                    "product_qty_done": qty_done,
                }
            )

    def _get_wizard_barcode_read(self):
        return self.env["wiz.stock.barcodes.read.picking"].browse(
            self.env.context["wiz_barcode_id"]
        )

    def action_lock_picking(self):
        wiz = self._get_wizard_barcode_read()
        picking_id = self.env.context["picking_id"]
        wiz.picking_id = picking_id
        wiz._set_candidate_pickings(wiz.picking_id)
        return wiz.action_done()

    def action_unlock_picking(self):
        wiz = self._get_wizard_barcode_read()
        wiz.update(
            {
                "picking_id": False,
                "candidate_picking_ids": False,
                "message_type": False,
                "message": False,
            }
        )
        return wiz.action_cancel()

    def action_validate_picking(self):
        picking = self.env["stock.picking"].browse(
            self.env.context.get("picking_id", False)
        )
        return picking.button_validate()


class WizLinePicking(models.TransientModel):
    _name = "wiz.line.picking"
    _description = "Line pickings for barcode interface"
    # To prevent remove the record wizard until 2 days old
    _transient_max_hours = 48

    wiz_barcode_id = fields.Many2one(
        comodel_name="wiz.stock.barcodes.read.picking", readonly=True,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Picking", readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", required=True,
    )
    reserved_availability = fields.Float(
        string="Reserved", digits="Product Unit of Measure", readonly=True,
    )
    product_uom_qty = fields.Float(
        string="Demand", digits="Product Unit of Measure", readonly=True,
    )
    quantity_done = fields.Float(
        string="Done", digits="Product Unit of Measure", readonly=True,
    )
    state = fields.Selection(
        selection=[("none", "None"), ("any", "Any"), ("all", "All")],
        compute="_compute_state",
        string="State",
        store=True,
    )
    lots = fields.Char(
        compute="_compute_lots",
        string="Lots",
        readonly=True,
    )
    # For reload kanban view
    scan_count = fields.Integer()

    @api.depends("quantity_done")
    def _compute_lots(self):
        for line in self:
            lots = ""
            for lot in line.picking_id.move_line_ids_without_package.filtered(
                lambda l: l.product_id == line.product_id and l.lot_id
            ):
                lots += lot.lot_id.name + " (" + str(lot.qty_done) + "),"
            line.lots = lots[:-1]

    @api.depends("quantity_done")
    def _compute_state(self):
        for line in self:
            if line.quantity_done == 0:
                line.state = "none"
            elif 0 < line.quantity_done < line.product_uom_qty:
                line.state = "any"
            else:
                line.state = "all"

    def _get_wizard_barcode_read(self):
        return self.env["wiz.stock.barcodes.read.picking"].browse(
            self.env.context["wiz_barcode_id"]
        )

    def get_lot(self):
        for line in self:
            lines = line.picking_id.move_line_ids_without_package.filtered(
                lambda l: l.product_id == line.product_id and l.lot_id
            )
            if lines:
                return lines[0].lot_id[0]
        return False
