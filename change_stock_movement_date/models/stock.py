# coding: utf-8
from collections import defaultdict
from odoo import _, fields
from odoo.addons.stock.models.stock_move import StockMove
from odoo.addons.stock.models.stock_move_line import StockMoveLine
from odoo.addons.stock.models.stock_picking import Picking
from odoo.exceptions import UserError
from odoo.tools import OrderedSet
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

"""
Stock move methods
"""


def _action_done(self, cancel_backorder=False):
    self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
    moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
    moves_todo = self.env['stock.move']

    # Cancel moves where necessary ; we should do it before creating the extra moves because
    # this operation could trigger a merge of moves.
    for move in moves:
        if move.quantity_done <= 0:
            if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                move._action_cancel()

    # Create extra moves where necessary
    for move in moves:
        if move.state == 'cancel' or move.quantity_done <= 0:
            continue

        moves_todo |= move._create_extra_move()

    moves_todo._check_company()
    # Split moves where necessary and move quants
    for move in moves_todo:
        # To know whether we need to create a backorder or not, round to the general product's
        # decimal precision and not the product's UOM.
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
            # Need to do some kind of conversion here
            qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
            new_move = move._split(qty_split)
            move._unreserve_initial_demand(new_move)
            if cancel_backorder:
                self.env['stock.move'].browse(new_move)._action_cancel()
    moves_todo.mapped('move_line_ids').sorted()._action_done()
    # Check the consistency of the result packages; there should be an unique location across
    # the contained quants.
    for result_package in moves_todo.mapped('move_line_ids.result_package_id').filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
        if len(result_package.quant_ids.filtered(
                lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped(
                'location_id')) > 1:
            raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
    picking = moves_todo.mapped('picking_id')
    for m in moves_todo:
        move_date = m.picking_id.date_done if m.picking_id and m.picking_id.date_done else fields.Datetime.now()
        m.write({'state': 'done', 'date': move_date})

    move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
    for move_dest in moves_todo.move_dest_ids:
        move_dests_per_company[move_dest.company_id.id] |= move_dest
    for company_id, move_dests in move_dests_per_company.items():
        move_dests.sudo().with_context(force_company=company_id)._action_assign()

    # We don't want to create back order for scrap moves
    # Replace by a kwarg in master
    if self.env.context.get('is_scrap'):
        return moves_todo

    if picking and not cancel_backorder:
        picking._create_backorder()
    return moves_todo


StockMove._action_done = _action_done

"""
Stock move line methods
"""


def _action_done2(self):
    """ This method is called during a move's `action_done`. It'll actually move a quant from
    the source location to the destination location, and unreserve if needed in the source
    location.

    This method is intended to be called on all the move lines of a move. This method is not
    intended to be called when editing a `done` move (that's what the override of `write` here
    is done.
    """
    Quant = self.env['stock.quant']

    # First, we loop over all the move lines to do a preliminary check: `qty_done` should not
    # be negative and, according to the presence of a picking type or a linked inventory
    # adjustment, enforce some rules on the `lot_id` field. If `qty_done` is null, we unlink
    # the line. It is mandatory in order to free the reservation and correctly apply
    # `action_done` on the next move lines.
    ml_ids_to_delete = OrderedSet()
    lot_vals_to_create = []  # lot values for batching the creation
    associate_line_lot = []  # move_line to associate to the lot
    for ml in self:
        # Check here if `ml.qty_done` respects the rounding of `ml.product_uom_id`.
        uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')
        if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
            raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision \
                              defined on the unit of measure "%s". Please change the quantity done or the \
                              rounding precision of your unit of measure.') % (ml.product_id.display_name, ml.product_uom_id.name))

        qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
        if qty_done_float_compared > 0:
            if ml.product_id.tracking != 'none':
                picking_type_id = ml.move_id.picking_type_id
                if picking_type_id:
                    if picking_type_id.use_create_lots:
                        # If a picking type is linked, we may have to create a production lot on
                        # the fly before assigning it to the move line if the user checked both
                        # `use_create_lots` and `use_existing_lots`.
                        if ml.lot_name and not ml.lot_id:
                            lot_vals_to_create.append({'name': ml.lot_name, 'product_id': ml.product_id.id, 'company_id': ml.move_id.company_id.id})
                            associate_line_lot.append(ml)
                            continue  # Avoid the raise after because not lot_id is set
                    elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
                        # If the user disabled both `use_create_lots` and `use_existing_lots`
                        # checkboxes on the picking type, he's allowed to enter tracked
                        # products without a `lot_id`.
                        continue
                elif ml.move_id.inventory_id:
                    # If an inventory adjustment is linked, the user is allowed to enter
                    # tracked products without a `lot_id`.
                    continue

                if not ml.lot_id:
                    raise UserError(_('You need to supply a Lot/Serial number for product %s.') % ml.product_id.display_name)
        elif qty_done_float_compared < 0:
            raise UserError(_('No negative quantities allowed'))
        else:
            ml_ids_to_delete.add(ml.id)
    mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
    mls_to_delete.unlink()

    # add
    lots = self.env['stock.production.lot'].create(lot_vals_to_create)
    for ml, lot in zip(associate_line_lot, lots):
        ml.write({'lot_id': lot.id})

    mls_todo = (self - mls_to_delete)
    mls_todo._check_company()

    # Now, we can actually move the quant.
    ml_ids_to_ignore = OrderedSet()
    for ml in mls_todo:
        if ml.product_id.type == 'product':
            rounding = ml.product_uom_id.rounding

            # if this move line is force assigned, unreserve elsewhere if needed
            if not ml._should_bypass_reservation(ml.location_id) and float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=rounding) > 0:
                qty_done_product_uom = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id, rounding_method='HALF-UP')
                extra_qty = qty_done_product_uom - ml.product_qty
                ml_to_ignore = self.env['stock.move.line'].browse(ml_ids_to_ignore)
                ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id,
                                     ml_to_ignore=ml_to_ignore)
            # unreserve what's been reserved
            if not ml._should_bypass_reservation(ml.location_id) and ml.product_id.type == 'product' and ml.product_qty:
                try:
                    Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id,
                                                    owner_id=ml.owner_id, strict=True)
                except UserError:
                    Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=False, package_id=ml.package_id,
                                                    owner_id=ml.owner_id, strict=True)

            # move what's been actually done
            quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
            available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id,
                                                                      owner_id=ml.owner_id)
            if available_qty < 0 and ml.lot_id:
                # see if we can compensate the negative quants with some untracked quants
                untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id,
                                                              strict=True)
                if untracked_qty:
                    taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                    Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id,
                                                     owner_id=ml.owner_id)
                    Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id,
                                                     owner_id=ml.owner_id)
            Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id,
                                             owner_id=ml.owner_id, in_date=in_date)
        ml_ids_to_ignore.add(ml.id)
    # Reset the reserved quantity as we just moved it to the destination location.
    lines = mls_todo.with_context(bypass_reservation_update=True)
    for m_line in lines:
        m_line_date = m_line.picking_id.date_done if m_line.picking_id and m_line.picking_id.date_done else fields.Datetime.now()
        m_line.write({
            'product_uom_qty': 0.00,
            'date': m_line_date,
        })


