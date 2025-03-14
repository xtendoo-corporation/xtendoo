#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for eBay sites.
"""
import json
import ast
import time
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.ebay_ept.ebaysdk.trading import Connection as trading

FLAG_MAPPING = {
    "GF": "fr",
    "BV": "no",
    "BQ": "nl",
    "GP": "fr",
    "HM": "au",
    "YT": "fr",
    "RE": "fr",
    "MF": "fr",
    "UM": "us",
}
EBAY_SITE_POLICY = 'ebay.site.policy.ept'


class EbayInstanceEpt(models.Model):
    """
    Describes eBay Instance Details
    """
    _name = "ebay.instance.ept"
    _description = "eBay Instance"

    name = fields.Char(size=120, string='Site Name', required=True)
    seller_id = fields.Many2one('ebay.seller.ept', string='eBay sellers')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    fiscal_position_id = fields.Many2one('account.fiscal.position',
                                         string='Fiscal Position')  # Added by Tushal Nimavat on 23/06/2022
    lang_id = fields.Many2one('res.lang', string='Language')
    auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Auto Workflow')
    country_id = fields.Many2one("res.country", "Country")
    country_flag = fields.Char(
        compute="_compute_country_flag", string="Flag", help="Url of static flag image")
    post_code = fields.Char('Postal Code', size=64, help="Enter the Postal Code for Item Location")
    auto_update_product = fields.Boolean("Auto Update Product?")
    site_id = fields.Many2one('ebay.site.details', 'Site')
    order_status = fields.Selection([
        ('Active', 'Active'), ('All', 'All'), ('CancelPending', 'CancelPending'),
        ('Completed', 'Completed'), ('Inactive', 'Inactive'), ('Shipped', 'Shipped')
    ], default='Completed', string='Import Order Status', required=True)
    last_ebay_catalog_import_date = fields.Datetime('Last Catalog Import Time', help="Product was last Imported On")
    last_inventory_export_date = fields.Datetime(
        'Last eBay Inventory Export Time', help="Product Stock last Updated On ")
    is_primary_shipping_address = fields.Boolean('ShipToRegistrationCountry', default=False)
    sessionID = fields.Char('SessionID')
    allow_out_of_stock_product = fields.Boolean(
        string="Allow out of stock ?",
        help="When the quantity of your Good 'Til Cancelled listing reaches zero, "
             "the listing remains active but is hidden from search until you increase the quantity."
             " You may also qualify for certain fee credits",
        default=True, readonly=True)
    product_url = fields.Char(string="Product Site URL")
    item_location_country = fields.Many2one(
        "res.country", "Item Location", help="Select the country for the Item Location.")
    item_location_name = fields.Char(
        string="Item Location(City, State) Name", help="Item Location(City, State) name.")
    # Account Field
    ebay_property_account_payable_id = fields.Many2one(
        'account.account', string="eBay Account Payable",
        help='This account will be used instead of the default one '
             'as the payable account for the current partner')
    ebay_property_account_receivable_id = fields.Many2one(
        'account.account', string="eBay Account Receivable",
        help='This account will be used instead of the default one '
             'as the receivable account for the current partner')
    sale_order_count = fields.Integer(compute='_compute_orders_invoices_count', string="Total Sales Orders")
    invoice_count = fields.Integer(compute='_compute_orders_invoices_count', string="Total Invoices")
    delivery_order_count = fields.Integer(compute='_compute_orders_invoices_count', string="Total Delivery Orders")
    ebay_stock_field = fields.Selection([
        ('free_qty', 'On Hand Quantity'), ('virtual_available', 'Forecast Quantity')
    ], string="eBay Stock Type", default='free_qty', help="eBay Stock Type")
    active = fields.Boolean(string="Active", default=True)
    ebay_stock_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        'ebay_instance_export_stock_warehouse_rel',
        'stock_warehouse_id',
        'instance_id',
        string="Export Stock Warehouse",
        help="eBay export stock Warehouse")
    color = fields.Integer(string='Color Index')
    ebay_order_data = fields.Text(compute="_compute_kanban_ebay_order_data")
    ebay_listing_duration = fields.Selection([
        ('Days_3', '3 Days'),
        ('Days_5', '5 Days'),
        ('Days_7', '7 Days'),
        ('Days_10', '10 Days'),
        ('Days_30', '30 Days (only for fixed price)'),
        ('GTC', 'Good \'Til Cancelled (only for fixed price)')],
        string='Duration', default='Days_7')
    # eBay Seller Policy
    ebay_seller_payment_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="Seller Payment Policy", help="Options for Seller Payment Policy")
    ebay_seller_return_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="eBay Seller Return Policy", help="Options for Seller Return Policy")
    ebay_seller_shipping_policy_id = fields.Many2one(
        EBAY_SITE_POLICY, string="Seller Shipping Policy", help="Options for Seller Shipping Policy")

    def _compute_country_flag(self):
        """This method is display flag in a instance country codewise"""
        for instance in self:
            code = FLAG_MAPPING.get(instance.country_id and instance.country_id.code or " ",
                                    instance.country_id.code and instance.country_id.code.lower() or "")
            self.country_flag = "/base/static/img/country_flags/%s.png" % code

    def _compute_orders_invoices_count(self):
        """
        Count Orders and Invoices via sql query from database
        because of increase speed of Dashboard.
        :return:
        """
        for instance in self:
            qry = "SELECT count(*) AS row_count FROM sale_order WHERE state not in ('draft','sent','cancel') and ebay_instance_id = %s"
            self._cr.execute(qry, (instance.id,))
            instance.sale_order_count = self._cr.fetchall()[0][0]

            qry = "SELECT count(*) AS row_count FROM account_move WHERE ebay_instance_id = %s and state='posted' and move_type='out_invoice'"
            self._cr.execute(qry, (instance.id,))
            instance.invoice_count = self._cr.fetchall()[0][0]

            qry = "SELECT count(*) AS row_count FROM stock_picking WHERE ebay_instance_id = %s"
            self._cr.execute(qry, (instance.id,))
            instance.delivery_order_count = self._cr.fetchall()[0][0]

    def _compute_kanban_ebay_order_data(self):
        if not self._context.get('sort'):
            context = dict(self.env.context)
            context.update({'sort': 'week'})
            self.env.context = context
        for record in self:
            # Prepare values for Graph
            values = record.get_graph_data(record)
            data_type, comparison_value = record.get_compare_data(record)
            # Total sales
            total_sales = round(sum([key['y'] for key in values]), 2)
            # Order count query
            order_data = record.get_total_orders(record)
            # Product count query
            product_data = record.get_total_products(record)
            # Order shipped count query
            order_shipped = record.get_shipped_orders(record)
            # Customer count query
            customer_data = record.get_customers(record)
            # refund count query
            refund_data = record.get_refund(record)
            record.ebay_order_data = json.dumps({
                "values": values,
                "title": "",
                "key": "Order: Untaxed amount",
                "area": True,
                "color": "#875A7B",
                "is_sample_data": False,
                "total_sales": total_sales,
                "order_data": order_data,
                "product_date": product_data,
                "customer_data": customer_data,
                "order_shipped": order_shipped,
                "refund_data": refund_data,
                "refund_count": refund_data.get('refund_count'),
                "sort_on": self._context.get('sort'),
                "currency_symbol": record.pricelist_id.currency_id.symbol or '',
                "graph_sale_percentage": {'type': data_type, 'value': comparison_value}
            })

    def get_graph_data(self, record):
        """
        Use: To get the details of shopify sale orders and total amount month wise or year wise to prepare the graph
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: shopify sale order date or month and sum of sale orders amount of current instance
        """

        def get_current_week_date(record):
            qry = """SELECT to_char(date(d.day),'DAY'), t.amount_untaxed as sum
                                FROM  (
                                   SELECT day
                                   FROM generate_series(date(date_trunc('week', (current_date)))
                                    , date(date_trunc('week', (current_date)) + interval '6 days')
                                    , interval  '1 day') day
                                   ) d
                                LEFT   JOIN 
                                (SELECT date(date_order)::date AS day, sum(amount_untaxed) as amount_untaxed
                                   FROM   sale_order
                                   WHERE  date(date_order) >= (select date_trunc('week', date(current_date)))
                                   AND    date(date_order) <= (select date_trunc('week', date(current_date)) 
                                   + interval '6 days')
                                   AND ebay_instance_id=%s and state in ('sale','done')
                                   GROUP  BY 1
                                   ) t USING (day)
                                ORDER  BY day"""
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def graph_of_current_month(record):
            qry = """select EXTRACT(DAY from date(date_day)) :: integer,sum(amount_untaxed) from (
                        SELECT 
                          day::date as date_day,
                          0 as amount_untaxed
                        FROM generate_series(date(date_trunc('month', (current_date)))
                            , date(date_trunc('month', (current_date)) + interval '1 MONTH - 1 day')
                            , interval  '1 day') day
                        union all
                        SELECT date(date_order)::date AS date_day,
                        sum(amount_untaxed) as amount_untaxed
                          FROM   sale_order
                        WHERE  date(date_order) >= (select date_trunc('month', date(current_date)))
                        AND date(date_order)::date <= (select date_trunc('month', date(current_date)) 
                        + '1 MONTH - 1 day')
                        and ebay_instance_id = %s and state in ('sale','done')
                        group by 1
                        )foo 
                        GROUP  BY 1
                        ORDER  BY 1"""
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def graph_of_current_year(record):
            qry = """select TRIM(TO_CHAR(DATE_TRUNC('month',month),'MONTH')),sum(amount_untaxed) from
                                (SELECT DATE_TRUNC('month',date(day)) as month,
                                  0 as amount_untaxed
                                FROM generate_series(date(date_trunc('year', (current_date)))
                                , date(date_trunc('year', (current_date)) + interval '1 YEAR - 1 day')
                                , interval  '1 MONTH') day
                                union all
                                SELECT DATE_TRUNC('month',date(date_order)) as month,
                                sum(amount_untaxed) as amount_untaxed
                                  FROM   sale_order
                                WHERE  date(date_order) >= (select date_trunc('year', date(current_date))) AND 
                                date(date_order)::date <= (select date_trunc('year', date(current_date)) 
                                + '1 YEAR - 1 day')
                                and ebay_instance_id = %s and state in ('sale','done')
                                group by DATE_TRUNC('month',date(date_order))
                                order by month
                                )foo 
                                GROUP  BY foo.month
                                order by foo.month"""
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def graph_of_all_time(record):
            qry = """select TRIM(TO_CHAR(DATE_TRUNC('month',date_order),'YYYY-MM')),sum(amount_untaxed)
                                from sale_order where ebay_instance_id = %s and state in ('sale','done')
                                group by DATE_TRUNC('month',date_order) 
                                order by DATE_TRUNC('month',date_order)"""
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        # Prepare values for Graph
        values = []
        if self._context.get('sort') == 'week':
            result = get_current_week_date(record)
        elif self._context.get('sort') == "month":
            result = graph_of_current_month(record)
        elif self._context.get('sort') == "year":
            result = graph_of_current_year(record)
        else:
            result = graph_of_all_time(record)
        if result:
            for data in result:
                values.append({"x": ("{}".format(data.get(list(data.keys())[0]))), "y": data.get('sum') or 0.0})
        return values

    def get_compare_data(self, record):
        """
        :param record: Shopify instance
        :return: Comparison ratio of orders (weekly,monthly and yearly based on selection)
        """
        data_type = False
        total_percentage = 0.0

        def get_compared_week_data(record):
            current_total = 0.0
            previous_total = 0.0
            day_of_week = date.weekday(date.today())
            qry = """select sum(amount_untaxed) as current_week from sale_order
                                where date(date_order) >= (select date_trunc('week', date(current_date))) and
                                ebay_instance_id=%s and state in ('sale','done')"""
            self._cr.execute(qry, (record.id,))
            current_week_data = self._cr.dictfetchone()
            if current_week_data:
                current_total = current_week_data.get('current_week') if current_week_data.get('current_week') else 0
            # Previous week data
            qry = """select sum(amount_untaxed) as previous_week from sale_order
                            where date(date_order) between (select date_trunc('week', current_date) - interval '7 day') 
                            and (select date_trunc('week', (select date_trunc('week', current_date) - interval '7
                            day')) + interval '%s day')
                            and ebay_instance_id=%s and state in ('sale','done')
                            """
            self._cr.execute(qry, (day_of_week, record.id,))
            previous_week_data = self._cr.dictfetchone()
            if previous_week_data:
                previous_total = previous_week_data.get('previous_week') if previous_week_data.get(
                    'previous_week') else 0
            return current_total, previous_total

        def get_compared_month_data(record):
            current_total = 0.0
            previous_total = 0.0
            day_of_month = date.today().day - 1
            qry = """select sum(amount_untaxed) as current_month from sale_order
                                where date(date_order) >= (select date_trunc('month', date(current_date)))
                                and ebay_instance_id=%s and state in ('sale','done')"""
            self._cr.execute(qry, (record.id,))
            current_data = self._cr.dictfetchone()
            if current_data:
                current_total = current_data.get('current_month') if current_data.get('current_month') else 0
            # Previous week data
            qry = """select sum(amount_untaxed) as previous_month from sale_order where date(date_order)
                            between (select date_trunc('month', current_date) - interval '1 month') and
                            (select date_trunc('month', (select date_trunc('month', current_date) - interval
                            '1 month')) + interval '%s days')
                            and ebay_instance_id=%s and state in ('sale','done')
                            """
            self._cr.execute(qry, (day_of_month, record.id,))
            previous_data = self._cr.dictfetchone()
            if previous_data:
                previous_total = previous_data.get('previous_month') if previous_data.get('previous_month') else 0
            return current_total, previous_total

        def get_compared_year_data(record):
            current_total = 0.0
            previous_total = 0.0
            year_begin = date.today().replace(month=1, day=1)
            year_end = date.today()
            delta = (year_end - year_begin).days - 1
            qry = """select sum(amount_untaxed) as current_year from sale_order
                                where date(date_order) >= (select date_trunc('year', date(current_date)))
                                and ebay_instance_id=%s and state in ('sale','done')"""
            self._cr.execute(qry, (record.id,))
            current_data = self._cr.dictfetchone()
            if current_data:
                current_total = current_data.get('current_year') if current_data.get('current_year') else 0
            # Previous week data
            qry = """select sum(amount_untaxed) as previous_year from sale_order where date(date_order)
                            between (select date_trunc('year', date(current_date) - interval '1 year')) and 
                            (select date_trunc('year', date(current_date) - interval '1 year') + interval '%s days') 
                            and ebay_instance_id=%s and state in ('sale','done')
                            """
            self._cr.execute(qry, (delta, record.id,))
            previous_data = self._cr.dictfetchone()
            if previous_data:
                previous_total = previous_data.get('previous_year') if previous_data.get('previous_year') else 0
            return current_total, previous_total

        if self._context.get('sort') == 'week':
            current_total, previous_total = get_compared_week_data(record)
        elif self._context.get('sort') == "month":
            current_total, previous_total = get_compared_month_data(record)
        elif self._context.get('sort') == "year":
            current_total, previous_total = get_compared_year_data(record)
        else:
            current_total, previous_total = 0.0, 0.0
        if current_total > 0.0:
            if current_total >= previous_total:
                data_type = 'positive'
                total_percentage = (current_total - previous_total) * 100 / current_total
            if previous_total > current_total:
                data_type = 'negative'
                total_percentage = (previous_total - current_total) * 100 / current_total
        return data_type, round(total_percentage, 2)

    def get_total_orders(self, record):
        """
        Use: To get the list of shopify sale orders month wise or year wise
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: total number of shopify sale orders ids and action for sale orders of current instance
        """

        def orders_of_current_week(record):
            qry = """select id from sale_order where date(date_order)
                                >= (select date_trunc('week', date(current_date)))
                                and ebay_instance_id= %s and state in ('sale','done')
                                order by date(date_order)
                        """
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def orders_of_current_month(record):
            qry = """select id from sale_order where date(date_order) >=
                                (select date_trunc('month', date(current_date)))
                                and ebay_instance_id= %s and state in ('sale','done')
                                order by date(date_order)
                        """
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def orders_of_current_year(record):
            qry = """select id from sale_order where date(date_order) >=
                                (select date_trunc('year', date(current_date))) 
                                and ebay_instance_id= %s and state in ('sale','done')
                                order by date(date_order)"""
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def orders_of_all_time(record):
            qry = """select id from sale_order where ebay_instance_id = %s and state in ('sale','done')"""
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        order_data = {}
        order_ids = []
        if self._context.get('sort') == "week":
            result = orders_of_current_week(record)
        elif self._context.get('sort') == "month":
            result = orders_of_current_month(record)
        elif self._context.get('sort') == "year":
            result = orders_of_current_year(record)
        else:
            result = orders_of_all_time(record)
        if result:
            for data in result:
                order_ids.append(data.get('id'))
        view = self.env.ref('ebay_ept.action_ebay_sales_orders').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def get_shipped_orders(self, record):
        """
        Use: To get the list of eBay shipped orders month wise or year wise
        :return: total number of eBay shipped orders ids and action for shipped orders of current instance
        """
        shipped_query = """select so.id from stock_picking sp
                             inner join sale_order so on so.procurement_group_id=sp.group_id inner 
                             join stock_location on stock_location.id=sp.location_dest_id and stock_location.usage='customer' 
                             where sp.updated_in_ebay = True and sp.state != 'cancel' and 
                             so.ebay_instance_id=%s"""

        def shipped_order_of_current_week(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('week', date(current_date)))"
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def shipped_order_of_current_month(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('month', date(current_date)))"
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def shipped_order_of_current_year(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('year', date(current_date)))"
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def shipped_order_of_all_time(shipped_query):
            self._cr.execute(shipped_query, (record.id,))
            return self._cr.dictfetchall()

        order_data = {}
        order_ids = []
        if self._context.get('sort') == "week":
            result = shipped_order_of_current_week(shipped_query)
        elif self._context.get('sort') == "month":
            result = shipped_order_of_current_month(shipped_query)
        elif self._context.get('sort') == "year":
            result = shipped_order_of_current_year(shipped_query)
        else:
            result = shipped_order_of_all_time(shipped_query)
        if result:
            for data in result:
                order_ids.append(data.get('id'))
        view = self.env.ref('ebay_ept.action_ebay_sales_orders').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def get_total_products(self, record):
        """
        Use: To get the list of products exported from eBay instance
        :return: total number of eBay products ids and action for products
        """
        product_data = {}
        qry = """select count(id) as total_count from ebay_product_template_ept where
                        exported_in_ebay = True and instance_id = %s"""
        self._cr.execute(qry, (record.id,))
        result = self._cr.dictfetchall()
        if result:
            total_count = result[0].get('total_count')
        view = self.env.ref('ebay_ept.action_ebay_product_exported_ept').sudo().read()[0]
        action = record.prepare_action(view,
                                       [('exported_in_ebay', '=', True), ('instance_id', '=', record.id)])
        product_data.update({'product_count': total_count, 'product_action': action})
        return product_data

    def get_customers(self, record):
        """
        Use: To get the list of customers with eBay instance for current eBay instance
        :return: total number of customer ids and action for customers
        """
        customer_data = {}
        self._cr.execute("""select id from res_partner where ebay_user_id IS NOT NULL""")
        result = self._cr.dictfetchall()
        ebay_customer_ids = [data.get('id') for data in result]

        view = self.env.ref('base.action_partner_form').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', ebay_customer_ids), ('active', 'in', [True, False])])
        customer_data.update({'customer_count': len(ebay_customer_ids), 'customer_action': action})
        return customer_data

    def get_refund(self, record):
        """
        Use: To get the list of refund orders of eBay instance for current eBay instance
        :return: total number of refund order ids and action for customers
        """
        refund_data = {}
        refund_ids = []
        refund_query = """select id from account_move where ebay_instance_id=%s and
                            move_type='out_refund'"""

        def refund_of_current_week(refund_query):
            qry = refund_query + " and date(invoice_date) >= (select date_trunc('week', date(current_date)))"
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def refund_of_current_month(refund_query):
            qry = refund_query + " and date(invoice_date) >= (select date_trunc('month', date(current_date)))"
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def refund_of_current_year(refund_query):
            qry = refund_query + " and date(invoice_date) >= (select date_trunc('year', date(current_date)))"
            self._cr.execute(qry, (record.id,))
            return self._cr.dictfetchall()

        def refund_of_all_time(refund_query):
            self._cr.execute(refund_query, (record.id,))
            return self._cr.dictfetchall()

        refund_data = {}
        refund_ids = []
        if self._context.get('sort') == "week":
            result = refund_of_current_week(refund_query)
        elif self._context.get('sort') == "month":
            result = refund_of_current_month(refund_query)
        elif self._context.get('sort') == "year":
            result = refund_of_current_year(refund_query)
        else:
            result = refund_of_all_time(refund_query)
        if result:
            for data in result:
                refund_ids.append(data.get('id'))
        view = self.env.ref('ebay_ept.action_refund_ebay_invoices').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', refund_ids)])
        refund_data.update({'refund_count': len(refund_ids), 'refund_action': action})
        return refund_data

    def prepare_action(self, view, domain):
        """
        Use: To prepare action dictionary
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: action details
        """
        action = {
            'name': view.get('name'),
            'type': view.get('type'),
            'domain': domain,
            'view_mode': view.get('view_mode'),
            'view_id': view.get('view_id')[0] if view.get('view_id') else False,
            'views': view.get('views'),
            'res_model': view.get('res_model'),
            'target': view.get('target'),
        }

        def change_tree_view_name(view):
            if view[1] == 'tree':
                return (view[0], 'list')
            return view

        action['views'] = list(map(change_tree_view_name, action['views']))

        # if 'tree' in action['views'][0]:
        #     action['views'][0] = (action['view_id'], 'list')
        return action

    @api.model
    def perform_operation(self, record_id):
        """
        Use: To prepare shopify operation action
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: shopify operation action details
        """
        view = self.env.ref('ebay_ept.action_wizard_ebay_instance_import_export_operations').sudo().read()[0]
        action = self.prepare_action(view, [])
        instance = self.browse(record_id)
        action.update({'context': {'default_seller_id': instance.seller_id.id, 'default_instance_ids': instance.ids}})
        return action

    @api.model
    def open_report(self, record_id):
        """
        Use: To prepare eBay report action
        :return: eBay report action details
        """
        view = self.env.ref('sale.action_order_report_all').sudo().read()[0]
        action = self.prepare_action(view, [('ebay_instance_id', '=', record_id)])
        # action.update({'context': {'search_default_shopify_instances': record_id, 'search_default_Sales': 1,
        #                            'search_default_filter_date': 1}})
        return action

    @api.model
    def open_logs(self, record_id):
        """
        Use: To prepare eBay logs action
        :return: eBay logs action details
        """
        view = self.env.ref('ebay_ept.action_ebay_process_job_log_lines_ept').sudo().read()[0]
        return self.prepare_action(view, [('ebay_instance_id', '=', record_id)])

    def write(self, vals):
        """
        Set OutOfStockControlPreference through eBay API.
        :param vals: values to be written
        :return: eBay Instance object
        """
        check = vals.get('allow_out_of_stock_product')
        auth_token = self.seller_id.auth_token
        if ('allow_out_of_stock_product' in vals) and auth_token and len(auth_token) > 1:
            trading_api = self.get_trading_api_object()
            if check:
                dict_temp = {'OutOfStockControlPreference': 'true'}
            else:
                dict_temp = {'OutOfStockControlPreference': 'false'}
            trading_api.execute('SetUserPreferences', dict_temp)
        res = super(EbayInstanceEpt, self).write(vals)
        return res

    @staticmethod
    def odoo_format_date(src_date):
        """
        Fprmat given date into Odoo format.
        :param src_date: date to be formatted
        :return: formatted date
        """
        src_date = src_date[:19]
        src_date = time.strptime(src_date, "%Y-%m-%dT%H:%M:%S")
        src_date = time.strftime("%Y-%m-%d %H:%M:%S", src_date)
        return src_date

    def ebay_action_archive_unarchive(self):
        """
        Set instance active or inactive.
        """
        if self.active:
            self.active = False
        else:
            self.active = True

    @api.model
    def get_trading_api_object(self):
        """
        Get Trading API object of eBay.
        :return: api response
        """
        appid = self.seller_id.app_id
        devid = self.seller_id.dev_id
        certid = self.seller_id.cert_id
        token = self.seller_id.auth_token
        if self.seller_id.environment == 'is_sandbox':
            domain = 'api.sandbox.ebay.com'
        else:
            domain = 'api.ebay.com'
        site_id = self.site_id.site_id or False
        if site_id:
            trading_apis = trading(
                config_file=False, appid=appid, devid=devid, certid=certid, token=token,
                domain=domain, siteid=self.site_id.site_id, timeout=500)
        else:
            trading_apis = trading(
                config_file=False, appid=appid, devid=devid, certid=certid, token=token,
                domain=domain, timeout=500)
        return trading_apis

    def check_connection(self):
        """
        Check eBay connection with Odoo
        """
        trading_api = self.get_trading_api_object()
        para = {}
        try:
            trading_api.execute('GetUser', para)
        except Exception as error:
            raise UserError(error)
        raise UserError(_('Service working properly'))

    def ebay_credential_update(self):
        """
        Open view to update ebay credentials
        """
        ebay_credential_view = self.env.ref('ebay_ept.ebay_credential_upadte_wizard', False)
        result = True
        if ebay_credential_view:
            result = {
                'name': 'eBay Credential', 'view_type': 'form', 'view_mode': 'form',
                'res_model': 'ebay.credential', 'type': 'ir.actions.act_window',
                'view_id': ebay_credential_view.id, 'target': 'new'}
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Creates eBay instance details
        :param vals_list: values to create eBay details
        :return: ebay instance object
        """
        instance_ids = super(EbayInstanceEpt, self).create(vals_list)
        for instance in instance_ids:
            try:
                if instance:
                    trading_api = instance.get_trading_api_object()
                    para = {'OutOfStockControlPreference': 'true'}
                    trading_api.execute('SetUserPreferences', para)
                    trading_api.response.dict()
            except Exception as error:
                instance.unlink()
                raise UserError(error)
        return instance_ids

    def _get_action(self, action):
        """
        Get eBay actions by given action parameter
        :params action: action to be retrieved
        :Returns : Specific action object
        """
        if not self.active:
            raise UserError(_("Instance %s is not active...", self.name))
        action = self.env.ref(action) or False
        result = action.read()[0] or {}
        domain = []
        if result.get('domain') and ast.literal_eval(result.get('domain')):
            domain = ast.literal_eval(result.get('domain'))
        if action.res_model == 'res.config.settings':
            result['context'] = {'instance_id': self.id}
        if action.res_model == 'ebay.process.import.export':
            result['context'] = {'instance_ids': self.ids}
        if action.res_model in ['sale.order', 'stock.picking', 'account.move']:
            domain.append(('ebay_instance_id', '=', self.id))
            result['domain'] = domain
        return result

    def get_action_perform_oprations(self):
        """
        Get action for eBay operations
        """
        return self._get_action('ebay_ept.action_wizard_ebay_import_processes_in_ebay_ept')

    def get_action_ebay_sales_orders(self):
        """
        Get action for eBay Sale orders
        """
        return self._get_action('ebay_ept.action_ebay_sales_orders')

    def get_action_delivery_orders(self):
        """
        Get action for eBay delivery orders
        """
        return self._get_action('ebay_ept.action_picking_view_ept')

    def get_action_invoice_ebay_invoices(self):
        """
        Get action for eBay invoices
        """
        return self._get_action('ebay_ept.action_invoice_ebay_invoices')
