# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger("WooCommerce")


class WooTagsEpt(models.Model):
    _name = "woo.tags.ept"
    _order = 'name'
    _description = "WooCommerce Product Tag"

    name = fields.Char(required=1, copy=False)
    description = fields.Text()
    slug = fields.Char(help="The slug is the URL-friendly version of the name. It is usually all "
                            "lowercase and contains only letters, numbers, and hyphens.", copy=False)
    woo_tag_id = fields.Char(size=120, copy=False)
    exported_in_woo = fields.Boolean(default=False, copy=False)
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1, copy=False)

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
        operation = "import" if process == "Get Product Tags" else "export"

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

    @api.model
    def woo_export_product_tags(self, instances, woo_product_tags):
        """
        This method is used for export the product tags from odoo to woo commerce
        :param instances:  It is the browsable object of the woo instance
        :param woo_product_tags: It contains the browsable object of woo product tags and its type is list
        :return: It will return True if the process of export tags in woo is successful completed
        @author: Dipak Gogiya @Emipro Technologies Pvt.Ltd
        @change: For exporting tags from wizard and action by Maulik Barad on Date 13-Dec-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for instance in instances:
            wc_api = instance.woo_connect()
            product_tags = []
            for woo_product_tag in woo_product_tags.filtered(lambda x: x.woo_instance_id == instance):
                row_data = {"name": woo_product_tag.name,
                            "description": str(woo_product_tag.description or ""),
                            "slug": str(woo_product_tag.slug or "")}
                product_tags.append(row_data)
            if not product_tags:
                continue
            _logger.info("Exporting tags to Woo of instance %s", instance.name)
            try:
                res = wc_api.post("products/tags/batch", {"create": product_tags})
            except Exception as error:
                raise UserError(_("Something went wrong while Exporting Tags.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            response = self.check_woocommerce_response(res, "Export Tags", instance)
            if not isinstance(response, dict):
                continue
            exported_product_tags = response.get("create")
            for tag in exported_product_tags:
                woo_product_tag = woo_product_tags.filtered(
                    lambda x: x.name == tag.get("name") and x.woo_instance_id == instance)
                if tag.get("id", False) and woo_product_tag:
                    woo_product_tag.write({"woo_tag_id": tag.get("id", False),
                                           "exported_in_woo": True,
                                           "slug": tag.get("slug", "")})
            _logger.info("Exported %s tags to Woo of instance %s", len(exported_product_tags), instance.name)
        self._cr.commit()
        return True

    def woo_import_all_tags(self, wc_api, page, instance):
        """
        This method is used for collecting the info of tags by page wise and return the response into dict format
        @param wc_api: It is the connection object of woo commerce to odoo
        @param page: It contains the page number of woo product tags and its type is Integer
        @return: It will return the response of collection details of tags from woo and its type is Dict
        @param instance:
        @author: Dipak Gogiya @Emipro Technologies Pvt.Ltd
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        try:
            res = wc_api.get("products/tags", params={"per_page": 100, 'page': page})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Tags.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))
        response = self.check_woocommerce_response(res, "Get Product Tags", instance)
        if not isinstance(response, list):
            return []
        return response

    def woo_sync_product_tags(self, instance):
        """
        This method is used for collecting the tags information and also sync the tags into woo commerce in odoo
        :param instance: It is the browsable object of the woo instance
        :return: return True if the process of tags is successful complete
        @author: Dipak Gogiya @Emipro Technologies Pvt.Ltd
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        try:
            res = wc_api.get("products/tags", params={"per_page": 100})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Tags.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        results = self.check_woocommerce_response(res, "Get Product Tags", instance)
        if not isinstance(results, list):
            return False
        total_pages = res.headers.get('x-wp-totalpages', 0) or 1
        if int(total_pages) >= 2:
            for page in range(2, int(total_pages) + 1):
                results += self.woo_import_all_tags(wc_api, page, instance)

        for res in results:
            if not isinstance(res, dict):
                continue
            tag_id = res.get('id')
            name = res.get('name')
            description = res.get('description')
            slug = res.get('slug')
            woo_tag = self.search(["&", ('woo_instance_id', '=', instance.id), "|", ('woo_tag_id', '=', tag_id),
                                   ('slug', '=', slug)], limit=1)
            if woo_tag:
                woo_tag.write({'woo_tag_id': tag_id, 'name': name, 'description': description,
                               'slug': slug, 'exported_in_woo': True})
            else:
                self.create({'woo_tag_id': tag_id, 'name': name, 'description': description,
                             'slug': slug, 'woo_instance_id': instance.id, 'exported_in_woo': True})
        return True

    @api.model
    def woo_update_product_tags(self, instances, woo_product_tags):
        """
        This method will update the tags in WooCommerce.
        @author: Maulik Barad on Date 14-Dec-2019.
        @param instances: Recordset of Woo Instance.
        @param woo_product_tags: Recordset of Tag in Woo layer to update.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        for instance in instances:
            wc_api = instance.woo_connect()
            product_tags = []
            for woo_product_tag in woo_product_tags.filtered(lambda x: x.woo_instance_id == instance):
                row_data = {"id": woo_product_tag.woo_tag_id, "name": woo_product_tag.name,
                            "description": str(woo_product_tag.description or ""),
                            "slug": str(woo_product_tag.slug or "")}
                product_tags.append(row_data)

            data = {"update": product_tags}
            _logger.info("Updating tags in Woo of instance %s", instance.name)
            try:
                res = wc_api.post("products/tags/batch", data)
            except Exception as error:
                raise UserError(_("Something went wrong while Updating Tags.\n\nPlease Check your Connection and "
                                  "Instance Configuration.\n\n" + str(error)))

            response = self.check_woocommerce_response(res, "Update Tags", instance)
            if not isinstance(response, dict):
                continue
            updated_product_tags = response.get("update")
            for tag in updated_product_tags:
                woo_product_tag = woo_product_tags.filtered(
                    lambda x: x.woo_tag_id == tag.get("id") and x.woo_instance_id == instance)
                if woo_product_tag:
                    woo_product_tag.write({"slug": tag.get("slug", "")})
            _logger.info("Updated %s tags to Woo of instance %s", len(updated_product_tags), instance.name)
        return True
