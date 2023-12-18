# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
import requests
import pytz

from odoo import models, fields, api, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.base_import.models.base_import import check_patterns
from odoo.addons.base_import.models.base_import import DATE_PATTERNS
from odoo.addons.base_import.models.base_import import TIME_PATTERNS
from odoo.exceptions import UserError

from .. import woocommerce
from ..wordpress_xmlrpc import base, media
from ..wordpress_xmlrpc.exceptions import InvalidCredentialsError

_logger = logging.getLogger("WooCommerce")
_secondsConverter = {
    'days': lambda interval: interval * 24 * 60 * 60,
    'hours': lambda interval: interval * 60 * 60,
    'weeks': lambda interval: interval * 7 * 24 * 60 * 60,
    'minutes': lambda interval: interval * 60,
}


class WooInstanceEpt(models.Model):
    _name = "woo.instance.ept"
    _description = "WooCommerce Instance"
    _check_company_auto = True

    @api.model
    def _get_default_warehouse(self):
        """
        Sets default warehouse from instance's company.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        stock_warehouse_obj = self.env['stock.warehouse']
        warehouse = stock_warehouse_obj.search([('company_id', '=', self.company_id.id)], limit=1, order='id')
        return warehouse.id if warehouse else False

    @api.model
    def _default_stock_field(self):
        """
        Sets Free qty field as default stock field for exporting the stock.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        stock_field = self.env['ir.model.fields'].search([('model_id.model', '=', 'product.product'),
                                                          ('name', '=', 'free_qty')], limit=1)
        return stock_field.id if stock_field else False

    @api.model
    def _get_default_language(self):
        """
        Sets default language in instance same as user's.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        lang_code = self.env.user.lang
        language = self.env["res.lang"].search([('code', '=', lang_code)])
        return language.id if language else False

    @api.model
    def _default_payment_term(self):
        """
        Sets default payment terms.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        payment_term = self.env.ref("account.account_payment_term_immediate")
        return payment_term.id if payment_term else False

    @api.model
    def _default_order_status(self):
        """
        Return default status of woo order, for importing the particular orders having this status.
        @author: Maulik Barad on Date 11-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_status = self.env.ref('woo_commerce_ept.processing')
        return [(6, 0, [order_status.id])] if order_status else False

    @api.model
    def _default_shipping_product(self):
        """
        Sets default shipping product to set in WooCommerce order.
        @author: Haresh Mori on Date 29-Sep-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        shipping_product = self.env.ref('woo_commerce_ept.product_woo_shipping_ept', False)
        if not shipping_product:
            raise UserError(_("Please upgrade the module and then try to create new instance.\n Maybe the shipping "
                              "product has been deleted, it will be recreated at the time of module upgrade."))
        return shipping_product

    @api.model
    def _default_fee_product(self):
        """
        Gives default discount product to set in imported woo order.
        @author: Maulik Barad on Date 11-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        fee_product = self.env.ref('woo_commerce_ept.product_woo_fees_ept', False)
        if not fee_product:
            raise UserError(_("Please upgrade the module and then try to create new instance.\n Maybe the Fee "
                              "product has been deleted, it will be recreated at the time of module upgrade."))
        return fee_product

    @api.model
    def _default_discount_product(self):
        """
        Gives default discount product to set in imported woo order.
        @author: Maulik Barad on Date 11-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        discount_product = self.env.ref('woo_commerce_ept.product_woo_discount_ept', False)
        if not discount_product:
            raise UserError(_("Please upgrade the module and then try to create new instance.\n Maybe the Discount "
                              "product has been deleted, it will be recreated at the time of module upgrade."))
        return discount_product

    @api.model
    def _woo_tz_get(self):
        """
        Gives all timezones from base.
        @author: Maulik Barad on Date 18-Nov-2019.
        @return: Calls base method for all timezones.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        return _tz_get(self)

    @api.model
    def set_woo_import_after_date(self):
        """
        It is used to set after order date which has already created an instance.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 16 March 2021.
        Task_id: 172067 - Order import after date
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        sale_order_obj = self.env["sale.order"]
        instances = self.search([])
        order_after_date = datetime.now() - timedelta(30)
        for instance in instances:
            if not instance.import_order_after_date:
                order = sale_order_obj.search([('woo_instance_id', '=', instance.id)],
                                              order='date_order asc', limit=1) or False
                if order:
                    order_after_date = order.date_order
                instance.write({"import_order_after_date": order_after_date})
        return order_after_date

    name = fields.Char(size=120, required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    woo_host = fields.Char("Host", required=True)
    auto_import_product = fields.Boolean(string="Auto Create Product if not found?", default=False)
    sync_price_with_product = fields.Boolean("Sync Product Price?", default=True,
                                             help="Check if you want to import price along with products")
    sync_images_with_product = fields.Boolean("Sync Images?", default=True,
                                              help="Check if you want to import images along with products")
    woo_consumer_key = fields.Char("Consumer Key", required=True,
                                   help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> "
                                        "API >> Keys/Apps >> Click on Add Key")
    woo_consumer_secret = fields.Char("Consumer Secret", required=True,
                                      help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings "
                                           ">> API >> Keys/Apps >> Click on Add Key")
    woo_verify_ssl = fields.Boolean("Verify SSL", default=False,
                                    help="Check this if your WooCommerce site is using SSL certificate")
    woo_admin_username = fields.Char("Username", help="WooCommerce UserName,Used to Export Image Files.")
    woo_admin_password = fields.Char("Password", help="WooCommerce Password,Used to Export Image Files.")
    woo_version = fields.Selection([("v3", "Below 2.6"), ("wc/v1", "2.6 To 2.9"), ("wc/v2", "3.0 To 3.4"),
                                    ("wc/v3", "3.5+")], string="WooCommerce Version", default="wc/v3",
                                   help="Set the appropriate WooCommerce Version you are using currently or\nLogin "
                                        "into WooCommerce site,Go to Admin Panel >> Plugins")
    woo_pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    woo_extra_pricelist_id = fields.Many2one('product.pricelist', string='Extra Pricelist')
    woo_stock_field = fields.Many2one('ir.model.fields', string='Stock Field', default=_default_stock_field)
    woo_last_synced_order_date = fields.Datetime(string="Last Date of Import Order",
                                                 help="Which from date to import woo order from woo commerce")
    woo_warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', check_company=True,
                                       default=_get_default_warehouse, required=True)
    woo_visible = fields.Boolean("Visible on the product page?", default=True,
                                 help="Attribute is visible on the product page")
    woo_attribute_type = fields.Selection([("select", "Select"), ("text", "Text")], string="Attribute Type",
                                          default="select")
    woo_currency_id = fields.Many2one("res.currency", string="Currency", help="Woo Commerce Currency.")
    woo_lang_id = fields.Many2one('res.lang', string='Language', default=_get_default_language)
    woo_payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', default=_default_payment_term)
    color = fields.Integer("Color Index")
    import_order_status_ids = fields.Many2many("import.order.status.ept", "woo_instance_order_status_rel",
                                               "instance_id", "status_id", "Import Order Status",
                                               default=_default_order_status,
                                               help="Selected status orders will be imported from WooCommerce")
    last_order_import_date = fields.Datetime(help="This date is used to import order from this date.")
    sales_team_id = fields.Many2one('crm.team', help="Choose Sales Team that handles the order you import.")
    custom_order_prefix = fields.Boolean("Use Odoo Default Sequence?",
                                         help="If checked,Then use default sequence of odoo while create sale order.")
    order_prefix = fields.Char(size=10, help="Custom order prefix for Woocommerce orders.")
    shipping_product_id = fields.Many2one("product.product", "Shipping", default=_default_shipping_product,
                                          ondelete="restrict")
    fee_product_id = fields.Many2one("product.product", "Fees", default=_default_fee_product, ondelete="restrict")
    discount_product_id = fields.Many2one("product.product", "Discount", default=_default_discount_product,
                                          ondelete="restrict")
    last_inventory_update_time = fields.Datetime()
    woo_stock_auto_export = fields.Boolean(string="Woo Stock Auto Update",
                                           help="Check if you want to automatically update stock levels from Odoo to "
                                                "WooCommerce.")
    auto_import_order = fields.Boolean("Auto Import Order from Woo?", help="Imports orders at certain interval.")
    auto_import_complete_order = fields.Boolean("Auto Import Complete Order from Woo?",
                                                help="Imports complete orders at certain interval.")
    auto_import_cancel_order = fields.Boolean("Auto Import Cancel Order from Woo?",
                                              help="Imports cancel orders at certain interval.")
    auto_update_order_status = fields.Boolean(string="Auto Update Order Status in Woo?",
                                              help="Automatically update order status to WooCommerce.")
    store_timezone = fields.Selection("_woo_tz_get", help="Timezone of Store for requesting data.")
    apply_tax = fields.Selection([("odoo_tax", "Odoo Default Tax"), ("create_woo_tax", "Create new tax if not found")],
                                 default="create_woo_tax", copy=False, help=""" For Woocommerce Orders :- \n
                                 1) Odoo Default Tax Behavior - The Taxes will be set based on Odoo's default 
                                 functional behavior i.e. based on Odoo's Tax and Fiscal Position configurations. \n
                                 2) Create New Tax If Not Found - System will search the tax data received from 
                                 Woocommerce in Odoo, will create a new one if it fails in finding it.""")
    invoice_tax_account_id = fields.Many2one('account.account', string='Invoice Tax Account')
    credit_note_tax_account_id = fields.Many2one('account.account',
                                                 string='Credit Note Tax Account')
    user_ids = fields.Many2many('res.users', string='Responsible User')
    activity_type_id = fields.Many2one('mail.activity.type')
    date_deadline = fields.Integer('Deadline lead days', help="It adds number of days in activity's deadline date")
    is_create_schedule_activity = fields.Boolean(string="Is Create Schedule Activity?",
                                                 help="If marked it will create a schedule activity of mismatch sales "
                                                      "order in the order queue.")
    active = fields.Boolean(default=True)
    webhook_ids = fields.One2many("woo.webhook.ept", "instance_id")
    create_woo_product_webhook = fields.Boolean("Manage WooCommerce Products via Webhooks",
                                                help="If checked, it will create all product related webhooks.")
    create_woo_customer_webhook = fields.Boolean("Manage WooCommerce Customers via Webhooks",
                                                 help="If checked, it will create all customer related webhooks.")
    create_woo_order_webhook = fields.Boolean("Manage WooCommerce Orders via Webhooks",
                                              help="If checked, it will create all order related webhooks.")
    create_woo_coupon_webhook = fields.Boolean("Manage WooCommerceCoupons via Webhooks",
                                               help="If checked, it will create all coupon related webhooks.")
    weight_uom_id = fields.Many2one("uom.uom", string="Weight UoM",
                                    default=lambda self: self.env.ref("uom.product_uom_kgm", False))
    is_export_update_images = fields.Boolean("Do you want to export/update Images?", default=False,
                                             help="Check this if you want to export/update product images from Odoo "
                                                  "to Woocommerce store.")
    last_completed_order_import_date = fields.Datetime(help="This date is when the completed orders imported at last.")
    last_cancel_order_import_date = fields.Datetime(help="This date is when the canceled orders imported at last.")
    tax_rounding_method = fields.Selection([("round_per_line", "Round per Line"), ("round_globally", "Round Globally")],
                                           default="round_per_line")
    is_instance_create_from_onboarding_panel = fields.Boolean(default=False)
    is_onboarding_configurations_done = fields.Boolean(default=False)
    woo_order_data = fields.Text(compute="_compute_kanban_woo_order_data")
    import_order_after_date = fields.Datetime(help="Connector only imports those orders which have created after a "
                                                   "given date.", default=set_woo_import_after_date)
    import_products_last_date = fields.Datetime(help="This date is when the products are imported at last.")

    # Analytic
    woo_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                              domain="['|', ('company_id', '=', False), "
                                                     "('company_id', '=', company_id)]")
    # woo_analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags',
    #                                         domain="['|', ('company_id', '=', False),
    #                                         ('company_id', '=', company_id)]")

    is_woo_digest = fields.Boolean(string="Set Shopify Digest?")

    # WooCommerce Meta Field Mapping
    meta_mapping_ids = fields.One2many("woo.meta.mapping.ept", "instance_id")

    woo_stock_export_warehouse_ids = fields.Many2many('stock.warehouse', string='Stock Export Warehouse', required=True)

    import_partner_as_company = fields.Boolean()
    woo_instance_product_categ_id = fields.Many2one("product.category", string="Product Category",
                                                    help="This category will set on new create products.")

    def _compute_kanban_woo_order_data(self):
        """
        Use: This method is used to get all data for dashboard
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 30/10/20
        """
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
            order_data = record.get_total_orders()
            # Product count query
            product_data = record.get_total_products()
            # Order shipped count query
            order_shipped = record.get_shipped_orders()
            # Customer count query
            customer_data = record.get_customers()
            # refund count query
            refund_data = record.get_refund()
            record.woo_order_data = json.dumps({
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
                "currency_symbol": record.company_id.currency_id.symbol or '',
                "graph_sale_percentage": {'type': data_type, 'value': comparison_value}
            })

    def get_graph_data(self, record):
        """
        Use: To get the details of woo sale orders and total amount month wise or year wise to prepare the graph
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: woo sale order date or month and sum of sale orders amount of current instance
        """

        def get_current_week_date(record):
            self._cr.execute("""SELECT to_char(date(d.day),'DAY'), t.amount_untaxed as sum
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
                                       AND    date(date_order) <= (select date_trunc('week', date(current_date)) + interval '6 days')
                                       AND woo_instance_id=%s and state in ('sale','done')
                                       GROUP  BY 1
                                       ) t USING (day)
                                    ORDER  BY day;""" % record.id)
            return self._cr.dictfetchall()

        def graph_of_current_year(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',month),'MONTH')),sum(amount_untaxed) from
                                        (
                                        SELECT 
                                          DATE_TRUNC('month',date(day)) as month,
                                          0 as amount_untaxed
                                        FROM generate_series(date(date_trunc('year', (current_date)))
                                            , date(date_trunc('year', (current_date)) + interval '1 YEAR - 1 day')
                                            , interval  '1 MONTH') day
                                        union all
                                        SELECT DATE_TRUNC('month',date(date_order)) as month,
                                        sum(amount_untaxed) as amount_untaxed
                                          FROM   sale_order
                                        WHERE  date(date_order) >= (select date_trunc('year', date(current_date))) AND date(date_order)::date <= (select date_trunc('year', date(current_date)) + '1 YEAR - 1 day')
                                        and woo_instance_id = %s and state in ('sale','done')
                                        group by DATE_TRUNC('month',date(date_order))
                                        order by month
                                        )foo 
                                        GROUP  BY foo.month
                                        order by foo.month""" % record.id)
            return self._cr.dictfetchall()

        def graph_of_current_month(record):
            self._cr.execute("""select EXTRACT(DAY from date(date_day)) :: integer,sum(amount_untaxed) from (
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
                            AND date(date_order)::date <= (select date_trunc('month', date(current_date)) + '1 MONTH - 1 day')
                            and woo_instance_id = %s and state in ('sale','done')
                            group by 1
                            )foo 
                            GROUP  BY 1
                            ORDER  BY 1""" % record.id)
            return self._cr.dictfetchall()

        def graph_of_all_time(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',date_order),'YYYY-MM')),sum(amount_untaxed)
                                    from sale_order where woo_instance_id = %s and state in ('sale','done')
                                    group by DATE_TRUNC('month',date_order) order by DATE_TRUNC('month',date_order)""" %
                             record.id)
            return self._cr.dictfetchall()

        # Prepare values for Graph
        if self._context.get('sort') == 'week':
            result = get_current_week_date(record)
        elif self._context.get('sort') == "month":
            result = graph_of_current_month(record)
        elif self._context.get('sort') == "year":
            result = graph_of_current_year(record)
        else:
            result = graph_of_all_time(record)
        values = [{"x": ("{}".format(data.get(list(data.keys())[0]))), "y": data.get('sum') or 0.0} for data in result]
        return values

    def get_compare_data(self, record):
        """
        :param record: woo instance
        :return: datatype > 'positive' or 'negative', comparison value
        """
        data_type = False
        total_percentage = 0.0

        def get_compared_week_data(record):
            current_total = 0.0
            previous_total = 0.0
            day_of_week = date.weekday(date.today())
            self._cr.execute("""select sum(amount_untaxed) as current_week from sale_order
                                    where date(date_order) >= (select date_trunc('week', date(current_date))) and 
                                    woo_instance_id=%s and state in ('sale','done')""" % record.id)
            current_week_data = self._cr.dictfetchone()
            if current_week_data:
                current_total = current_week_data.get('current_week') if current_week_data.get('current_week') else 0
            # Previous week data
            self._cr.execute("""select sum(amount_untaxed) as previous_week from sale_order
                                where date(date_order) between (select date_trunc('week', current_date) - interval '7 day') 
                                and (select date_trunc('week', (select date_trunc('week', current_date) - interval '7 
                                day')) + interval '%s day')
                                and woo_instance_id=%s and state in ('sale','done')
                                """ % (day_of_week, record.id))
            previous_week_data = self._cr.dictfetchone()
            if previous_week_data:
                previous_total = previous_week_data.get('previous_week') if previous_week_data.get(
                    'previous_week') else 0
            return current_total, previous_total

        def get_compared_month_data(record):
            current_total = 0.0
            previous_total = 0.0
            day_of_month = date.today().day - 1
            self._cr.execute("""select sum(amount_untaxed) as current_month from sale_order
                                    where date(date_order) >= (select date_trunc('month', date(current_date)))
                                    and woo_instance_id=%s and state in ('sale','done')""" % record.id)
            current_data = self._cr.dictfetchone()
            if current_data:
                current_total = current_data.get('current_month') if current_data.get('current_month') else 0
            # Previous week data
            self._cr.execute("""select sum(amount_untaxed) as previous_month from sale_order where date(date_order)
                                between (select date_trunc('month', current_date) - interval '1 month') and 
                                (select date_trunc('month', (select date_trunc('month', current_date) - interval '1 
                                month')) + interval '%s days')
                                and woo_instance_id=%s and state in ('sale','done')
                                """ % (day_of_month, record.id))
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
            self._cr.execute("""select sum(amount_untaxed) as current_year from sale_order
                                    where date(date_order) >= (select date_trunc('year', date(current_date))) 
                                    and woo_instance_id=%s and state in ('sale','done')""" % record.id)
            current_data = self._cr.dictfetchone()
            if current_data:
                current_total = current_data.get('current_year') if current_data.get('current_year') else 0
            # Previous week data
            self._cr.execute("""select sum(amount_untaxed) as previous_year from sale_order where date(date_order)
                                between (select date_trunc('year', date(current_date) - interval '1 year')) and 
                                (select date_trunc('year', date(current_date) - interval '1 year') + interval '%s days') 
                                and woo_instance_id=%s and state in ('sale','done')
                                """ % (delta, record.id))
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

    def get_total_orders(self):
        """
        Use: To get the list of woo sale orders month wise or year wise
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: total number of woo sale orders ids and action for sale orders of current instance
        """
        order_query = """select id from sale_order where woo_instance_id= %s and state in ('sale','done')""" % self.id

        def orders_of_current_week(order_query):
            qry = order_query + " and date(date_order) >= (select date_trunc('week', date(current_date))) order by " \
                                "date(date_order)"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def orders_of_current_month(order_query):
            qry = order_query + " and date(date_order) >= (select date_trunc('month', date(current_date))) order by " \
                                "date(date_order)"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def orders_of_current_year(order_query):
            qry = order_query + " and date(date_order) >= (select date_trunc('year', date(current_date))) order by " \
                                "date(date_order)"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def orders_of_all_time(record):
            self._cr.execute("""select id from sale_order where woo_instance_id = %s and state in ('sale','done')"""
                             % record.id)
            return self._cr.dictfetchall()

        order_data = {}
        if self._context.get('sort') == "week":
            result = orders_of_current_week(order_query)
        elif self._context.get('sort') == "month":
            result = orders_of_current_month(order_query)
        elif self._context.get('sort') == "year":
            result = orders_of_current_year(order_query)
        else:
            result = orders_of_all_time(self)
        order_ids = [data.get('id') for data in result]
        view = self.env.ref('woo_commerce_ept.action_woo_orders').sudo().read()[0]
        action = self.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def get_shipped_orders(self):
        """
        Use: To get the list of woo shipped orders month wise or year wise
        Task: 167063
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 29/10/20
        :return: total number of Woo shipped orders ids and action for shipped orders of current instance
        """
        shipped_query = """select so.id from stock_picking sp
                                 inner join sale_order so on so.procurement_group_id=sp.group_id inner 
                                 join stock_location on stock_location.id=sp.location_dest_id and stock_location.usage='customer' 
                                 where sp.updated_in_woo = True and sp.state != 'cancel' and 
                                 so.woo_instance_id=%s""" % self.id

        def shipped_order_of_current_week(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('week', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def shipped_order_of_current_month(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('month', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def shipped_order_of_current_year(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('year', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def shipped_order_of_all_time(shipped_query):
            self._cr.execute(shipped_query)
            return self._cr.dictfetchall()

        order_data = {}
        if self._context.get('sort') == "week":
            result = shipped_order_of_current_week(shipped_query)
        elif self._context.get('sort') == "month":
            result = shipped_order_of_current_month(shipped_query)
        elif self._context.get('sort') == "year":
            result = shipped_order_of_current_year(shipped_query)
        else:
            result = shipped_order_of_all_time(shipped_query)
        order_ids = [data.get('id') for data in result]
        view = self.env.ref('woo_commerce_ept.action_woo_orders').sudo().read()[0]
        action = self.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def get_total_products(self):
        """
        Use: To get the list of products exported from Woo instance
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 31/10/20
        :return: total number of Woo products ids and action for products
        """
        product_data = {}
        self._cr.execute("""select count(id) as total_count from woo_product_template_ept where
                            exported_in_woo = True and woo_instance_id = %s""" % self.id)
        result = self._cr.dictfetchall()
        if result:
            total_count = result[0].get('total_count')
        view = self.env.ref('woo_commerce_ept.action_woo_product_template_exported_ept').sudo().read()[0]
        action = self.prepare_action(view, [('exported_in_woo', '=', True), ('woo_instance_id', '=', self.id)])
        product_data.update({'product_count': total_count, 'product_action': action})
        return product_data

    def get_customers(self):
        """
        Use: To get the list of customers with Woo instance for current Woo instance
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 31/10/20
        :return: total number of customer ids and action for customers
        """
        customer_data = {}
        self._cr.execute("""select partner_id from woo_res_partner_ept where woo_instance_id = %s"""
                         % self.id)
        result = self._cr.dictfetchall()
        customer_ids = [data.get('partner_id') for data in result]
        view = self.env.ref('woo_commerce_ept.action_woo_partner').sudo().read()[0]
        action = self.prepare_action(view, [('id', 'in', customer_ids), ('active', 'in', [True, False])])
        customer_data.update({'customer_count': len(customer_ids), 'customer_action': action})
        return customer_data

    def get_refund(self):
        """
        Use: To get the list of refund orders of Woo instance for current Woo instance
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 03/11/20
        :return: total number of refund order ids and action for customers
        """
        refund_query = """select id from account_move where woo_instance_id=%s and move_type='out_refund'""" % self.id

        def refund_of_current_week(refund_query):
            qry = refund_query + " and date(invoice_date) >= (select date_trunc('week', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def refund_of_current_month(refund_query):
            qry = refund_query + " and date(invoice_date) >= (select date_trunc('month', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def refund_of_current_year(refund_query):
            qry = refund_query + " and date(invoice_date) >= (select date_trunc('year', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def refund_of_all_time(refund_query):
            self._cr.execute(refund_query)
            return self._cr.dictfetchall()

        refund_data = {}
        if self._context.get('sort') == "week":
            result = refund_of_current_week(refund_query)
        elif self._context.get('sort') == "month":
            result = refund_of_current_month(refund_query)
        elif self._context.get('sort') == "year":
            result = refund_of_current_year(refund_query)
        else:
            result = refund_of_all_time(refund_query)
        refund_ids = [data.get('id') for data in result]
        view = self.env.ref('woo_commerce_ept.action_refund_woo_invoices_ept').sudo().read()[0]
        # [('woo_instance_id', '=', record_id)]
        action = self.prepare_action(view, [('id', 'in', refund_ids)])
        refund_data.update({'refund_count': len(refund_ids), 'refund_action': action})
        return refund_data

    def prepare_action(self, view, domain):
        """
        Use: To prepare action dictionary
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 31/10/20
        :return: action details
        """
        action = {
            'name': view.get('name'),
            'type': view.get('type'),
            'domain': domain,
            'view_mode': view.get('view_mode'),
            'view_id': view.get('view_id')[0] if view.get('view_id') else False,
            'views': view.get('views'),
            # 'views' : [(False, 'list'), (False, 'form'), (False, 'kanban')],
            'res_model': view.get('res_model'),
            'target': view.get('target'),
        }

        if 'tree' in action['views'][0]:
            action['views'][0] = (action['view_id'], 'list')
        return action

    @api.model
    def perform_operation(self, record_id):
        """
        Use: To prepare Woo operation action
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 31/10/20
        :return: Woo operation action details
        """
        view = self.env.ref('woo_commerce_ept.action_wizard_woo_instance_import_export_operations').sudo().read()[0]
        action = self.prepare_action(view, [])
        action.update({'context': {'default_woo_instance_id': record_id}})
        return action

    @api.model
    def open_report(self, record_id):
        """
        Use: To prepare Woo report action
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 31/10/20
        :return: Woo report action details
        """
        view = self.env.ref('woo_commerce_ept.woo_sale_report_action_dashboard').sudo().read()[0]
        action = self.prepare_action(view, [('woo_instance_id', '=', record_id)])
        action.update({'context': {'search_default_woo_instances': record_id, 'search_default_Sales': 1,
                                   'search_default_filter_date': 1}})
        return action

    @api.model
    def open_logs(self, record_id):
        """
        Use: To prepare Woo logs action
        Task: 167349
        Added by: Preet Bhatti @Emipro Technologies
        Added on: 31/10/20
        :return: Woo logs action details
        """
        view = self.env.ref('woo_commerce_ept.action_woocommerce_common_log_line_ept').sudo().read()[0]
        return self.prepare_action(view, [('woo_instance_id', '=', record_id)])

    _sql_constraints = [('unique_host', 'unique(woo_host)',
                         "Instance already exists for given host. Host must be Unique for the instance!")]

    def toggle_active(self):
        """
        This method is overridden for archiving other properties, while archiving the instance from the Action menu.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 October 2020 .
        Task_id: 166948
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        context = dict(self._context)
        context.update({'active_ids': self.ids})
        action = self[0].with_context(context).action_open_deactive_wizard() if self else False
        return action

    def update_instance_data(self, domain):
        """
        This method archives products, auto crons, payment gateways and financial statuses and deletes webhooks,
        when an instance is archived.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_template_obj = self.env['woo.product.template.ept']
        data_queue_mixin_obj = self.env['data.queue.mixin.ept']
        ir_cron_obj = self.env["ir.cron"]
        sale_auto_workflow_configuration_obj = self.env['woo.sale.auto.workflow.configuration']
        payment_gateway_obj = self.env['woo.payment.gateway']
        woo_webhook_obj = self.env["woo.webhook.ept"]
        deactivate = {'active': False}

        auto_crons = ir_cron_obj.search([("name", "ilike", self.name), ("active", "=", True)])
        if auto_crons:
            auto_crons.write(deactivate)
        self.woo_stock_auto_export = self.auto_update_order_status = self.auto_import_order = \
            self.auto_import_complete_order = False
        woo_webhook_obj.search([('instance_id', '=', self.id)]).unlink()
        self.create_woo_product_webhook = self.create_woo_order_webhook = self.create_woo_customer_webhook = \
            self.create_woo_coupon_webhook = False
        woo_template_obj.search(domain).write(deactivate)
        sale_auto_workflow_configuration_obj.search(domain).write(deactivate)
        payment_gateway_obj.search(domain).write(deactivate)
        data_queue_mixin_obj.delete_data_queue_ept(is_delete_queue=True)

    def sync_shipping_method_payment_gateway(self):
        """
        This method used to sync shipping method and payment gateway.
        @author: Meera Sidapara@Emipro Technologies Pvt. Ltd on date 18-04-2022.
        @Task id: 187338 - Sync shipping method and payment method In Instance
        """
        payment_gateway_obj = self.env['woo.payment.gateway']
        shipping_method_obj = self.env['woo.shipping.method']
        if self.woo_version in ["wc/v2", "wc/v3"]:
            payment_gateway_obj.woo_get_payment_gateway(self)
            shipping_method_obj.woo_get_shipping_method(self)
        self.prepare_payment_methods()
        return True

    def woo_action_archive(self):
        """
        This method used to archive or unarchive instances and also disable the cron job of related instances while
        archiving the instance.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 09-12-2019.
        :Task id: 158502
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_template_obj = self.env['woo.product.template.ept']
        domain = [('woo_instance_id', '=', self.id)]

        if self.active:
            self.update_instance_data(domain)
        else:
            self.confirm()
            domain.append(('active', '=', False))
            woo_template_obj.search(domain).write({'active': True})
        self.active = not self.active
        return True

    def action_open_deactive_wizard(self):
        """
        This method is used to open a wizard to display the information related to how much data will active/archive
        while instance is actived/archived.
        @return: action
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 November 2020 .
        Task_id: 167723
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        view = self.env.ref('woo_commerce_ept.view_inactive_woo_instance')
        return {
            'name': _('Instance Active/Inactive Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'woo.manual.queue.process.ept',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': self._context,
        }

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create pricelist and set that to instance.
        :param vals_list: Dict of instance
        :return: instance
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for vals in vals_list:
            if vals.get("woo_host").endswith('/'):
                vals["woo_host"] = vals.get("woo_host").rstrip('/')

        instances = super(WooInstanceEpt, self).create(vals_list)

        for instance in instances:
            instance.woo_set_current_currency_data()
            pricelist = instance.woo_create_pricelist()
            extra_pricelist_id = instance.woo_create_sale_pricelist()
            sales_channel = instance.woo_create_sales_channel()

            instance.write({
                'woo_pricelist_id': pricelist.id,
                'sales_team_id': sales_channel.id,
                'woo_extra_pricelist_id': extra_pricelist_id.id,
            })

        return instances

    def woo_create_pricelist(self):
        """
        Create price list for woocommerce instance
        :return: pricelist
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 18-11-2019.
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        vals = {
            'name': "Woo {} Pricelist".format(self.name),
            'currency_id': self.woo_currency_id and self.woo_currency_id.id or False,
            "company_id": self.company_id.id
        }
        return self.env['product.pricelist'].create(vals)

    def woo_create_sale_pricelist(self):
        """
        Create sale price list for woocommerce instance
        @return: pricelist
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 12-05-2022.
        @Task id: 189553 - Sync sale price
        """
        vals = {
            'name': "Woo {} Sale Pricelist".format(self.name),
            'currency_id': self.woo_currency_id and self.woo_currency_id.id or False,
            "company_id": self.company_id.id
        }
        return self.env['product.pricelist'].create(vals)

    def woo_create_sales_channel(self):
        """
        Creates new sales team for Woo instance.
        @author: Maulik Barad on Date 09-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        vals = {'name': self.name, 'use_quotations': True}
        return self.env['crm.team'].create(vals)

    def woo_set_current_currency_data(self):
        """
        Set default instance currency according to woocommerce store currency
        :return: Boolean
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 18-11-2019.
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        currency = self.woo_get_currency()
        self.woo_currency_id = currency and currency.id or self.env.user.currency_id.id or False
        return True

    def woo_create_log_line(self, message):
        """
        This method creates log line from the message.
        @param message: Message to add in log line as per the issue.
        @return: Dictionary of log line data.
        @author: Maulik Barad on Date 30-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        return self.env["common.log.lines.ept"].create_common_log_line_ept(
            operation_type="import", module="woocommerce_ept", woo_instance_id=self.id, model_name=self._name,
            message=message).id

    def woo_check_for_currency(self, currency_code):
        """
        It searches for the currency from code.
        @param currency_code: Currency code got from WooCommerce store.
        @return: Record of currency if found.
        @author: Maulik Barad on Date 30-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        currency_obj = self.env['res.currency']

        currency = currency_obj.search([('name', '=', currency_code)])

        if not currency:
            currency = currency_obj.search([('name', '=', currency_code), ('active', '=', False)])
            currency.active = True
        if not currency:
            raise UserError(_("Currency %s not found in odoo.\nPlease make sure currency record is created for %s and"
                              " is in active state.") % (currency_code, currency_code))
        return currency

    @api.model
    def woo_get_currency(self):
        """
        Get currency from odoo according to woocommerce store currency.
        :return: currency
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 18-11-2019.
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        response = self.woo_get_system_info()
        if not response:
            raise UserError(_("Json Error:\n The response is not coming in proper format from WooCommerce store.\n "
                              "Please check the Store."))

        currency_code = response.get('settings').get('currency', False)

        if not currency_code:
            message = "Import Woo System Status \nCurrency Code Not Received in Response"
            self.woo_create_log_line(message)

        currency = self.woo_check_for_currency(currency_code)

        return currency

    def woo_get_system_info(self):
        """
        Get system information like store currency, configurations of woocommerce etc.
        :return: List
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 18-11-2019.
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = self.woo_connect()
        try:
            res = wc_api.get("system_status")
        except Exception as error:
            raise UserError(_("Something went wrong while getting WooCommerce Status.\n\nPlease Check your Connection "
                              "and Instance Configuration.\n\n" + str(error)))

        if not isinstance(res, requests.models.Response):
            message = "Import Woo System Status \nResponse is not in proper format :: %s" % (res)
            self.woo_create_log_line(message)
        if res.status_code not in [200, 201]:
            message = "Error in Import Woo System Status %s" % res.content
            self.woo_create_log_line(message)

        try:
            response = res.json()
        except Exception as error:
            response = []
            message = "Json Error : While import system status from WooCommerce for self %s. \n%s" % (self.name, error)
            self.woo_create_log_line(message)

        return response

    @api.model
    def woo_connect(self):
        """
        Creates connection for given instance of WooCommerce.
        @author: Maulik Barad on Date 09-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        host = self.woo_host
        consumer_key = self.woo_consumer_key
        consumer_secret = self.woo_consumer_secret
        wc_api = woocommerce.api.API(url=host, consumer_key=consumer_key, consumer_secret=consumer_secret,
                                     verify_ssl=self.woo_verify_ssl, version=self.woo_version, query_string_auth=True)
        return wc_api

    def confirm(self):
        """
        Performs needed operations for instance after its creation.
        @author: Maulik Barad on Date 09-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = self.woo_connect()
        if self.is_export_update_images:
            self.check_credentials_for_image(self.woo_admin_username, self.woo_admin_password)

        try:
            response = wc_api.get("products", params={"_fields": "id"})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Products.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))
        if not isinstance(response, requests.models.Response):
            raise UserError(_("Response is not in proper format :: %s") % response)
        if response.status_code != 200:
            raise UserError(_("%s\n%s") % (response.status_code, response.reason))

        # When there is case of full discount, customer do not need to pay or select any payment method for that order.
        # So, creating this type of payment method for applying the auto workflow and picking policy in order.
        self.prepare_payment_methods()
        return True

    def prepare_payment_methods(self):
        """
        This method is used to prepare payment methods and financial status, while creating instance and activating
        instance.
        @author: Maulik Barad on Date 29-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        payment_gateway_obj = self.env['woo.payment.gateway']
        no_payment_method = payment_gateway_obj.with_context(active_test=False).search(
            [("code", "=", "no_payment_method"), ("woo_instance_id", "=", self.id)])

        if not no_payment_method:
            payment_gateway_obj.create({"name": "No Payment Method",
                                        "code": "no_payment_method",
                                        "woo_instance_id": self.id})

        payment_methods = payment_gateway_obj.with_context(active_test=False).search(
            [('woo_instance_id', '=', self.id)])
        if payment_methods:
            payment_methods.write({'active': True})
            self.woo_create_financial_status('paid', payment_methods)
            self.woo_create_financial_status('not_paid', payment_methods)
        return True

    def check_credentials_for_image(self, username, password, host=False):
        """
        This method checks if the given credentials are correct or not for image export process.
        @param username: WooCommerce admin username.
        @param password: WooCommerce admin password.
        @param host: WooCommerce host. By default, instance's host can be used.
        @author: Maulik Barad on Date 29-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if not host:
            host = self.woo_host
        client = base.Client("%s/xmlrpc.php" % host, username, password)
        try:
            client.call(media.UploadFile(""))
        except InvalidCredentialsError as error:
            raise UserError(_("%s") % error)
        except Exception as error:
            _logger.info(_('%s'), error)
        return True

    def reset_woo_credentials(self):
        """
        This method call from the button in the instance view and it used for taken values of username and password.
        @param : self
        @return: action(Redirect to form view)
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27 August 2020.
        Task_id:165888
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        res_config_woo_instance_obj = self.env['res.config.woo.instance']
        form_view_id = self.env.ref('woo_commerce_ept.view_set_woo_credential').id
        vals = {
            'woo_host': self.woo_host,
            'woo_consumer_key': self.woo_consumer_key,
            'woo_consumer_secret': self.woo_consumer_secret,
            'store_timezone': self.store_timezone,
            'is_export_update_images': self.is_export_update_images,
            'woo_admin_username': self.woo_admin_username,
            'woo_admin_password': self.woo_admin_password,
        }
        woo_res_config_id = res_config_woo_instance_obj.create(vals)
        return {
            'name': _('Set Credentials'),
            'view_mode': 'form',
            'res_model': 'res.config.woo.instance',
            'views': [(form_view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': woo_res_config_id.id,
        }

    def woo_create_financial_status(self, financial_status, payment_methods):
        """
        Creates financial status for all payment methods of Woo instance.
        @param financial_status: Status as paid or not paid.
        @return: Boolean
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        financial_status_obj = self.env["woo.sale.auto.workflow.configuration"]
        auto_workflow_record = self.env.ref("common_connector_library.automatic_validation_ept")
        for payment_method in payment_methods:
            domain = [('woo_instance_id', '=', self.id),
                      ('woo_payment_gateway_id', '=', payment_method.id),
                      ('woo_financial_status', '=', financial_status)]
            existing_financial_status = financial_status_obj.with_context(active_test=False).search(domain)

            if existing_financial_status:
                existing_financial_status.write({'active': True})
                continue

            vals = {
                'woo_instance_id': self.id,
                'woo_auto_workflow_id': auto_workflow_record.id,
                'woo_payment_gateway_id': payment_method.id,
                'woo_financial_status': financial_status
            }
            financial_status_obj.create(vals)
        return True

    def action_redirect_to_ir_cron(self):
        """
        This method is used for redirect to scheduled action tree view and filtered only WooCommerce crons.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 16-11-2019.
        :Task id: 156886
        :return: action
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        action = self.env.ref('base.ir_cron_act').read()[0]
        action['domain'] = [('name', 'ilike', self.name), ("active", "=", True)]
        return action

    def refresh_webhooks(self, webhooks=False):
        """
        This method refreshes all webhooks for current instance.
        @author: Maulik Barad on Date 19-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if not webhooks:
            webhooks = self.webhook_ids
        for webhook in webhooks:
            webhook.get_webhook()
        _logger.info("Webhooks are refreshed of instance '%s'.", self.name)
        return True

    def configure_woo_product_webhook(self):
        """
        Creates or activates all product related webhooks, when it is True.
        Pauses all product related webhooks, when it is False.
        @author: Maulik Barad on Date 06-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        topic_list = ["product.updated", "product.deleted", "product.restored"]
        self.configure_webhooks(topic_list)
        return True

    def configure_woo_customer_webhook(self):
        """
        Creates or activates all customer related webhooks, when it is True.
        Pauses all product related webhooks, when it is False.
        @author: Maulik Barad on Date 06-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        topic_list = ["customer.updated", "customer.deleted"]
        self.configure_webhooks(topic_list)
        return True

    def configure_woo_order_webhook(self):
        """
        Creates or activates all order related webhooks, when it is True.
        Pauses all product related webhooks, when it is False.
        @author: Maulik Barad on Date 06-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        topic_list = ["order.updated", "order.deleted"]
        self.configure_webhooks(topic_list)
        return True

    def configure_woo_coupon_webhook(self):
        """
        Creates or activates all coupon related webhooks, when it is True.
        Pauses all product related webhooks, when it is False.
        @author: Maulik Barad on Date 06-Jan-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        topic_list = ["coupon.updated", "coupon.deleted", "coupon.restored"]
        self.configure_webhooks(topic_list)
        return True

    def configure_webhooks(self, topic_list):
        """
        Creates or activates all webhooks as per topic list, when it is True.
        Pauses all product related webhooks, when it is False.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        webhook_obj = self.env["woo.webhook.ept"]

        instance_id = self.id
        resource = topic_list[0].split('.')[0]
        available_webhooks = webhook_obj.search([("topic", "in", topic_list), ("instance_id", "=", instance_id)])

        self.refresh_webhooks(available_webhooks)

        if getattr(self, "create_woo_%s_webhook" % resource):
            if available_webhooks:
                available_webhooks.toggle_status("active")
                _logger.info("%s Webhooks are activated of instance '%s'.", resource, self.name)
                topic_list = list(set(topic_list) - set(available_webhooks.mapped("topic")))

            for topic in topic_list:
                webhook_obj.create({"name": self.name + "_" + topic.replace(".", "_"),
                                    "topic": topic, "instance_id": instance_id})
                _logger.info("Webhook for '%s' of instance '%s' created.", topic, self.name)
        else:
            if available_webhooks:
                available_webhooks.toggle_status("paused")
                _logger.info("%s Webhooks are paused of instance '%s'.", resource, self.name)
        return True

    def search_woo_instance(self):
        """
        Usage : Search Woo Instance
        @Task:  166918 - Odoo v14 : Dashboard analysis
        @author: Dipak Gogiya, 23/09/2020
        :return: woo.instance.ept()
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        company = self.env.company or self.env.user.company_id
        instance = self.search([('is_instance_create_from_onboarding_panel', '=', True),
                                ('is_onboarding_configurations_done', '=', False),
                                ('company_id', '=', company.id)], limit=1, order='id desc')
        if not instance:
            instance = self.search([('company_id', '=', company.id), ('is_onboarding_configurations_done', '=', False)],
                                   limit=1, order='id desc')
            instance.write({'is_instance_create_from_onboarding_panel': True})
        return instance

    def get_woo_cron_execution_time(self, cron_name):
        """
        This method is used to get the interval time of the cron.
        @param cron_name: External ID of the Cron.
        @return: Interval time in seconds.
        @author: Maulik Barad on Date 25-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        process_queue_cron = self.env.ref(cron_name, False)
        if not process_queue_cron:
            raise UserError(_("Please upgrade the module. \n Maybe the job has been deleted, it will be recreated at "
                              "the time of module upgrade."))
        interval = process_queue_cron.interval_number
        interval_type = process_queue_cron.interval_type
        if interval_type == "months":
            days = 0
            current_year = fields.Date.today().year
            current_month = fields.Date.today().month
            for i in range(0, interval):
                month = current_month + i

                if month > 12:
                    if month == 13:
                        current_year += 1
                    month -= 12

                days_in_month = monthrange(current_year, month)[1]
                days += days_in_month

            interval_type = "days"
            interval = days
        interval_in_seconds = _secondsConverter[interval_type](interval)
        return interval_in_seconds

    def meta_field_mapping(self, vals, operation_type, record):
        """
        This method is used for map woocommerce meta field with Odoo field.
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 12 May 2022.
        @Task: 189552 - Meta data sync
        """
        _logger.info("Mapping start of record(%s)", record)
        if operation_type == "import":
            meta_vals_list = vals.get('meta_data')
            for meta_value in meta_vals_list:
                meta_mapping = self.meta_mapping_ids.filtered(
                    lambda mapping: mapping.woo_operation == self._context.get(
                        'woo_operation') and mapping.woo_meta_key == meta_value.get(
                        'key') and mapping.model_id.model == record._name)
                if meta_mapping:
                    self.write_meta_key_value_in_record(meta_mapping, meta_value, record)
        elif operation_type == "export":
            meta_mapping_record = self.meta_mapping_ids.filtered(
                lambda mapping: mapping.woo_operation == self._context.get(
                    'woo_operation') and mapping.model_id.model == record._name)
            last_vals = [val for val in vals if 'meta_data' not in val]
            data = list(filter(lambda val: val.get('meta_data'), last_vals))
            if meta_mapping_record:
                for meta_mapping_field in meta_mapping_record:
                    if len(record.ids) > 1:
                        rec_val = []
                        for rec in record:
                            rec_val.append(getattr(rec, meta_mapping_field.field_id.name))
                        field_value = ','.join(rec_val)
                    else:
                        field_value = getattr(record, meta_mapping_field.field_id.name)
                    if not data:
                        data.append({
                            'key': meta_mapping_field.woo_meta_key, 'value': field_value})
                        last_vals[0].update({'meta_data': data})
                    else:
                        last_vals[0].get('meta_data').append({
                            'key': meta_mapping_field.woo_meta_key, 'value': field_value})
            return last_vals
        return True

    def write_meta_key_value_in_record(self, meta_mapping, meta_value, record):
        """
        This method is used for write woocommerce meta key value in Odoo field.
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 14 May 2022.
        @Task: 189552 - Meta data sync
        """
        try:
            meta_key_value = meta_value.get('value')
            if meta_mapping.field_id.ttype in ['datetime', 'date']:
                # date_time_pattern = ["%s %s" % (d, t) for d in DATE_PATTERNS for t in TIME_PATTERNS]
                # patterns = DATE_PATTERNS + date_time_pattern
                # match_format = check_patterns(patterns, [meta_value.get('value')])
                # meta_key_value = datetime.strptime(meta_value.get('value'), match_format)
                match_format = meta_mapping.date_format + ' ' + meta_mapping.time_format if meta_mapping.time_format else meta_mapping.date_format
                meta_key_value = datetime.strptime(meta_value.get('value'), match_format)
            field = record._fields[meta_mapping.field_id.name]
            record_value = field.convert_to_cache(meta_key_value, record)
            record.write(
                {meta_mapping.field_id.name: record_value})
        except Exception as error:
            _logger.warning(_('Something went wrong while sync WooCommerce Metadata \n %s'), error)
        return True
