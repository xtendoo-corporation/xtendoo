# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import ast
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger("WooCommerce")


class WooCouponEpt(models.Model):
    _name = "woo.coupons.ept"
    _rec_name = "code"
    _description = "WooCommerce Coupon"

    coupon_id = fields.Char("WooCommerce Id", size=120, help="WooCommerce coupon id")
    code = fields.Char(required=1, help="Coupon code")
    description = fields.Text(help="Coupon description.")
    discount_type = fields.Selection([('percent', 'Percentage Discount'), ('fixed_cart', 'Fixed Cart Discount'),
                                      ('fixed_product', 'Fixed Product Discount')], default="fixed_cart",
                                     help="Determines the type of discount that will be applied.")
    amount = fields.Float(help="The amount of discount.")
    free_shipping = fields.Boolean("Allow Free Shipping",
                                   help="Check this box if the coupon grants free shipping."
                                        "A free shipping method must be enabled in your shipping"
                                        "zone and be set to require \"a valid free shipping coupon\""
                                        "(see the \"Free Shipping Requires\""
                                        "setting in WooCommerce).")
    expiry_date = fields.Date(help="Coupon expiry date")
    minimum_amount = fields.Float("Minimum Spend",
                                  help="Minimum order amount that needs to be in the cart before coupon applies.")
    maximum_amount = fields.Float("Maximum Spend", help="Maximum order amount allowed when using the coupon.")
    individual_use = fields.Boolean(help="If true, the coupon can only be used individually."
                                         "Other applied coupons will be removed from the cart.")
    exclude_sale_items = fields.Boolean(help="Check this box if the coupon should not apply "
                                             "to items on sale. Per-item coupons will only work"
                                             "if the item is not on sale. Per-cart coupons will"
                                             "only work if there are no sale items in the cart.")
    product_ids = fields.Many2many("woo.product.template.ept", 'woo_product_tmpl_product_rel', 'product_ids',
                                   'woo_product_ids', "Products", help="List of product IDs the coupon can be used on.")
    product_variant_ids = fields.Many2many("woo.product.product.ept", 'woo_prodcut_variant_product_rel',
                                           'product_variant_id', 'woo_product_id', string="Product Variants",
                                           help="List of product variants IDs the coupon can be used on.")

    exclude_product_ids = fields.Many2many("woo.product.template.ept", 'woo_product_tmpl_exclude_product_rel',
                                           'exclude_product_ids', 'woo_product_ids', "Exclude Products",
                                           help="List of product IDs the coupon cannot be used on.")

    exclude_product_variant_ids = fields.Many2many("woo.product.product.ept", 'woo_prodcut_variant_exclude_product_rel',
                                                   'exclude_product_variant_id', 'exclude_woo_product_id',
                                                   string="Exclude Product Variants",
                                                   help="List of product variants IDs the coupon cannot be used on.")

    product_category_ids = fields.Many2many('woo.product.categ.ept', 'woo_template_categ_incateg_rel',
                                            'product_category_ids', 'woo_categ_id', "Product Categories")
    excluded_product_category_ids = fields.Many2many('woo.product.categ.ept', 'woo_template_categ_exclude_categ_rel',
                                                     'excluded_product_category_ids', 'woo_categ_id',
                                                     "Exclude Product Categories")
    email_restrictions = fields.Char(help="List of email addresses that can use this coupon,"
                                          "Enter Email ids Separated by comma(,)")
    usage_limit = fields.Integer("Usage limit per coupon", help="How many times the coupon can be used in total.")
    limit_usage_to_x_items = fields.Integer(help="Max number of items in the cart the coupon can be applied to.")
    usage_limit_per_user = fields.Integer(help="How many times the coupon can be used per customer.")
    usage_count = fields.Integer(help="Number of times the coupon has been used already.")
    used_by = fields.Char(help="List of user IDs (or guest email addresses) that have used the coupon.")
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1)
    exported_in_woo = fields.Boolean("Exported in WooCommerce")
    active = fields.Boolean(default=True)
    _sql_constraints = [('code_unique', 'unique(code,woo_instance_id)', "Code already exists. Code must be unique!")]

    def create_woo_coupon_log_lines(self, message, instance, queue_line=None, operation_type="import"):
        """
        Creates log line for the failed queue line.
        @param operation_type:
        @param instance:
        @param queue_line: Failed queue line.
        @param message: Cause of failure.
        @return: Created log line.
        @author: Nilesh Parmar
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if queue_line:
            queue_line.state = "failed"
        return self.env["common.log.lines.ept"].create_common_log_line_ept(
            operation_type=operation_type, module="woocommerce_ept", woo_instance_id=instance.id, model_name=self._name,
            message=message, woo_coupon_data_queue_line_id=queue_line and queue_line.id)

    def check_woocommerce_response(self, response, process, instance):
        """
        This method verifies the response got from WooCommerce after Update/Export operations.
        @param instance:
        @param process: Name of the process.
        @param response: Response from Woo.
        @return: Log line if issue found.
        @author: Maulik Barad on Date 10-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        operation = "import" if process == "Import Coupons" else "export"

        if not isinstance(response, requests.models.Response):
            message = process + "Response is not in proper format :: %s" % response
            return common_log_line_obj.create_common_log_line_ept(operation_type=operation, module="woocommerce_ept",
                                                                  woo_instance_id=instance.id, model_name=self._name,
                                                                  message=message)
        if response.status_code not in [200, 201]:
            return common_log_line_obj.create_common_log_line_ept(operation_type=operation, module="woocommerce_ept",
                                                                  woo_instance_id=instance.id, model_name=self._name,
                                                                  message=response.content)
        try:
            data = response.json()
        except Exception as error:
            message = "Json Error : While" + process + "\n%s" % error
            return common_log_line_obj.create_common_log_line_ept(operation_type=operation, module="woocommerce_ept",
                                                                  woo_instance_id=instance.id, model_name=self._name,
                                                                  message=message)
        return data

    def prepare_coupon_categories(self, coupon, instance):
        """
        This method searches the categories attached with the coupon.
        @param coupon: Data of a coupon.
        @param instance: Record of instance.
        @author: Maulik Barad on Date 10-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_categ_ept_obj = self.env["woo.product.categ.ept"]
        woo_product_categ = woo_product_categ_ept_obj.search([("woo_categ_id", "in", coupon.get("product_categories")),
                                                              ("woo_instance_id", "=", instance.id)]).ids
        product_category = [(6, False, woo_product_categ)] or ''
        exclude_woo_product_categ = woo_product_categ_ept_obj.search(
            [("woo_categ_id", "in", coupon.get("excluded_product_categories")),
             ("woo_instance_id", "=", instance.id)]).ids
        exclude_product_category = [(6, False, exclude_woo_product_categ)] or ''
        return product_category, exclude_product_category

    def prepare_coupon_products(self, coupon, instance):
        """
        This method searches the products attached with the coupon.
        @param coupon: Data of a coupon.
        @param instance: Record of instance.
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        woo_product_template_ept_obj = self.env["woo.product.template.ept"]
        woo_product_product_obj = self.env['woo.product.product.ept']
        coupon_product_ids = coupon.get("product_ids")
        coupon_exclude_product_id = coupon.get("excluded_product_ids")

        woo_product_ids = woo_product_template_ept_obj.search([("woo_tmpl_id", "in", coupon_product_ids),
                                                               ("woo_instance_id", "=", instance.id)])
        remain_products = list(set(coupon_product_ids) - set(list(map(int, woo_product_ids.mapped("woo_tmpl_id")))))
        woo_variant_ids = woo_product_product_obj.search(
            [("variant_id", "in", remain_products), ("woo_instance_id", "=", instance.id)])
        remain_products = list(set(remain_products) - set(list(map(int, woo_variant_ids.mapped("variant_id")))))

        exclude_woo_product_ids = woo_product_template_ept_obj.search([("woo_tmpl_id", "in", coupon_exclude_product_id),
                                                                       ("woo_instance_id", "=", instance.id)])
        remain_exclude_products = list(
            set(coupon_exclude_product_id) - set(list(map(int, exclude_woo_product_ids.mapped("woo_tmpl_id")))))
        exclude_woo_variant_ids = woo_product_product_obj.search([("variant_id", "in", remain_exclude_products),
                                                                  ("woo_instance_id", "=", instance.id)])
        remain_exclude_products = list(
            set(remain_exclude_products) - set(list(map(int, exclude_woo_variant_ids.mapped("variant_id")))))

        product_dict = {"woo_product_ids": woo_product_ids, "remain_products": remain_products,
                        "woo_variant_ids": woo_variant_ids,
                        "remain_exclude_products": remain_exclude_products,
                        "exclude_woo_product_ids": exclude_woo_product_ids,
                        "exclude_woo_variant_ids": exclude_woo_variant_ids}
        return product_dict

    def prepare_woo_coupon_vals(self, coupon, instance, products_dict, product_category, exclude_product_category,
                                email_ids):
        """
        This method prepares dict for creating or updating the coupon.
        @param coupon: Data of a coupon.
        @param instance: Record of the instance.
        @param products_dict: Products to add in coupon.
        @param product_category: Category to add in coupon.
        @param exclude_product_category: Excluded category to add in coupon.
        @param email_ids: Restricted Email ids.
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        woo_product_ids = products_dict.get("woo_product_ids")
        woo_variant_ids = products_dict.get("woo_variant_ids")
        exclude_woo_product_ids = products_dict.get("exclude_woo_product_ids")
        exclude_woo_variant_ids = products_dict.get("exclude_woo_variant_ids")

        vals = {
            'coupon_id': coupon.get("id"), 'code': coupon.get("code"),
            'description': coupon.get("description"), 'discount_type': coupon.get("discount_type"),
            'amount': coupon.get("amount"), 'free_shipping': coupon.get("free_shipping"),
            'expiry_date': coupon.get("date_expires") or False,
            'minimum_amount': float(coupon.get("minimum_amount", 0.0)),
            'maximum_amount': float(coupon.get("maximum_amount", 0.0)),
            'individual_use': coupon.get("individual_use"), 'exclude_sale_items': coupon.get("exclude_sale_items"),
            'product_ids': [(6, False, woo_product_ids.ids)], 'product_variant_ids': [(6, False, woo_variant_ids.ids)],
            'exclude_product_ids': [(6, False, exclude_woo_product_ids.ids)],
            'exclude_product_variant_ids': [(6, False, exclude_woo_variant_ids.ids)],
            'product_category_ids': product_category, 'excluded_product_category_ids': exclude_product_category,
            'email_restrictions': email_ids, 'usage_limit': coupon.get("usage_limit"),
            'limit_usage_to_x_items': coupon.get("limit_usage_to_x_items"),
            'usage_limit_per_user': coupon.get("usage_limit_per_user"), 'usage_count': coupon.get("usage_count"),
            'used_by': coupon.get("used_by"), 'woo_instance_id': instance.id, 'exported_in_woo': True
        }
        return vals

    def create_or_update_woo_coupon(self, coupon, queue_line, instance):
        """
        This method searches for the coupon, prepares data for it and updates or creates from the data.
        @param coupon: Data of a coupon.
        @param queue_line: Queue line.
        @param instance: Record of the instance.
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        coupon_id = coupon.get("id")
        code = coupon.get("code")

        woo_coupon = self.with_context(active_test=False).search(["&", "|", ('coupon_id', '=', coupon_id),
                                                                  ('code', '=', code),
                                                                  ('woo_instance_id', '=', instance.id)], limit=1)

        product_category, exclude_product_category = self.prepare_coupon_categories(coupon, instance)

        products_dict = self.prepare_coupon_products(coupon, instance)

        if products_dict.get("remain_products") or products_dict.get("remain_exclude_products"):
            message = "System could not import coupon '%s'. Some of the products are not imported in odoo.", code
            self.create_woo_coupon_log_lines(message, instance, queue_line)
            return False

        email_ids = "" if not coupon.get("email_restrictions") else ",".join(coupon.get("email_restrictions"))

        vals = self.prepare_woo_coupon_vals(coupon, instance, products_dict, product_category, exclude_product_category,
                                            email_ids)

        if not woo_coupon:
            woo_coupon = self.create(vals)
        else:
            woo_coupon.write(vals)
        return woo_coupon

    def create_or_write_coupon(self, queue_lines):
        """
        this method is used to create new coupons or update the coupons which available in odoo.
        @param queue_lines: coupons data and type list
        @author : Nilesh Parmar on date 17 Dec 2019.
        """
        instance = queue_lines.instance_id
        woo_coupons = []
        commit_count = 0
        for queue_line in queue_lines:
            commit_count += 1
            if commit_count == 10:
                queue_line.coupon_data_queue_id.is_process_queue = True
                self._cr.commit()
                commit_count = 0

            coupon = ast.literal_eval(queue_line.coupon_data)
            if not coupon.get("code"):
                message = "Coupon code not available in coupon number %s" % coupon.get("id")
                self.create_woo_coupon_log_lines(message, instance, queue_line)
                continue

            woo_coupon = self.create_or_update_woo_coupon(coupon, queue_line, instance)
            if not woo_coupon:
                continue
            queue_line.state = "done"
            queue_line.coupon_data = False
            woo_coupons += woo_coupon
            queue_line.coupon_data_queue_id.is_process_queue = False
        return woo_coupons

    def woo_import_all_coupons(self, wc_api, page, instance):
        """
        this method is used to import the all coupons from woo commerce.
        @param page:
        @param wc_api:
        @param instance:
        @author : Nilesh Parmar on date 17 Dec 2019.
        """
        try:
            res = wc_api.get("coupons", params={"per_page": 100, 'page': page})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Coupons.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        result = self.check_woocommerce_response(res, "Import Coupons", instance)
        if not isinstance(result, list):
            return False
        return result

    def create_woo_coupon_data_queue(self, woo_instance, coupon_data, created_by="import"):
        """
        Creates coupon data queues from the data got from API.
        @param created_by: From where queue is being created.
        @param woo_instance: Instance of Woocommerce.
        @param coupon_data: Imported JSON data of coupons.
        @author : Nilesh Parmar update on date 31 Dec 2019.
        """
        woo_coupon_data_queue_obj = self.env["woo.coupon.data.queue.ept"]
        vals = {"woo_instance_id": woo_instance.id, "created_by": created_by}
        coupon_queues = []
        while coupon_data:
            data = coupon_data[:100]
            if data:
                coupon_data_queue = woo_coupon_data_queue_obj.create(vals)
                coupon_queues.append(coupon_data_queue.id)
                _logger.info("New coupon queue %s created.", coupon_data_queue.name)
                coupon_data_queue.create_woo_data_queue_lines(data)
                if coupon_data_queue.coupon_data_queue_line_ids:
                    _logger.info("Lines added in Coupon queue %s.", coupon_data_queue.name)
                else:
                    coupon_data_queue.unlink()
                del coupon_data[:100]
        _logger.info("Import coupon process completed.")
        return coupon_queues

    def sync_woo_coupons(self, instance):
        """
        This method imports coupon data and creates queues of it.
        @param instance: Record of instance.
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        wc_api = instance.woo_connect()
        try:
            res = wc_api.get('coupons', params={"per_page": 100})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Coupons.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        results = self.check_woocommerce_response(res, "Import Coupons", instance)
        if not isinstance(results, list):
            return False
        total_pages = res.headers.get('x-wp-totalpages') or 1

        if int(total_pages) >= 2:
            for page in range(2, int(total_pages) + 1):
                results += self.woo_import_all_coupons(wc_api, page, instance)
        if not results:
            _logger.info("Coupons data not found from woo")
            return False
        coupon_queue = self.create_woo_coupon_data_queue(instance, results)

        return coupon_queue

    @api.model
    def export_coupons(self, instance):
        """
        this method used to export the coupons to woo commerce
        :param instance:
        @author: Nilesh Parmar on 16 Dec 2019
        """
        wc_api = instance.woo_connect()
        coupons = []
        for woo_coupon in self:
            woo_product_tmpl_ids, woo_product_exclude_tmpl_ids = woo_coupon.get_coupon_product_data()
            woo_category_ids, woo_exclude_category_ids = woo_coupon.get_coupon_category_data()
            vals = woo_coupon.prepare_vals_to_export_update_coupon(woo_product_tmpl_ids,
                                                                   woo_product_exclude_tmpl_ids, woo_category_ids,
                                                                   woo_exclude_category_ids)
            coupons.append(vals)

        coupons_data = {"create": coupons}
        _logger.info("Exporting coupons to Woo of instance %s", instance.name)
        try:
            res = wc_api.post("coupons/batch", coupons_data)
        except Exception as error:
            raise UserError(_("Something went wrong while Exporting Coupons.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))
        response = self.check_woocommerce_response(res, "Export Coupons", instance)
        if not isinstance(response, dict):
            return False
        exported_coupons = response.get("create")
        for woo_coupon in exported_coupons:
            exported_coupon = self.filtered(
                lambda x: x.code.lower() == woo_coupon.get("code") and x.woo_instance_id == instance)
            if woo_coupon.get("id", False) and exported_coupon:
                exported_coupon.write(
                    {"coupon_id": woo_coupon.get("id"), "exported_in_woo": True, "code": woo_coupon.get("code")})
        _logger.info("Exported %s coupons to Woo of instance %s", len(exported_coupons), instance.name)
        return True

    def update_woo_coupons(self, instances):
        """
        This method is used to update coupons to WooCommerce.
        @param instances: Record of instances.
        @author: Nilesh Parmar on 16 Dec 2019
        """
        for instance in instances:
            wc_api = instance.woo_connect()
            coupons = []
            for woo_coupon in self:
                woo_product_tmpl_ids, woo_product_exclude_tmpl_ids = woo_coupon.get_coupon_product_data()
                woo_category_ids, woo_exclude_category_ids = woo_coupon.get_coupon_category_data()

                vals = woo_coupon.prepare_vals_to_export_update_coupon(woo_product_tmpl_ids,
                                                                       woo_product_exclude_tmpl_ids, woo_category_ids,
                                                                       woo_exclude_category_ids)
                vals.update({'id': woo_coupon.coupon_id})
                coupons.append(vals)
            _logger.info("Updating coupons to Woo of instance %s", instance.name)
            try:
                res = wc_api.put("coupons/batch", {'update': coupons})
            except Exception as error:
                raise UserError(_("Something went wrong while Updating Coupons.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            results = self.check_woocommerce_response(res, "Update Coupon", instance)
            if not isinstance(results, dict):
                continue
        return True

    def get_coupon_product_data(self):
        """
        This method is used to collect product ids to update/export coupon in WooCommerce.
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        self.ensure_one()
        woo_product_tmpl_ids = []
        woo_product_exclude_tmpl_ids = []

        for product_tmpl_id in self.product_ids:
            woo_product_tmpl_ids.append(product_tmpl_id.woo_tmpl_id)
        for product_variant in self.product_variant_ids:
            woo_product_tmpl_ids.append(product_variant.variant_id)

        for exclude_product_tmpl_id in self.exclude_product_ids:
            woo_product_exclude_tmpl_ids.append(exclude_product_tmpl_id.woo_tmpl_id)
        for exclude_variant in self.exclude_product_variant_ids:
            woo_product_exclude_tmpl_ids.append(exclude_variant.variant_id)

        return woo_product_tmpl_ids, woo_product_exclude_tmpl_ids

    def get_coupon_category_data(self):
        """
        This method is used to collect category ids to update/export coupon in WooCommerce.
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        self.ensure_one()
        woo_category_ids = []
        woo_exclude_category_ids = []

        for categ_id in self.product_category_ids:
            woo_category_ids.append(categ_id.woo_categ_id)
        for exclude_categ_id in self.excluded_product_category_ids:
            woo_exclude_category_ids.append(exclude_categ_id.woo_categ_id)

        return woo_category_ids, woo_exclude_category_ids

    def prepare_vals_to_export_update_coupon(self, woo_product_tmpl_ids, woo_product_exclude_tmpl_ids, woo_category_ids,
                                             woo_exclude_category_ids):
        """
        This method is used to collect product ids to update/export coupon in WooCommerce.
        @param woo_product_tmpl_ids:
        @param woo_product_exclude_tmpl_ids:
        @param woo_category_ids:
        @param woo_exclude_category_ids:
        @author: Maulik Barad on Date 10-Nov-2020.
        """
        self.ensure_one()
        email_ids = []
        if self.email_restrictions:
            email_ids = self.email_restrictions.split(",")

        vals = {'code': self.code,
                'description': str(self.description or '') or '',
                'discount_type': self.discount_type, 'free_shipping': self.free_shipping,
                'amount': str(self.amount), 'date_expires': "{}".format(self.expiry_date or ''),
                'minimum_amount': str(self.minimum_amount),
                'maximum_amount': str(self.maximum_amount),
                'individual_use': self.individual_use,
                'exclude_sale_items': self.exclude_sale_items,
                'product_ids': woo_product_tmpl_ids,
                'excluded_product_ids': woo_product_exclude_tmpl_ids,
                'product_categories': woo_category_ids,
                'excluded_product_categories': woo_exclude_category_ids,
                'email_restrictions': email_ids,
                'usage_limit': self.usage_limit,
                'limit_usage_to_x_items': self.limit_usage_to_x_items,
                'usage_limit_per_user': self.usage_limit_per_user}
        return vals
