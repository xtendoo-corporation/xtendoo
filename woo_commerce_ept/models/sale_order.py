# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import ast
import logging
import time
from datetime import timedelta, datetime

import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import split_every, format_date

_logger = logging.getLogger("WooCommerce")


class SaleOrder(models.Model):
    """
    Inherited for importing and creating sale orders from WooCommerce.
    @author: Maulik Barad on Date 23-Oct-2019.
    """
    _inherit = "sale.order"

    def _compute_woo_order_status(self):
        """
        Compute updated_in_woo of order from the pickings.
        @author: Maulik Barad on Date 04-06-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for order in self:
            if order.woo_instance_id:
                pickings = order.picking_ids.filtered(lambda x: x.state != "cancel")
                if pickings:
                    outgoing_picking = pickings.filtered(
                        lambda x: x.location_dest_id.usage == "customer")
                    if all(outgoing_picking.mapped("updated_in_woo")):
                        order.updated_in_woo = True
                        continue
                elif order.woo_status == "completed":
                    """When all products are service type and no pickings are there."""
                    order.updated_in_woo = True
                    continue
                order.updated_in_woo = False
                continue
            order.updated_in_woo = False

    def _search_woo_order_ids(self, operator, value):
        query = """select so.id from stock_picking sp
                    inner join sale_order so on so.procurement_group_id=sp.group_id                   
                    inner join stock_location on stock_location.id=sp.location_dest_id and stock_location.usage='customer'
                    where sp.updated_in_woo %s true and sp.state != 'cancel'
                    """ % operator
        if operator == '=':
            query += """union all
                    select so.id from sale_order as so
                    inner join sale_order_line as sl on sl.order_id = so.id
                    inner join stock_move as sm on sm.sale_line_id = sl.id
                    where sm.picking_id is NULL and sm.state = 'done' and so.woo_instance_id notnull"""
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids = []
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id', 'in', order_ids)]

    woo_order_id = fields.Char("Woo Order Reference", help="WooCommerce Order Reference", copy=False)
    woo_order_number = fields.Char("Order Number", help="WooCommerce Order Number", copy=False)
    woo_instance_id = fields.Many2one("woo.instance.ept", "Woo Instance", copy=False)
    payment_gateway_id = fields.Many2one("woo.payment.gateway", "Woo Payment Gateway", copy=False)
    woo_coupon_ids = fields.Many2many("woo.coupons.ept", string="Coupons", copy=False)
    woo_trans_id = fields.Char("Transaction ID", help="WooCommerce Order Transaction Id", copy=False)
    woo_customer_ip = fields.Char("Customer IP", help="WooCommerce Customer IP Address", copy=False)
    updated_in_woo = fields.Boolean("Updated In woo", compute="_compute_woo_order_status",
                                    search="_search_woo_order_ids", copy=False)
    canceled_in_woo = fields.Boolean("Canceled In WooCommerce", default=False, copy=False)
    woo_status = fields.Selection([("pending", "Pending"), ("processing", "Processing"),
                                   ("on-hold", "On hold"), ("completed", "Completed"),
                                   ("cancelled", "Cancelled"), ("refunded", "Refunded")], copy=False, tracking=7)
    is_service_woo_order = fields.Boolean(default=False, help="It uses to identify that sale order contains all "
                                                              "products as service type.")
    wc_order_reference = fields.Char("WC Order Reference")

    _sql_constraints = [('_woo_sale_order_unique_constraint', 'unique(woo_order_id,woo_instance_id,woo_order_number)',
                         "Woocommerce order must be unique")]

    def create_woo_order_data_queue(self, woo_instance, orders_data, order_type, created_by="import"):
        """
        Creates order data queues from the data got from API.
        @param woo_instance: Instance of Woocommerce.
        @param orders_data: Imported JSON data of orders.
        @param created_by: By which process, we are creating the queues.
        @param order_type: Type of order for which the queue is being created.
        @author: Maulik Barad on Date 04-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_queues_list = order_data_queue_obj = self.env["woo.order.data.queue.ept"]
        bus_bus_obj = self.env['bus.bus']
        while orders_data:
            vals = {"instance_id": woo_instance.id, "created_by": created_by,
                    "queue_type": "shipped" if order_type == "completed" else "unshipped"}
            data = orders_data[:50]
            if data:
                order_data_queue = order_data_queue_obj.create(vals)
                _logger.info("New order queue %s created.", order_data_queue.name)
                order_data_queue.create_woo_data_queue_lines(data)
                if order_data_queue.order_data_queue_line_ids:
                    order_queues_list += order_data_queue
                    _logger.info("Lines added in Order queue %s.", order_data_queue.name)
                    message = "Order Queue created %s" % order_data_queue.name
                    bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
                                         {'title': _('WooCommerce Connector'), 'message': _(message), "sticky": False,
                                          "warning": True})
                else:
                    order_data_queue.unlink()
                del orders_data[:50]
                self._cr.commit()

        return order_queues_list

    def woo_convert_dates_by_timezone(self, instance, from_date, to_date, order_type):
        """
        This method converts the dates by timezone of the store to import orders.
        @param instance: Instance.
        @param from_date: From date for importing orders.
        @param to_date: To date for importing orders.
        @param order_type: Order type for check from date.
        @author: Maulik Barad on Date 03-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if not from_date:
            if order_type == 'completed' and instance.last_completed_order_import_date:
                from_date = instance.last_completed_order_import_date - timedelta(days=1)
            elif instance.last_order_import_date:
                from_date = instance.last_order_import_date - timedelta(days=1)
            elif order_type == 'cancelled' and instance.last_cancel_order_import_date:
                from_date = instance.last_cancel_order_import_date - timedelta(days=1)
            else:
                from_date = fields.Datetime.now() - timedelta(days=1)
        to_date = to_date if to_date else fields.Datetime.now()

        from_date = pytz.utc.localize(from_date).astimezone(pytz.timezone(instance.store_timezone))
        to_date = pytz.utc.localize(to_date).astimezone(pytz.timezone(instance.store_timezone))

        return from_date, to_date

    def import_woo_orders(self, woo_instance, from_date="", to_date="", order_type=""):
        """
        Imports orders from woo commerce and creates order data queue.
        @param order_type: Type of Orders.
        @param woo_instance: Woo Instance to import orders from.
        @param from_date: Orders will be imported which are created after this date.
        @param to_date: Orders will be imported which are created before this date.
        @author: Maulik Barad on Date 04-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_instance_obj = self.env["woo.instance.ept"]
        start = time.time()

        if isinstance(woo_instance, int):
            woo_instance = woo_instance_obj.browse(woo_instance)
        if not woo_instance.active:
            return False

        from_date, to_date = self.woo_convert_dates_by_timezone(woo_instance, from_date, to_date, order_type)

        params = {"after": str(from_date)[:19], "before": str(to_date)[:19], "per_page": 100, "page": 1,
                  "order": "asc", "status": ",".join(map(str, woo_instance.import_order_status_ids.mapped("status")))}
        if order_type == 'completed':
            params["status"] = "completed"
        elif order_type == 'cancelled':
            params["status"] = "cancelled"
        order_data_queue = self.get_order_data_wc_v3(params, woo_instance, order_type=order_type)

        if order_type == 'completed':
            date_field = "last_completed_order_import_date"
        elif order_type == 'cancelled':
            date_field = "last_cancel_order_import_date"
        else:
            date_field = "last_order_import_date"
        setattr(woo_instance, date_field, to_date.astimezone(pytz.timezone("UTC")).replace(tzinfo=None))
        end = time.time()
        if order_data_queue:
            _logger.info("Order queues created in %s seconds.", str(end - start))

        return order_data_queue

    def import_woo_specific_orders(self, woo_instance, order_ids):
        """
        This method use for get order queue base specific order ids
        @author : Nilam Kubavat at 11-Aug-2022
        @task ID : 197960
        """
        woo_instance_obj = self.env["woo.instance.ept"]
        start = time.time()

        if isinstance(woo_instance, int):
            woo_instance = woo_instance_obj.browse(woo_instance)
        if not woo_instance.active:
            return False

        params = {"per_page": 100, "page": 1,
                  "order": "asc", "status": ",".join(map(str, woo_instance.import_order_status_ids.mapped("status")))}

        order_data_queue = self.get_order_data_from_specific_ids(params, woo_instance, order_ids=order_ids)
        woo_instance.last_order_import_date = fields.Datetime.now().astimezone(pytz.timezone("UTC")).replace(
            tzinfo=None)
        end = time.time()
        _logger.info("Order queues created in %s seconds.", str(end - start))

        return order_data_queue

    @api.model
    def get_order_data_from_specific_ids(self, params, woo_instance, order_ids):
        """
        This method use for create order queue base specific order ids
        @author : Nilam Kubavat at 11-Aug-2022
        @task ID : 197960
        """
        bus_bus_obj = self.env['bus.bus']

        order_queues = []
        order_data_list = []
        wc_api = woo_instance.woo_connect()

        for order_id in list(order_ids.split(",")):
            try:
                response = wc_api.get('orders/%s' % order_id, params=params)
                if response.status_code != 200:
                    message = (str(response.status_code) + " || " + response.json().get("message", response.reason))
                    self.create_woo_log_lines(message, woo_instance)
                    return False
            except Exception as error:
                raise UserError(_("Something went wrong while importing Orders.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            order_data_list.append(response.json())

        if not order_data_list:
            message = "No orders Found between %s and %s for %s" % (
                params.get('after'), params.get('before'), woo_instance.name)
            # bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
            #                      {'title': 'WooCommerce Connector', 'message': message, "sticky": False,
            #                       "warning": True})
            bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
                                 {'title': _('WooCommerce Connector'), 'message': _(message), "sticky": False,
                                  "warning": True})
            _logger.info(message)

        order_queue_ids = self.create_woo_order_data_queue(woo_instance, order_data_list, order_type="").ids
        order_queues += order_queue_ids

        return order_queues

    def import_all_orders(self, total_pages, params, wc_api, woo_instance, order_type):
        """
        This method is used to import orders if there are more one page data.
        @param order_type: Type of order.
        @param total_pages: Total pages of data.
        @param params: Parameters to pass in API.
        @param wc_api: WC API Object.
        @param woo_instance: Record of Instance.
        @return: All data of orders and Ids of the order data queue.
        @author: Maulik Barad on Date 02-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_queue_ids = []
        for page in range(2, int(total_pages) + 1):
            params["page"] = page
            try:
                response = wc_api.get("orders", params=params)
            except Exception as error:
                raise UserError(_("Something went wrong while importing Orders.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            orders_response = response.json()
            order_queue_ids += self.create_woo_order_data_queue(woo_instance, orders_response, order_type).ids

        return order_queue_ids

    @api.model
    def get_order_data_wc_v3(self, params, woo_instance, order_type):
        """
        This method used to get order response from Woocommerce to Odoo.
        @param : self, params, woo_instance,order_type
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        bus_bus_obj = self.env['bus.bus']

        order_queues = []
        wc_api = woo_instance.woo_connect()

        try:
            response = wc_api.get("orders", params=params)
        except Exception as error:
            raise UserError(_("Something went wrong while importing Orders.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        if response.status_code != 200:
            try:
                message = (str(response.status_code) + " || " + response.json())
            except:
                message = (response.json().get("message", response.reason))
            self.create_woo_log_lines(message, woo_instance)
            return False

        orders_data = response.json()
        if not orders_data:
            message = "No orders Found between %s and %s for %s" % (
                params.get('after'), params.get('before'), woo_instance.name)
            # bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
            #                      {'title': 'WooCommerce Connector', 'message': message, "sticky": False,
            #                       "warning": True})
            bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
                                 {'title': _('WooCommerce Connector'), 'message': _(message), "sticky": False,
                                  "warning": True})
            _logger.info(message)
        if order_type == 'cancelled':
            return orders_data
        order_queue_ids = self.create_woo_order_data_queue(woo_instance, orders_data, order_type).ids
        order_queues += order_queue_ids

        total_pages = response.headers.get("X-WP-TotalPages")
        if int(total_pages) > 1:
            order_queue_ids = self.import_all_orders(total_pages, params, wc_api, woo_instance, order_type)
            order_queues += order_queue_ids

        return order_queues

    @api.model
    def create_or_update_payment_gateway(self, instance, order_response):
        """
        This method used to create a payment gateway in odoo base on code.
        @param : self, instance, order
        @return: payment_gateway
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 3 September 2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        payment_gateway_obj = self.env["woo.payment.gateway"]
        code = order_response.get("payment_method", "")
        name = order_response.get("payment_method_title", "")
        if not code:
            code = "no_payment_method"
            name = "No Payment Method"
        payment_gateway = payment_gateway_obj.search([("code", "=", code), ("woo_instance_id", "=", instance.id)],
                                                     limit=1)
        if not payment_gateway:
            payment_gateway = payment_gateway_obj.create({"code": code, "name": name, "woo_instance_id": instance.id})
        return payment_gateway

    def create_woo_log_lines(self, message, instance, queue_line=None, operation_type="import"):
        """
        Creates log line for the failed queue line.
        @param instance
        @param operation_type
        @param queue_line: Failed queue line.
        @param message: Cause of failure.
        @return: Created log line.
        @author: Maulik Barad on Date 09-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if queue_line:
            queue_line.state = "failed"
        return self.env["common.log.lines.ept"].create_common_log_line_ept(
            operation_type=operation_type, module="woocommerce_ept", woo_instance_id=instance.id, model_name=self._name,
            message=message, woo_order_data_queue_line_id=queue_line and queue_line.id, sale_order_id=self and self.id)

    def update_woo_order_vals(self, order_data, woo_order_number, woo_instance, workflow_config, shipping_partner):
        """
        This method prepares data for updating the order vals.
        @param order_data: Data of order.
        @param woo_order_number: Order number.
        @param woo_instance: Record of Instance.
        @param workflow_config: Record of Financial status.
        @param shipping_partner: Record of Delivery partner.
        @author: Maulik Barad on Date 03-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        payment_gateway_id = workflow_config.woo_payment_gateway_id.id if workflow_config.woo_payment_gateway_id else \
            False
        vals = {
            "note": order_data.get("customer_note"),
            "woo_order_id": order_data.get("id"),
            "woo_order_number": woo_order_number,
            "woo_instance_id": woo_instance.id,
            "team_id": woo_instance.sales_team_id.id if woo_instance.sales_team_id else False,
            "payment_gateway_id": payment_gateway_id,
            "woo_trans_id": order_data.get("transaction_id", ""),
            "woo_customer_ip": order_data.get("customer_ip_address"),
            "picking_policy": workflow_config.woo_auto_workflow_id.picking_policy,
            "auto_workflow_process_id": workflow_config.woo_auto_workflow_id.id,
            "partner_shipping_id": shipping_partner.ids[0],
            "woo_status": order_data.get("status"),
            "client_order_ref": woo_order_number,
            "analytic_account_id": woo_instance.woo_analytic_account_id.id if woo_instance.woo_analytic_account_id else False,
        }
        if self.env["ir.config_parameter"].sudo().get_param("woo_commerce_ept.use_default_terms_and_condition_of_odoo"):
            vals = self.prepare_order_note_with_customer_note(vals)
        return vals

    def get_order_link(self):
        """
        This method is used to redirect Woocommerce order in WooCommerce Store.
        @author: Meera Sidapara on Date 17-May-2022.
        @Task: 189557 - WC order link
        """
        self.ensure_one()
        order_link = "%s/wp-admin/post.php?post=%s&action=edit" % (self.woo_instance_id.woo_host, self.woo_order_id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': order_link,
        }

    def prepare_woo_order_vals(self, order_data, woo_instance, partner, billing_partner, shipping_partner,
                               workflow_config):
        """
        This method used to prepare a order vals.
        @param : self, order_data, woo_instance, partner, billing_partner, shipping_partner, workflow_config
        @return: woo_order_vals
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_date = order_data.get("date_created_gmt")
        price_list = self.find_woo_order_pricelist(order_data, woo_instance)

        woo_order_vals = {
            "partner_id": partner.ids[0],
            "partner_shipping_id": shipping_partner.ids[0],
            "partner_invoice_id": billing_partner.ids[0],
            "warehouse_id": woo_instance.woo_warehouse_id.id,
            "company_id": woo_instance.company_id.id,
            "pricelist_id": price_list.id,
            "payment_term_id": woo_instance.woo_payment_term_id.id,
            "date_order": order_date.replace("T", " "),
            "state": "draft"
        }

        woo_order_number = order_data.get("number")

        if not woo_instance.custom_order_prefix:
            if woo_instance.order_prefix:
                name = "%s%s" % (woo_instance.order_prefix, woo_order_number)
            else:
                name = woo_order_number
            woo_order_vals.update({"name": name})

        updated_vals = self.update_woo_order_vals(order_data, woo_order_number, woo_instance, workflow_config,
                                                  shipping_partner)
        woo_order_vals.update(updated_vals)
        return woo_order_vals

    def find_woo_order_pricelist(self, order_data, woo_instance):
        """
        This method use to check the order price list exists or not in odoo base on the order currency..
        @param : order_data, woo_instance
        @return: price_list
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_pricelist_obj = self.env['product.pricelist']
        currency_obj = self.env["res.currency"]
        order_currency = order_data.get("currency")

        currency_id = currency_obj.search([('name', '=', order_currency)], limit=1)
        if not currency_id:
            currency_id = currency_obj.search([('name', '=', order_currency), ('active', '=', False)], limit=1)
            currency_id.write({'active': True})

        if woo_instance.woo_pricelist_id.currency_id.id == currency_id.id:
            return woo_instance.woo_pricelist_id
        price_list = product_pricelist_obj.search([('currency_id', '=', currency_id.id),
                                                   ("company_id", "=", woo_instance.company_id.id)], limit=1)
        if price_list:
            return price_list

        price_list = product_pricelist_obj.create({'name': currency_id.name, 'currency_id': currency_id.id,
                                                   'company_id': woo_instance.company_id.id})
        return price_list

    @api.model
    def create_woo_tax(self, tax, tax_included, woo_instance):
        """
        Creates tax in odoo as woo tax.
        @param woo_instance:
        @param tax: Dictionary of woo tax.
        @param tax_included: If tax is included or not in price of product in woo.
        @author: Maulik Barad on Date 20-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        account_tax_obj = self.env["account.tax"]
        title = tax["name"]
        rate = tax["rate"]

        if tax_included:
            name = "%s (%s %% included)" % (title, rate)
        else:
            name = "%s (%s %% excluded)" % (title, rate)

        odoo_tax = account_tax_obj.create({"name": name, "amount": float(rate),
                                           "type_tax_use": "sale", "price_include": tax_included,
                                           "company_id": woo_instance.company_id.id})

        odoo_tax.mapped("invoice_repartition_line_ids").write({"account_id": woo_instance.invoice_tax_account_id.id})
        odoo_tax.mapped("refund_repartition_line_ids").write({"account_id": woo_instance.credit_note_tax_account_id.id})

        return odoo_tax

    @api.model
    def apply_woo_taxes(self, taxes, tax_included, woo_instance):
        """
        Finds matching odoo taxes with woo taxes' rates.
        If no matching tax found in odoo, then creates a new one.
        @author: Maulik Barad on Date 20-Nov-2019.
        @param taxes: List of Dictionaries of woo taxes.
        @param tax_included: If tax is included or not in price of product in woo.
        @param woo_instance: Instance of Woo.
        @return: Taxes' ids.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        tax_obj = self.env["account.tax"]
        tax_ids = []
        for tax in taxes:
            title = tax.get("name")
            rate = float(tax.get("rate"))
            if tax_included:
                name = "%s (%s %% included)" % (title, rate)
            else:
                name = "%s (%s %% excluded)" % (title, rate)
            tax_id = tax_obj.search([('name', '=ilike', name),
                                     ("price_include", "=", tax_included),
                                     ("type_tax_use", "=", "sale"), ("amount", "=", rate),
                                     ("company_id", "=", woo_instance.company_id.id)], limit=1)
            if not tax_id:
                tax_id = tax_obj.search([("price_include", "=", tax_included),
                                         ("type_tax_use", "=", "sale"), ("amount", "=", rate),
                                         ("company_id", "=", woo_instance.company_id.id)], limit=1)
            if not tax_id:
                tax_id = self.sudo().create_woo_tax(tax, tax_included, woo_instance)
                _logger.info('New tax %s created in Odoo.', tax_id.name)
            if tax_id:
                tax_ids.append(tax_id.id)

        return tax_ids

    @api.model
    def create_woo_order_line(self, line_id, product, quantity, price, taxes, tax_included, woo_instance,
                              is_shipping=False):
        """
        This method used to create a sale order line.
        @param : self, line_id, product, quantity, price, taxes, tax_included,woo_instance,is_shipping=False
        @return: sale order line
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        sale_line_obj = self.env["sale.order.line"]
        rounding = woo_instance.tax_rounding_method != 'round_globally'
        woo_so_line_vals = {
            "name": product.name,
            "product_id": product.id,
            "product_uom": product.uom_id.id if product.uom_id else False,
            "order_id": self.id,
            "product_uom_qty": quantity,
            "price_unit": price,
            "company_id": woo_instance.company_id.id,
            "state": "draft"
        }

        if woo_instance.apply_tax == "create_woo_tax":
            tax_ids = self.apply_woo_taxes(taxes, tax_included, woo_instance)
            woo_so_line_vals.update({"tax_id": [(6, 0, tax_ids)]})

        # woo_analytic_tag_ids = woo_instance.woo_analytic_tag_ids.ids
        # , "analytic_tag_ids": [(6, 0, woo_analytic_tag_ids)]
        woo_so_line_vals.update(
            {"woo_line_id": line_id, "is_delivery": is_shipping})
        sale_order_line = sale_line_obj.create(woo_so_line_vals)
        sale_order_line.order_id.with_context(round=rounding).write({'woo_instance_id': woo_instance.id})
        return sale_order_line

    def get_woo_unit_price(self, tax_included, quantity, subtotal, subtotal_tax):
        """
        This method computes the unit price of the product.
        @param tax_included: Tax is included or not.
        @param quantity: Total qty of product in order line.
        @param subtotal: Total amount of order line.
        @param subtotal_tax: Total tax of order line.
        @author: Maulik Barad on Date 03-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        actual_unit_price = 0.0
        if subtotal and quantity:
            if tax_included:
                actual_unit_price = (subtotal + subtotal_tax) / quantity
            else:
                actual_unit_price = subtotal / quantity
        return actual_unit_price

    def woo_create_discount_line(self, order_line, tax_included, woo_instance, taxes, order_line_id):
        """
        This method creates discount line for a order line.
        @param order_line: Data of order line.
        @param tax_included: Tax is included or excluded.
        @param woo_instance: Record of Instance.
        @param taxes: Ids of taxes.
        @param order_line_id: Order line for which we are creating the discount line.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        discount_line = False
        line_discount = float(order_line.get('subtotal')) - float(order_line.get('total')) or 0
        if line_discount > 0:
            if tax_included:
                tax_discount = float(order_line.get("subtotal_tax", 0.0)) - float(order_line.get("total_tax", 0.0)) or 0
                line_discount = tax_discount + line_discount
            discount_line = self.create_woo_order_line(False, woo_instance.discount_product_id, 1, line_discount * -1,
                                                       taxes, tax_included, woo_instance)

            discount_line.write({'name': 'Discount for ' + order_line_id.name})
            if woo_instance.apply_tax == 'odoo_tax':
                discount_line.tax_id = order_line_id.tax_id
        return discount_line

    @api.model
    def create_woo_sale_order_lines(self, queue_line, order_data, tax_included, instance, woo_taxes):
        """
        Checks for products and creates sale order lines.
        @param instance:
        @param order_data: Data of order.
        @param queue_line: The queue line.
        @param woo_taxes: Dictionary of woo taxes.
        @param tax_included: If tax is included or not in price of product.
        @return: Created sale order lines.
        @author: Maulik Barad on Date 13-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_lines_list = []
        for order_line in order_data.get("line_items"):
            taxes = []
            woo_product = self.find_or_create_woo_product(queue_line, order_line, instance)
            if not woo_product:
                message = "Product [%s][%s] not found for Order %s" % (
                    order_line.get("sku"), order_line.get("name"), order_data.get('number'))
                self.create_woo_log_lines(message, instance, queue_line)
                return False
            product = woo_product.product_id
            quantity = float(order_line.get("quantity"))

            actual_unit_price = self.get_woo_unit_price(tax_included, quantity, float(order_line.get("subtotal")),
                                                        float(order_line.get("subtotal_tax")))

            if instance.apply_tax == "create_woo_tax":
                for tax in order_line.get("taxes"):
                    if not tax.get('total'):
                        continue
                    taxes.append(woo_taxes.get(tax['id']))

            order_line_id = self.create_woo_order_line(order_line.get("id"), product, order_line.get("quantity"),
                                                       actual_unit_price, taxes, tax_included, instance)
            order_lines_list.append(order_line_id)

            self.woo_create_discount_line(order_line, tax_included, instance, taxes, order_line_id)
            _logger.info("Sale order line is created for order %s.", self.name)
        return order_lines_list

    @api.model
    def find_or_create_woo_product(self, queue_line, order_line, woo_instance):
        """
        Searches for the product and return it.
        If it is not found and configuration is set to import product, it will collect data and
        create the product.
        @param woo_instance:
        @author: Maulik Barad on Date 12-Nov-2019.
        @param queue_line: Order data queue.
        @param order_line: Order line.
        @return: Woo product if found, otherwise blank object.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_template_obj = self.env["woo.product.template.ept"]

        # Checks for the product. If found then returns it.
        woo_product_id = order_line.get("variation_id") if order_line.get("variation_id") else order_line.get(
            "product_id")
        woo_product, odoo_product = \
            woo_product_template_obj.search_odoo_product_variant(woo_instance, order_line.get("sku"),
                                                                 woo_product_id)

        if not woo_product and woo_instance.auto_import_product or odoo_product:
            # If product not found and configuration is set to import product, then creates it.
            if not order_line.get("product_id"):
                _logger.info('Product id not found in sale order line response')
                return woo_product
            product_data = woo_product_template_obj.get_products_from_woo_v1_v2_v3(woo_instance,
                                                                                   order_line.get("product_id"))
            woo_product_template_obj.sync_products(product_data, woo_instance, order_queue_line=queue_line)
            woo_product = woo_product_template_obj.search_odoo_product_variant(woo_instance, order_line.get("sku"),
                                                                               woo_product_id)[0]
        return woo_product

    @api.model
    def get_tax_ids(self, woo_instance, tax_id, woo_taxes):
        """
        Fetches all taxes for the woo instance.
        @param woo_taxes:
        @param tax_id:
        @author: Maulik Barad on Date 20-Nov-2019.
        @param woo_instance: Woo Instance.
        @return: Tax data if no issue was there, otherwise the error message.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = woo_instance.woo_connect()
        params = {"_fields": "id,name,rate"}
        try:
            response = wc_api.get("taxes/%s" % tax_id, params=params)
            if response.status_code != 200:
                return response.json().get("message", response.reason)
            tax_data = response.json()
        except Exception:
            return woo_taxes
        woo_taxes.update({tax_data["id"]: tax_data})
        return woo_taxes

    @api.model
    def verify_order_for_payment_method(self, order_data):
        """
        Check order for full discount, when there is no payment gateway found.
        @author: Maulik Barad on Date 21-May-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        total_discount = 0

        total = order_data.get("total")
        if order_data.get("coupon_lines"):
            total_discount = order_data.get("discount_total")

        if float(total) == 0 and float(total_discount) > 0:
            return True
        return False

    def get_status_code(self, order_data):
        """
        Get Order Status Dictionary.
        :param order_data: Order status received from Woocommerce.
        :return: Order Status dictionary
        """
        status_code = ''
        order_status = order_data.get('status')
        if order_status == "pending":
            status_code = 'pending'
        elif order_status == "processing":
            status_code = 'processing'
        elif order_status == "on-hold":
            status_code = 'on-hold'
        elif order_status == "completed":
            status_code = 'completed'
        return status_code

    def woo_prepare_tax_data(self, tax_line_data, rate_percent, woo_taxes, queue_line, woo_instance, order_data):
        """
        This method is used to check if the rate of tax is available in order, otherwise get tax data from WooCommerce.
        @param order_data:
        @param woo_instance:
        @param queue_line:
        @param tax_line_data: Tax data of a order.
        @param rate_percent: If the rate available in data.
        @param woo_taxes: Null at the first time and then already collected taxes for orders.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for order_tax in tax_line_data:
            if order_tax.get('rate_id') in woo_taxes.keys():
                continue
            if not rate_percent:
                if 'rate_percent' in order_tax.keys():
                    rate_percent = "available"
                else:
                    rate_percent = "not available"

            if rate_percent == "available":
                woo_taxes.update({order_tax.get('rate_id'): {"name": order_tax.get('label'),
                                                             "rate": order_tax.get('rate_percent')}})
            elif rate_percent == "not available":
                woo_taxes = self.get_tax_ids(woo_instance, order_tax.get('rate_id'), woo_taxes)
                if isinstance(woo_taxes, str):
                    message = "Order #%s not imported due to missing tax information.\nTax rate id: %s and Tax " \
                              "label: %s is deleted after order creation in WooCommerce " \
                              "store." % (order_data.get('number'), order_tax.get('rate_id'), order_tax.get('label'))
                    self.create_woo_log_lines(message, woo_instance, queue_line)
                    return False
        return woo_taxes

    def woo_prepare_order_data(self, is_process_from_queue, queue_line):
        """
        This method defines the order_data and queue_line.
        @param is_process_from_queue: If queue is processing from the queue.
        @param queue_line: Queue line or order data.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if is_process_from_queue:
            order_data = ast.literal_eval(queue_line.order_data)
            queue_line.processed_at = fields.Datetime.now()
        else:
            order_data = queue_line
            queue_line = False

        return order_data, queue_line

    @api.model
    def create_woo_orders(self, queue_lines):
        """
        This method used to create a order in Odoo base on the response.
        @param : self, queue_lines
        @return: new_orders
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        new_orders = self
        woo_instance = False
        commit_count = 0
        woo_taxes = {}
        rate_percent = ""

        for queue_line in queue_lines:
            commit_count += 1
            if commit_count == 5:
                queue_line.order_data_queue_id.is_process_queue = True
                self._cr.commit()
                commit_count = 0
            if woo_instance != queue_line.instance_id:
                woo_instance = queue_line.instance_id
                woo_taxes = {}

            order_data = ast.literal_eval(queue_line.order_data)
            queue_line.processed_at = fields.Datetime.now()
            _logger.info("Started processing order %s." % order_data.get("number"))

            if str(woo_instance.import_order_after_date) > order_data.get("date_created_gmt"):
                message = "Order %s is not imported in Odoo due to configuration mismatch.\n Received order date is " \
                          "%s. \n Please check the order after date in WooCommerce configuration." \
                          % (order_data.get('number'), order_data.get("date_created_gmt"))
                _logger.info(message)
                self.create_woo_log_lines(message, woo_instance, queue_line)
                continue

            existing_order = self.search_existing_woo_order(woo_instance, order_data)

            if existing_order:
                queue_line.state = "done"
                queue_line.order_data = False
                _logger.info("Sale order %s already exists." % order_data.get("number"))
                continue

            # WooCommerce Meta Mapping for import Unshipped/Shipped Orders
            woo_operation = 'import_completed_orders' if queue_line.order_data_queue_id.queue_type == 'shipped' else \
                'import_unshipped_orders'
            meta_mapping_ids = woo_instance.meta_mapping_ids.filtered(lambda meta: meta.woo_operation == woo_operation)
            operation_type = "import"

            workflow_config = self.create_update_payment_gateway_and_workflow(order_data, woo_instance, queue_line)
            if not workflow_config:
                continue

            partner, billing_partner, shipping_partner = self.woo_order_billing_shipping_partner(order_data,
                                                                                                 woo_instance,
                                                                                                 queue_line)
            if not partner:
                continue

            if woo_instance.apply_tax == "create_woo_tax":
                woo_taxes = self.woo_prepare_tax_data(order_data.get('tax_lines'), rate_percent, woo_taxes, queue_line,
                                                      woo_instance, order_data)
                if isinstance(woo_taxes, bool):
                    continue

            if partner and meta_mapping_ids and meta_mapping_ids.filtered(
                    lambda meta: meta.model_id.model == partner._name):
                woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(order_data, operation_type,
                                                                                          partner)

            order_values = self.prepare_woo_order_vals(order_data, woo_instance, partner, billing_partner,
                                                       shipping_partner, workflow_config)
            sale_order = self.create(order_values)
            tax_included = order_data.get("prices_include_tax")

            order_lines = sale_order.create_woo_sale_order_lines(queue_line, order_data, tax_included, woo_instance,
                                                                 woo_taxes)
            if not order_lines:
                sale_order.unlink()
                queue_line.state = "failed"
                continue

            sale_order.woo_create_extra_lines(order_data, tax_included, woo_taxes)

            if meta_mapping_ids and meta_mapping_ids.filtered(lambda meta: meta.model_id.model == self._name):
                woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(order_data, operation_type,
                                                                                          sale_order)
            # if sale_order.woo_status == 'completed':
            #     sale_order.auto_workflow_process_id.shipped_order_workflow_ept(sale_order)
            # else:
            #     sale_order.process_orders_and_invoices_ept()

            if order_data.get('status') == 'completed':
                sale_order.auto_workflow_process_id.shipped_order_workflow_ept(sale_order)
            else:
                sale_order.auto_workflow_process_id.auto_workflow_process_ept(sale_order.auto_workflow_process_id.id,
                                                                              [sale_order.id])

            service_product = [product for product in sale_order.order_line.product_id if
                               product.detailed_type == 'service']
            sale_order.is_service_woo_order = bool(service_product)

            if meta_mapping_ids and meta_mapping_ids.filtered(
                    lambda meta: meta.model_id.model == sale_order.picking_ids._name):
                woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(order_data, operation_type,
                                                                                          sale_order.picking_ids)

            new_orders += sale_order
            queue_line.write({"sale_order_id": sale_order.id, "state": "done", "order_data": False})
            message = "Sale order: %s and Woo order number: %s is created." % (sale_order.name,
                                                                               order_data.get('number'))
            _logger.info(message)
        queue_lines.order_data_queue_id.is_process_queue = False
        return new_orders

    def search_existing_woo_order(self, woo_instance, order_data):
        """
        This method used to search existing Woo order in Odoo.
        @param : self,woo_instance,order_data
        @return: existing_order
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        existing_order = self.search([("woo_instance_id", "=", woo_instance.id),
                                      ("woo_order_id", "=", order_data.get("id")),
                                      ("woo_order_number", "=", order_data.get("number"))], limit=1)
        if not existing_order:
            existing_order = self.search([("woo_instance_id", '=', woo_instance.id),
                                          ("client_order_ref", "=", order_data.get("number"))], limit=1)
        return existing_order

    def woo_create_extra_lines(self, order_data, tax_included, woo_taxes):
        """
        Creates shipping lines, fee lines and coupon for the order.
        @param order_data: Data of the order.
        @param tax_included: True If tax is included.
        @param woo_taxes: List of taxes.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        self.create_woo_shipping_line(order_data, tax_included, woo_taxes)
        self.create_woo_fee_line(order_data, tax_included, woo_taxes)
        self.set_coupon_in_sale_order(order_data)
        return True

    def get_financial_status(self, order_data):
        """
        This method defines the financial status from transaction, date_paid, payment method and status of the order.
        @param order_data: Data of order.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if order_data.get("transaction_id"):
            financial_status = "paid"
        elif order_data.get("date_paid") and order_data.get("payment_method") != "cod" and order_data.get(
                "status") == "processing":
            financial_status = "paid"
        else:
            financial_status = "not_paid"
        return financial_status

    def create_update_payment_gateway_and_workflow(self, order_data, woo_instance, queue_line):
        """
        This method used to search or create payment gateway and workflow base on the order response.
        @param : self,order_data,woo_instance,queue_line
        @return: payment_gateway, workflow_config
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        sale_auto_workflow_obj = self.env["woo.sale.auto.workflow.configuration"]
        woo_payment_gateway_obj = self.env['woo.payment.gateway']

        financial_status = self.get_financial_status(order_data)
        payment_gateway = self.create_or_update_payment_gateway(woo_instance, order_data)
        no_payment_gateway = self.verify_order_for_payment_method(order_data)
        status_code = self.get_status_code(order_data)

        if payment_gateway:
            workflow_config = sale_auto_workflow_obj.search([("woo_instance_id", "=", woo_instance.id),
                                                             ("woo_financial_status", "=", financial_status),
                                                             ("woo_payment_gateway_id", "=", payment_gateway.id),
                                                             ('woo_order_status', '=', status_code)],
                                                            limit=1)
        elif no_payment_gateway:
            payment_gateway = woo_payment_gateway_obj.search([("code", "=", "no_payment_method"),
                                                              ("woo_instance_id", "=", woo_instance.id)])
            workflow_config = sale_auto_workflow_obj.search([("woo_instance_id", "=", woo_instance.id),
                                                             ("woo_financial_status", "=", financial_status),
                                                             ("woo_payment_gateway_id", "=", payment_gateway.id),
                                                             ('woo_order_status', '=', status_code)],
                                                            limit=1)
        else:
            message = """- System could not find the payment gateway response from WooCommerce store.
            - The response received from Woocommerce store was Empty. Woo Order number: %s""" % order_data.get("number")
            self.create_woo_log_lines(message, woo_instance, queue_line)
            return False

        if not workflow_config:
            message = """- Automatic order process workflow configuration not found for this order %s.
            - System tries to find the workflow based on combination of Payment Gateway(such as Manual, Credit Card, 
            Paypal etc.) and Financial Status(such as Paid,Pending,Authorised etc.) and Order Status(such as Processing,Pending Payment,On hold,Completed etc.).
            - In this order Payment Gateway is %s and Financial Status is %s and Order Status is %s.
            - You can configure the Automatic order process workflow under the menu Woocommerce > Configuration > 
            Financial Status.""" % (
                order_data.get("number"), order_data.get("payment_method_title", ""), financial_status, status_code)
            self.create_woo_log_lines(message, woo_instance, queue_line)
            return False
        workflow = workflow_config.woo_auto_workflow_id

        if not workflow.picking_policy:
            message = """- Picking policy decides how the products will be delivered, 'Deliver all at once' or
            'Deliver each when available'.
            - System found %s Auto Workflow, but couldn't find configuration about picking policy under it.
            - Please review the Auto workflow configuration here :
            WooCommerce -> Configuration -> Sales Auto Workflow """ % workflow.name
            self.create_woo_log_lines(message, woo_instance, queue_line)
            return False
        return workflow_config

    def woo_order_billing_shipping_partner(self, order_data, woo_instance, queue_line):
        """
        This method used to call a child method of billing and shipping partner.
        @param : self, order_data, woo_instance, queue_line,is_process_from_queue
        @return: partner, shipping_partner
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        partner_obj = self.env['res.partner']
        woo_partner_obj = self.env['woo.res.partner.ept']
        partner = False

        if not order_data.get('billing').get('first_name') and not order_data.get('billing').get('last_name'):
            message = "- System could not find the billing address in WooCommerce order : %s" % (order_data.get("id"))
            self.create_woo_log_lines(message, woo_instance, queue_line)
            return False, False, False

        # woo_partner = woo_partner_obj.search([("woo_customer_id", "=", order_data.get('customer_id')),
        #                                       ("woo_instance_id", "=", woo_instance.id)], limit=1)
        if order_data.get('customer_id') != 0:
            woo_partner = woo_partner_obj.find_woo_customer(woo_instance, order_data.get('customer_id'))
        else:
            woo_partner = False

        if woo_partner:
            partner = woo_partner

        billing_partner = partner_obj.woo_create_or_update_customer(order_data.get("billing"), woo_instance, partner,
                                                                    'invoice', order_data.get('customer_id', False))
        if not partner:
            partner = billing_partner
        shipping_partner = partner_obj.woo_create_or_update_customer(order_data.get("shipping"), woo_instance, partner,
                                                                     'delivery')
        if not shipping_partner:
            shipping_partner = partner

        return partner, billing_partner, shipping_partner

    def find_or_create_delivery_carrier(self, shipping_product_id, delivery_method, shipping_line):
        """
        Find or create the carrier for the shipping line.
        @param shipping_product_id: Default Product for setting in carrier.
        @param delivery_method: Method name from WooCommerce.
        @param shipping_line: Data of shipping line.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        delivery_carrier_obj = self.env["delivery.carrier"]
        shipping_method_obj = self.env['woo.shipping.method']
        carrier = delivery_carrier_obj.search([("woo_code", "=", shipping_line.get('method_id'))], limit=1)
        woo_shipping_method = shipping_method_obj.search([("code", "ilike", shipping_line.get('method_id'))],
                                                         limit=1)
        if not carrier:
            carrier = delivery_carrier_obj.search([("name", "=", delivery_method)], limit=1)
        if not carrier:
            carrier = delivery_carrier_obj.search(["|", ("name", "ilike", delivery_method),
                                                   ("woo_code", "ilike", shipping_line.get('method_id'))], limit=1)
        if not carrier:
            carrier = delivery_carrier_obj.create({"name": delivery_method, "woo_code": shipping_line.get('method_id'),
                                                   "woo_shipping_method_id": woo_shipping_method.id,
                                                   "product_id": shipping_product_id.id})
        return carrier

    def create_woo_shipping_line(self, order_data, tax_included, woo_taxes):
        """
        This method used to create a shipping line base on the shipping response in the order.
        @param : self, order_data, sale_order, tax_included, woo_taxes
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        shipping_product_id = self.woo_instance_id.shipping_product_id

        for shipping_line in order_data.get("shipping_lines"):
            delivery_method = shipping_line.get("method_title")
            if delivery_method:
                carrier = self.find_or_create_delivery_carrier(shipping_product_id, delivery_method, shipping_line)
                shipping_product = carrier.product_id
                self.write({"carrier_id": carrier.id})

                taxes = []
                if self.woo_instance_id.apply_tax == "create_woo_tax":
                    taxes = [woo_taxes.get(tax["id"]) for tax in shipping_line.get("taxes") if tax.get("total")]

                total_shipping = float(shipping_line.get("total", 0.0))
                if tax_included:
                    total_shipping += float(shipping_line.get("total_tax", 0.0))
                self.create_woo_order_line(shipping_line.get("id"), shipping_product, 1, total_shipping, taxes,
                                           tax_included, self.woo_instance_id, True)
                _logger.info("Shipping line is created for the sale order: %s.", self.name)
        return True

    def create_woo_fee_line(self, order_data, tax_included, woo_taxes):
        """
        This method used to create a fee line base on the fee response in the order.
        @param : self, order_data, tax_included, woo_taxes, sale_order
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for fee_line in order_data.get("fee_lines"):
            if tax_included:
                total_fee = float(fee_line.get("total", 0.0)) + float(fee_line.get("total_tax", 0.0))
            else:
                total_fee = float(fee_line.get("total", 0.0))
            if total_fee:
                taxes = []
                if self.woo_instance_id.apply_tax == "create_woo_tax":
                    taxes = [woo_taxes.get(tax["id"]) for tax in fee_line.get("taxes") if tax.get("total")]

                self.create_woo_order_line(fee_line.get("id"), self.woo_instance_id.fee_product_id, 1, total_fee, taxes,
                                           tax_included, self.woo_instance_id)
                _logger.info("Fee line is created for the sale order %s.", self.name)
        return True

    def set_coupon_in_sale_order(self, order_data):
        """
        This method is used to set the coupon in the order, it will set coupon if the coupon is already synced in odoo.
        @param : self, order_data
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 4 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_coupon_obj = self.env["woo.coupons.ept"]
        woo_coupons = []
        for coupon_line in order_data.get("coupon_lines"):
            coupon_code = coupon_line["code"]
            coupon = woo_coupon_obj.search([("code", "=", coupon_code),
                                            ("woo_instance_id", "=", self.woo_instance_id.id)])
            if coupon:
                woo_coupons.append(coupon.id)
                _logger.info("Coupon %s added.", coupon_code)
            else:
                message = "The coupon {0} could not be added as it is not imported in odoo.".format(coupon_line["code"])
                self.message_post(body=message)
                _logger.info("Coupon %s not found.", coupon_code)
        self.woo_coupon_ids = [(6, 0, woo_coupons)]
        return True

    def import_cancel_order_cron_action(self, instance):
        """
        This method is used to import cancel orders from the auto-import cron job.
        """
        instance_obj = self.env['woo.instance.ept']
        if isinstance(instance, int):
            instance = instance_obj.browse(instance)
        if not instance.active:
            return False
        if instance.last_cancel_order_import_date:
            from_date = instance.last_cancel_order_import_date - timedelta(days=1)
        else:
            from_date = fields.Datetime.now() - timedelta(days=1)
        to_date = datetime.now()
        if not from_date:
            from_date = to_date - timedelta(3)
        self.import_woo_cancel_order(instance, from_date, to_date)
        return True

    def import_woo_cancel_order(self, instance, from_date, to_date):
        """ This method is used if Woo orders imported in odoo and after Woo store in some orders are canceled
            then this method cancel imported orders and created a log note.
            @param : instance,from_date,to_date
            @return: True
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 02 April 2022.
            Task_id: 186892
        """
        order_ids = self.import_woo_orders(instance, from_date, to_date, order_type="cancelled")
        for order_data in order_ids:
            if order_data.get('status') == "cancelled":
                sale_order = self.search_existing_woo_order(instance, order_data)
                if sale_order and sale_order.state != 'cancel':
                    sale_order.cancel_woo_order()
                    sale_order.write({'canceled_in_woo': True, "woo_status": "cancelled"})
        return True

    @api.model
    def update_woo_order_status(self, woo_instance):
        """
        Updates order's status in WooCommerce.
        @author: Maulik Barad on Date 14-Nov-2019.
        @param woo_instance: Woo Instance.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        instance_obj = self.env["woo.instance.ept"]
        log_lines = []
        woo_order_ids = []
        if isinstance(woo_instance, int):
            woo_instance = instance_obj.browse(woo_instance)
        if not woo_instance.active:
            return False
        wc_api = woo_instance.woo_connect()
        sales_orders = self.search([("warehouse_id", "=", woo_instance.woo_warehouse_id.id),
                                    ("woo_order_id", "!=", False), ("woo_instance_id", "=", woo_instance.id),
                                    ("state", "in", ["sale", "done"]), ("woo_status", "!=", 'completed')])

        for sale_order in sales_orders:
            if sale_order.updated_in_woo:
                continue

            pickings = sale_order.picking_ids.filtered(lambda x:
                                                       x.location_dest_id.usage == "customer" and x.state
                                                       != "cancel" and not x.updated_in_woo)
            _logger.info("Start Order update status for Order : %s", sale_order.name)
            if all(state == 'done' for state in pickings.mapped("state")):
                woo_order_ids.append({"id": int(sale_order.woo_order_id), "status": "completed", })
            elif not pickings and sale_order.state == "sale":
                # When all products are of service type.
                woo_order_ids.append({"id": int(sale_order.woo_order_id), "status": "completed"})
            else:
                continue
            # WooCommerce Meta Mapping for Update Order shipping status
            woo_operation = 'is_update_order_status'
            meta_mapping_ids = woo_instance.meta_mapping_ids.filtered(
                lambda meta: meta.woo_operation == woo_operation)
            if meta_mapping_ids and meta_mapping_ids.filtered(
                    lambda meta: meta.model_id.model == self._name):
                record = sale_order
                woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(woo_order_ids, "export",
                                                                                          record)

            if meta_mapping_ids and meta_mapping_ids.filtered(
                    lambda meta: meta.model_id.model == pickings._name):
                record = pickings.filtered(lambda picking: picking.state == 'done')
                woo_instance.with_context(woo_operation=woo_operation).meta_field_mapping(woo_order_ids, "export",
                                                                                          record)

        for woo_orders in split_every(100, woo_order_ids):
            log_line_id = self.update_order_status_in_batch(woo_orders, wc_api, woo_instance)
            if log_line_id:
                if isinstance(log_line_id, list):
                    log_lines += log_line_id
                else:
                    log_lines.append(log_line_id)
            self._cr.commit()

        if log_lines and woo_instance.is_create_schedule_activity:
            self.woo_create_schedule_activity_against_logline(log_lines, woo_instance)
        return True

    def update_order_status_in_batch(self, woo_orders, wc_api, woo_instance):
        """
        This method is used to update orders in the batch from Odoo to the Woocommerce store.
        :param woo_orders: list of dictionary with woo order id and status.
        :param wc_api: Object of Woocommerce rest API.
        :param woo_instance: Browsable record of instance.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 26 November 2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        try:
            response = wc_api.post('orders/batch', {'update': list(woo_orders)})
        except Exception as error:
            raise UserError(_("Something went wrong while Updating Orders' Status.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))
        if response.status_code not in [200, 201]:
            _logger.info("Could not update status batch")
            message = "Error in updating order status batch"
            log_line = self.create_woo_log_lines(message, woo_instance, operation_type="export")
            return log_line.id
        update_order_list = [order_res.get('id') for order_res in response.json().get('update', {}) if
                             not order_res.get('error')]
        log_lines = []
        for order in woo_orders:
            if order.get('id') not in update_order_list:
                message = 'Could not update order status of Woo order id %s' % order.get('id')
                _logger.info(message)
                log_line = self.create_woo_log_lines(message, woo_instance, operation_type="export")
                log_lines.append(log_line.id)
                continue
            sale_order = self.search([("woo_order_id", "=", order.get('id')), ("woo_instance_id", "=",
                                                                               woo_instance.id)], limit=1)
            if sale_order:
                sale_order.picking_ids.write({"updated_in_woo": True})
                sale_order.woo_status = "completed"

        if log_lines:
            return log_lines

        return False

    def cancel_in_woo(self):
        """
        This method used to open a wizard to cancel order in WooCommerce.
        @return: action
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 23-11-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        view = self.env.ref('woo_commerce_ept.view_woo_cancel_order_wizard')
        context = dict(self._context)
        context.update({'active_model': 'sale.order', 'active_id': self.id, 'active_ids': self.ids})
        return {
            'name': _('Cancel Order In WooCommerce'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'woo.cancel.order.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }

    @api.model
    def process_order_via_webhook(self, order_data, instance, update_order=False):
        """
        Creates order data queue and process it.
        This method is for order imported via create and update webhook.
        @param update_order: If this queue line is for updating the order via webhook.
        @author: Maulik Barad on Date 30-Dec-2019.
        @param order_data: Dictionary of order's data.
        @param instance: Instance of Woo.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        order_queue = woo_order_data_queue_obj = self.env["woo.order.data.queue.ept"]
        order_number = order_data.get('number')
        order_status = order_data.get("status")
        if update_order:
            order_queue = woo_order_data_queue_obj.search([
                ('instance_id', '=', instance.id), ('state', '=', 'draft'), ('created_by', '=', 'webhook'),
                ("queue_type", "=", "shipped" if order_status else "unshipped")], limit=1)
            if order_queue:
                order_queue.create_woo_data_queue_lines([order_data])
                _logger.info("Added order %s in existing order queue %s.", order_number, order_queue.display_name)

        if not order_queue:
            order_queue = self.create_woo_order_data_queue(instance, [order_data], order_status, "webhook")
            _logger.info("Created Order Queue : %s.", order_queue.display_name)

        if len(order_queue.order_data_queue_line_ids) >= 50 or not update_order:
            order_queue.order_data_queue_line_ids.process_order_queue_line(update_order)
        return True

    def woo_change_shipping_partner(self, order_data, woo_instance, queue_line):
        """
        This method is used to update the shipping partner in Order and Picking.
        @param queue_line:
        @param order_data: Data of the order.
        @param woo_instance: Record of the instance.
        @author: Maulik Barad on Date 04-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        shipping_partner = self.partner_shipping_id
        updated_shipping_partner = self.woo_order_billing_shipping_partner(order_data, woo_instance, queue_line)[2]
        if updated_shipping_partner and updated_shipping_partner.id != shipping_partner.id:
            self.write({'partner_shipping_id': updated_shipping_partner.id})
            picking = self.picking_ids.filtered(
                lambda x: x.picking_type_code == 'outgoing' and x.state not in ['cancel', 'done'])
            if picking:
                picking.write({'partner_id': updated_shipping_partner.id})
        return True

    @api.model
    def update_woo_order(self, queue_lines, instance):
        """
        This method will update order as per its status got from WooCommerce.
        @param instance:
        @author: Maulik Barad on Date 31-Dec-2019.
        @param queue_lines: Order Data Queue Line.
        @return: Updated Sale order.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        orders = []
        for queue_line in queue_lines:
            message = ""
            order_data = ast.literal_eval(queue_line.order_data)
            queue_line.processed_at = fields.Datetime.now()
            woo_status = order_data.get("status")
            order = self.search([("woo_instance_id", "=", instance.id),
                                 ("woo_order_id", "=", order_data.get("id"))])

            if not order:
                order = self.create_woo_orders(queue_line)
                if not order:
                    return orders

            if woo_status != "cancelled":
                order.woo_change_shipping_partner(order_data, instance, queue_line)

            if woo_status == "cancelled" and order.state != "cancel":
                cancelled = order.cancel_woo_order()
                if not cancelled:
                    message = "System can not cancel the order %s as one of the picking is in the done state." % \
                              order.name
            elif woo_status == "refunded":
                refunded = order.create_woo_refund(order_data.get("refunds"))
                if refunded[0] == 4:
                    message = """- Refund can only be generated if it's related order invoice is found.\n- For order
                    [%s], system could not find the related order invoice. """ % order_data.get('number')
                elif refunded[0] == 3:
                    message = """- Refund can only be generated if it's related order invoice is in 'Post' status.
                    - For order [%s], system found related invoice but it is not in 'Post' status.""" % order_data.get(
                        'number')
                elif refunded[0] == 2:
                    message = """- Partial refund is received from Woocommerce for order [%s].
                    - System do not process partial refunds.
                    - Either create partial refund manually in Odoo or do full refund in Woocommerce.""" % \
                              order_data.get('number')
            elif woo_status == "completed":
                completed = order.complete_woo_order()
                if not completed:
                    message = """There is not enough stock to complete Delivery for order [%s]""" % order_data.get(
                        'number')
                else:
                    if order.woo_status == "on-hold" and order.auto_workflow_process_id.register_payment:
                        order.paid_invoice_ept(order.invoice_ids)
                    elif order.woo_status == "pending" and order.auto_workflow_process_id.create_invoice:
                        order.woo_status = woo_status
                        order.validate_and_paid_invoices_ept(order.auto_workflow_process_id)
            elif woo_status == "processing":
                if order.woo_status == "on-hold" and order.auto_workflow_process_id.register_payment:
                    order.paid_invoice_ept(order.invoice_ids)
                elif order.woo_status == "pending" and order.auto_workflow_process_id.create_invoice:
                    order.woo_status = woo_status
                    order.validate_and_paid_invoices_ept(order.auto_workflow_process_id)
            orders.append(order)
            if message:
                log_line = order.create_woo_log_lines(message, instance, queue_line)
            elif queue_line.state != 'failed':
                queue_line.state = "done"
                queue_line.order_data = False
                order_vals = {"woo_status": woo_status}
                if not order.woo_trans_id and order_data.get("transaction_id", False):
                    order_vals.update({"woo_trans_id": order_data.get("transaction_id")})
                order.write(order_vals)

        return orders

    def cancel_woo_order(self):
        """
        Cancelled the sale order when it is cancelled in WooCommerce.
        @author: Maulik Barad on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if "done" in self.picking_ids.mapped("state"):
            for picking_id in self.picking_ids:
                picking_id.message_post(
                    body=_("Order %s has been canceled in the WooCommerce store.", self.woo_order_number))
            return False
        self.with_context(disable_cancel_warning=True).action_cancel()
        return True

    def complete_woo_order(self):
        """
        If order is confirmed yet, confirms it first.
        Make the picking done, when order will be completed in WooCommerce.
        This method is used for Update order webhook.
        @author: Maulik Barad on Date 31-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if not self.state == "sale":
            self.action_confirm()
        return self.complete_picking_for_woo(
            self.picking_ids.filtered(lambda x: x.location_dest_id.usage == "customer"))

    def complete_picking_for_woo(self, pickings):
        """
        It will make the pickings done.
        This method is used for Update order webhook.
        @author: Maulik Barad on Date 01-Jan-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        skip_sms = {"skip_sms": True}
        for picking in pickings.filtered(lambda x: x.state != "done"):
            if picking.state != "assigned":
                if picking.move_ids.move_orig_ids:
                    completed = self.complete_picking_for_woo(picking.move_ids.move_orig_ids.picking_id)
                    if not completed:
                        return False
                picking.action_assign()
                if picking.state != "assigned":
                    return False

            result = picking.with_context(**skip_sms).button_validate()

            if isinstance(result, dict):
                context = dict(result.get("context"))
                context.update(skip_sms)
                res_model = result.get("res_model", "")
                # model can be stock.immediate.transfer or stock.backorder.confirmation

                if res_model:
                    immediate_transfer_record = self.env[res_model].with_context(context).create({})
                    immediate_transfer_record.process()
            if picking.state == 'done':
                picking.write({"updated_in_woo": True})
                picking.message_post(body=_("Picking is done by Webhook as Order is fulfilled in Woocommerce."))
            else:
                return result
        return True

    def create_woo_refund(self, refunds_data):
        """
        Creates refund of Woo order, when order is refunded in WooCommerce.
        It will need invoice created and posted for creating credit note in Odoo, otherwise it will
        create log and generate activity as per configuration.
        @author: Maulik Barad on Date 02-Jan-2019.
        @param refunds_data: Data of refunds.
        @return:[True]:When credit notes are created or partial refund is done.
                [2] : When partial refund was made in Woo.
                [3] : When invoice is not posted.
                [4] : When no invoice is created.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if not self.invoice_ids:
            return [4]
        total_refund = 0.0
        for refund in refunds_data:
            total_refund += float(refund.get("total", 0)) * -1
        invoices = self.invoice_ids.filtered(lambda x: x.move_type == "out_invoice")
        refunds = self.invoice_ids.filtered(lambda x: x.move_type == "out_refund")

        if refunds:
            return [True]

        for invoice in invoices:
            if not invoice.state == "posted":
                return [3]
        if self.amount_total == total_refund:
            journal_id = invoices.mapped('journal_id')
            context = {"active_model": "account.move", "active_ids": invoices.ids}
            move_reversal = self.env["account.move.reversal"].with_context(context).create(
                {"refund_method": "cancel",
                 "reason": "Refunded from Woo" if len(refunds_data) > 1 else refunds_data[0].get("reason"),
                 "journal_id": journal_id.id})
            move_reversal.reverse_moves()
            move_reversal.new_move_ids.message_post(
                body=_("Credit note generated by Webhook as Order refunded in Woocommerce."))
            return [True]
        return [2]

    def _prepare_invoice(self):
        """
        This method is used to set instance id to invoice. for identified invoice.
        :return: invoice
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd on date 23-11-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.woo_instance_id:
            invoice_vals.update({'woo_instance_id': self.woo_instance_id.id})
        return invoice_vals

    def _get_invoiceable_lines(self, final=False):
        if self.woo_instance_id:
            rounding = self.woo_instance_id.tax_rounding_method != 'round_globally'
            self.env.context = dict(self._context)
            self.env.context.update({'round': rounding})
        invoiceable_lines = super(SaleOrder, self)._get_invoiceable_lines(final)
        return invoiceable_lines

    def validate_and_paid_invoices_ept(self, work_flow_process_record):
        """
        This method will create invoices, validate it and paid it, according
        to the configuration in workflow sets in quotation.
        :param work_flow_process_record:
        :return: It will return boolean.
        Migration done by Haresh.
        This method used to create and register payment base on the Woo order status.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        self.ensure_one()
        if not self.woo_instance_id:
            return super(SaleOrder, self).validate_and_paid_invoices_ept(work_flow_process_record)
        if self.woo_instance_id and self.woo_status == 'pending':
            return False
        if work_flow_process_record.create_invoice:
            fiscalyear_lock_date = self.company_id._get_user_fiscal_lock_date()
            if self.date_order.date() <= fiscalyear_lock_date:
                message = "You cannot create invoice for order (%s) " \
                          "prior to and inclusive of the lock date %s. " \
                          "So, order is created but invoice is not created." % (
                              self.name, format_date(self.env, fiscalyear_lock_date))
                self.create_woo_log_lines(message, self.woo_instance_id)
                _logger.info(message)
                return True
            invoices = self._create_invoices()
            self.validate_invoice_ept(invoices)
            if self.woo_instance_id and self.woo_status == 'on-hold':
                return True
            if work_flow_process_record.register_payment:
                self.paid_invoice_ept(invoices)
        return True

    def prepare_schedule_activity_message(self, log_lines):
        """
        This method used to prepare schedule activity message based on log line.
        @param : self,log_lines
        @return: message
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 13 December 2021.
        Task_id: 179270
        """
        message = []
        count = 0
        for log_line in log_lines:
            count += 1
            if count <= 5:
                message.append('<' + 'li' + '>' + log_line.message + '<' + '/' + 'li' + '>')
        if count >= 5:
            message.append(
                '<' + 'p' + '>' + 'Please refer the logs and check it in more detail' +
                '<' + '/' + 'p' + '>')
        note = "\n".join(message)
        return note

    def woo_create_schedule_activity_against_logline(self, log_lines, instance):
        """
        This method used to create schedule activity against log line.
        @param : self, mismatch_record, note
        @return: True
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 13 December 2021.
        Task_id: 179270
        """
        mail_activity_obj = self.env['mail.activity']
        ir_model_obj = self.env['ir.model']
        model_id = ir_model_obj.sudo().search([('model', '=', 'common.log.lines.ept')])
        activity_type_id = instance.activity_type_id.id
        date_deadline = datetime.strftime(datetime.now() + timedelta(days=int(instance.date_deadline)), "%Y-%m-%d")
        for log_line in log_lines:
            for user_id in instance.user_ids:
                mail_activity = mail_activity_obj.search([('res_model_id', '=', model_id.id),
                                                          ('user_id', '=', user_id.id),
                                                          ('res_name', '=', log_line.message),
                                                          ('activity_type_id', '=', activity_type_id)])
                note = "<p>" + log_line.message + '</p>'
                duplicate_activity = mail_activity.filtered(lambda x: x.note == note)
                if not mail_activity or not duplicate_activity:
                    vals = {'activity_type_id': activity_type_id, 'note': note,
                            'user_id': user_id.id or self._uid, 'res_model_id': model_id.id,
                            'date_deadline': date_deadline, "res_id": log_line.id}
                    try:
                        mail_activity_obj.create(vals)
                    except Exception as error:
                        _logger.info("Unable to create schedule activity, Please give proper "
                                     "access right of this user :%s  ", user_id.name)
                        _logger.info(error)
        return True


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    woo_line_id = fields.Char()
