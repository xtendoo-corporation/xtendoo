import json
import odoo
from odoo import http
from odoo.http import request

class TableBooking(http.Controller):

    #xtd
    @http.route(['/table/<model("restaurant.table"):table>/test'], auth="public", website=True)
    def table_booking_test(self, table=None, **post):
        values = {}
        order = None
        old_order_resume = None
        order_resume = request.env['table.order'].sudo().search(
            [('state', '=', 'draft'), ('active', '=', False), ('is_table_order', '=', True),
             ('table_id', '=', table.id)], limit=1)
        old_order_resume = request.env['table.order'].sudo().search(
            [('state', '=', 'draft'), ('active', '=', True), ('is_table_order', '=', True),
             ('table_id', '=', table.id)], limit=1)
        if order_resume:
            request.session['sale_table_last_order_id'] = order_resume.id
            order = order_resume
        else:
            request.session['sale_table_last_order_id'] = None
        products = request.env['product.template'].sudo().search([('is_table_order', '=', True)])
        cate_ids = None
        if products:
            cate_ids = products.mapped('pos_categ_id')
        values.update({
            'products': products or False,
            'table_obj': table,
            'order': order or None,
            'old_order_resume': old_order_resume or None,
            'ol_resume': None,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'cate_ids': cate_ids or None,
            'active_cat_id': cate_ids[0] if cate_ids else None
        })
        return request.render("qrcode_table.test_table", values)
    #xtd
    @http.route(['/table/<model("restaurant.table"):table>'], auth="public", website=True)
    def table_booking(self, table=None, **post):
        values = {}
        order = None
        old_order_resume = None
        order_resume = request.env['table.order'].sudo().search([('state', '=', 'draft'), ('active', '=', False), ('is_table_order', '=', True), ('table_id', '=', table.id)], limit=1)
        old_order_resume = request.env['table.order'].sudo().search([('state', '=', 'draft'), ('active', '=', True), ('is_table_order', '=', True), ('table_id', '=', table.id)], limit=1)
        if order_resume:
            request.session['sale_table_last_order_id'] = order_resume.id
            order = order_resume
        else:
            request.session['sale_table_last_order_id'] = None
        products = request.env['product.template'].sudo().search([('is_table_order', '=', True)])
        cate_ids = None
        if products:
            cate_ids = products.mapped('pos_categ_id')
        values.update({
            'products': products or False,
            'table_obj': table,
            'order': order or None,
            'old_order_resume': old_order_resume or None,
            'ol_resume': None,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'cate_ids': cate_ids or None,
            'active_cat_id': cate_ids[0] if cate_ids else None
            })
        return request.render("qrcode_table.tablebook_temp", values)

    @http.route(['/table/resume/<model("table.order"):torder>'], auth="public", website=True)
    def ResumeOrder(self, torder=None, **post):
        values = {}
        order = None
        table = None
        if torder:
            request.session['sale_table_last_order_id'] = torder.id
            order = torder.sudo() if torder.sudo().state == 'draft' else None
            if not order:
                request.session['sale_table_last_order_id'] = None
            table = torder.table_id if torder.table_id else None
        else:
            request.session['sale_table_last_order_id'] = None
        products = request.env['product.template'].sudo().search([('is_table_order', '=', True)])
        cate_ids = None
        if products:
            cate_ids = products.mapped('pos_categ_id')
        values.update({
            'products': products or False,
            'table_obj': table,
            'order': order or None,
            'old_order_resume': order or None,
            'ol_resume': order or None,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'cate_ids': cate_ids or None,
            'active_cat_id': cate_ids[0] if cate_ids else None
            })
        return request.render("qrcode_table.tablebook_temp", values)

    @http.route(['/table/cart/update_json'], type='json', auth="public", csrf=False)
    def table_cart_update_json(self, product_id, table_id, add_qty=1, **kw):
        merge = True
        session_order = None
        if request.session.get('sale_table_last_order_id'):
            session_order = request.env['table.order'].sudo().search([
                ('id', '=', request.session.get('sale_table_last_order_id')),
                ('active', '=', False)])
            if not session_order:
                session_order = request.env['table.order'].sudo().search([
                    ('id', '=', request.session.get('sale_table_last_order_id'))])
            if session_order:
                line = None
                if session_order.lines:
                    line = session_order.lines.filtered(
                        lambda x: x.product_id.sudo().id == int(product_id) and x.state == 'draft')
                if line and merge:
                    line.write({'qty': line.qty + 1, 'state': 'draft'})
                    line._onchange_product_id()
                else:
                    product_id = request.env['product.product'].sudo().search([
                        ('id', '=', product_id)])
                    line_id = request.env['table.order.line'].sudo().create({
                        'product_id': product_id.id,
                        'qty': add_qty,
                        'price_unit': product_id.lst_price,
                        'state': 'draft',
                        'price_subtotal':0,
                        'price_subtotal_incl':0,
                        'note': kw.get('note'),
                    })
                    session_order.lines = [(4, line_id.id)]
                    line_id._onchange_product_id()
                session_order._onchange_amount_all()
        else:
            table = request.env['restaurant.table'].sudo().search([('id', '=', int(table_id))])
            product_id = request.env['product.product'].sudo().search([('id', '=', product_id)])
            pos_session_id = request.env['pos.session'].sudo().search([
                ('state', '=', 'opened')], limit=1)
            if not pos_session_id:
                return {'error': 'POS Session is not running Please contact to Manager or Administrator.'}
            pricelist_id = pos_session_id.config_id.pricelist_id
            if table:
                lines = [(0, 0, {
                    'product_id': product_id.id,
                    'qty': add_qty,
                    'price_unit': product_id.lst_price,
                    'state': 'draft',
                    'price_subtotal':0,
                    'price_subtotal_incl':0,
                    'note': kw.get('note')})]
                new_order = request.env['table.order'].sudo().create({
                    'table_id': table.id,
                    'is_table_order': True,
                    'active': False,
                    'amount_tax':0,
                    'amount_total':0,
                    'pricelist_id': pricelist_id.id,
                    'lines': lines })
                if new_order and new_order.lines:
                    for line in new_order.lines:
                        line._onchange_product_id()
                    new_order._onchange_amount_all()
                request.session['sale_table_last_order_id'] = new_order.id

        order = request.env['table.order'].sudo().search([
            ('id', '=', request.session.get('sale_table_last_order_id')), ('active', '=', False)])
        if not order:
            order = request.env['table.order'].sudo().search([
                ('id', '=', request.session.get('sale_table_last_order_id'))])
        value = {}
        value['qrcode_table.table_cart_shop'] = request.env['ir.ui.view']._render_template(
            "qrcode_table.table_cart_shop", {'order': order})
        return value

    @http.route(['/table/remove/order_line_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def remove_order_line_table(self, line_id):
        if line_id:
            order_line_id = request.env['table.order.line'].sudo().search([('id', '=', line_id)])
            if order_line_id:
                order_line_id.sudo().unlink()
                if request.session.get('sale_table_last_order_id'):
                    order = None
                    order = request.env['table.order'].sudo().search([('id', '=', request.session.get('sale_table_last_order_id')), ('active', '=', False)], limit=1)
                    if not order:
                        order = request.env['table.order'].sudo().search([('id', '=', request.session.get('sale_table_last_order_id'))], limit=1)
                    if order:
                        order._onchange_amount_all()
                        value = {}
                        value['table_cart_lines'] = request.env['ir.ui.view']._render_template("qrcode_table.table_cart_shop", {
                            'order': order,
                        })
                        return value

    @http.route(['/confirm/table/order'], auth="public", website=True)
    def confirm_table_order(self, **post):
        token = None
        order_res = None
        values = {}
        if request.session.get('sale_table_last_order_id'):
            order = None
            order = request.env['table.order'].sudo().search([('id', '=', request.session.get('sale_table_last_order_id')), ('active', '=', False)])
            if not order:
                order = request.env['table.order'].sudo().search([('id', '=', request.session.get('sale_table_last_order_id'))])
            if order:
                order.active = True
                order_res = order
                if order.token:
                    token = order.token
                else:
                    order.token = request.env['ir.sequence'].sudo().next_by_code('table.order')
                if order:
                    for line in order.lines:
                        if line.state == 'draft':
                            line.state = 'confirm'
                token = order.token
                notifications = []
                table_order_message = order.table_id.name + " Have new order."
                user_ids = request.env['pos.session'].sudo().search([('state', '=', 'opened')]).mapped('user_id')
                for user_id in user_ids.sudo():
                    vals = {
                        'user_id': user_id.id,
                        'table_order_message': table_order_message,
                    }
                    notifications.append([user_id.partner_id, 'table.order', user_id.id])
                    request.env['bus.bus'].sudo()._sendmany(notifications)
                values.update({
                        'token': token,
                        'order': order_res
                        })
        return request.render("qrcode_table.confirm_order_temp", values)

    def get_attribute_value_ids(self, pricelist, product):
        """ list of selectable attributes of a product

        :return: list of product variant description
           (variant id, [visible attribute ids], variant price, variant sale price)
        """
        # product attributes with at least two choices
        if not pricelist:
            PosConfig = request.env['pos.config'].sudo().search([('active', '=', True)], limit=1)
            pricelist = PosConfig.pricelist_id
        quantity = product._context.get('quantity') or 1
        product = product.with_context(quantity=quantity)

        visible_attrs_ids = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id').ids
        to_currency = pricelist.currency_id
        attribute_value_ids = []
        for variant in product.product_variant_ids:
            if to_currency != product.currency_id:
                price = variant.currency_id.compute(variant.lst_price, to_currency) / quantity
            else:
                price = variant.lst_price / quantity
            visible_attribute_ids = [v.id for v in variant.product_template_attribute_value_ids if v.attribute_id.id in visible_attrs_ids]
            attribute_value_ids.append([variant.id, visible_attribute_ids, price, variant.list_price / quantity])
        return attribute_value_ids

    @http.route(['/table/get/note'], type='json', auth="public", csrf=False)
    def table_get_note_json(self, order_line_id, **kw):
        values = {}
        if order_line_id:
            order_line_id = request.env['table.order.line'].browse(order_line_id)
            values.update({'note': order_line_id.note,
                           'order_line_id': order_line_id.id})
        return values

    @http.route(['/table/update/note'], type='json', auth="public", csrf=False)
    def table_update_note_json(self, order_line_id, note='', **kw):
        values = {}
        if order_line_id:
            order_line_id = request.env['table.order.line'].browse(order_line_id)
            order_line_id.note = note
            values.update({'success': True,
                           'order_line_id': order_line_id.id})
        return values

    @http.route(['/qrcode_table/update_json'], type='json', auth="public", website=True, csrf=False)
    def qrcode_table_update_json(self):
        """This route is called when changing quantity from the cart or adding
        a product from the wishlist."""
        order = request.session.get('sale_table_last_order_id')
        if not order:
            return {}
        order = request.env['table.order'].sudo().search([('id', '=', request.session.get('sale_table_last_order_id'))])
        value = {}
        value['qrcode_table.table_cart_lines'] = request.env['ir.ui.view']._render_template("qrcode_table.table_cart_lines", {'order': order})
        return value