StockMoveLine._action_done = _action_done2

"""
Stock picking methods
"""


def action_done(self):
    """Changes picking state to done by processing the Stock Moves of the Picking

    Normally that happens when the button "Done" is pressed on a Picking view.
    @return: True
    """
    self._check_company()
    todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
    # Check if there are ops not linked to moves yet
    for pick in self:
        if pick.owner_id:
            pick.move_lines.write({'restrict_partner_id': pick.owner_id.id})
            pick.move_line_ids.write({'owner_id': pick.owner_id.id})
        for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
            # Search move with this product
            moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
            moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
            if moves:
                ops.move_id = moves[0].id
            else:
                new_move = self.env['stock.move'].create({
                    'name': _('New Move:') + ops.product_id.display_name,
                    'product_id': ops.product_id.id,
                    'product_uom_qty': ops.qty_done,
                    'product_uom': ops.product_uom_id.id,
                    'description_picking': ops.description_picking,
                    'location_id': pick.location_id.id,
                    'location_dest_id': pick.location_dest_id.id,
                    'picking_id': pick.id,
                    'picking_type_id': pick.picking_type_id.id,
                    'restrict_partner_id': pick.owner_id.id,
                    'company_id': pick.company_id.id,
                })
                ops.move_id = new_move.id
                new_move = new_move._action_confirm()
                todo_moves |= new_move
        if not pick.date_done:
            pick.date_done = fields.Datetime.now()
    todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
    # self.write({'date_done': fields.Datetime.now()})
    self._send_confirmation_email()
    return True


Picking.action_done = action_done
