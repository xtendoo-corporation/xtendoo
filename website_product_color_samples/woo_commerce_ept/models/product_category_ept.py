# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

from ..img_upload import img_file_upload

_logger = logging.getLogger("WooCommerce")


class WooProductCategoryEpt(models.Model):
    _name = 'woo.product.categ.ept'
    _order = 'name'
    _description = "WooCommerce Product Category"
    _rec_name = 'complete_name'

    name = fields.Char(required="1", translate=True)
    parent_id = fields.Many2one('woo.product.categ.ept', string='Parent', index=True, ondelete='cascade')
    description = fields.Char(translate=True)
    slug = fields.Char(help="The slug is the URL-friendly version of the name. It is usually all "
                            "lowercase and contains only letters, numbers, and hyphens.")
    display = fields.Selection([('default', 'Default'), ('products', 'Products'),
                                ('subcategories', 'Sub Categories'), ('both', 'Both')], default='default')
    woo_instance_id = fields.Many2one("woo.instance.ept", "Instance", required=1)
    exported_in_woo = fields.Boolean(default=False, readonly=True)
    woo_categ_id = fields.Char('Woo Category Id', size=120, readonly=True)
    image = fields.Binary()
    url = fields.Char(size=600, string='Image URL')
    response_url = fields.Char(size=600, string='Response URL', help="URL from WooCommerce")
    complete_name = fields.Char(compute='_compute_complete_name', recursive=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    def check_woocommerce_response(self, response, process, instance):
        """
        This method verifies the response got from WooCommerce after Update/Export operations.
        @param instance:
        @param process: Name of the process.
        @param response: Response from Woo.
        @param model_name: Name of the model for creating log line.
        @return: Log line if issue found.
        @author: Maulik Barad on Date 10-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]
        operation = "import" if process == "Import Category" else "export"

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
                                                                  message=response.content)
        return data

    def import_all_woo_categories(self, wc_api, page, instance):
        """
        This method imports all categories, when multiple pages data is there.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        try:
            res = wc_api.get("products/categories", params={'per_page': 100, 'page': page})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Categories.\n\nPlease Check your Connection and"
                              "Instance Configuration.\n\n" + str(error)))
        response = self.check_woocommerce_response(res, "Import Category", instance)
        if not isinstance(response, list):
            return []
        return response

    def create_or_update_woo_category(self, category, sync_images_with_product, instance):
        """
        Category will be created or updated from the data given.
        @param category: Data of a category.
        @param sync_images_with_product: If image needed to import.
        @param instance: Record of Instance.
        @author: Maulik Barad on Date 11-Nov-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_categ_id = category.get('id')
        slug = category.get('slug')
        parent_woo_id = category.get('parent')
        parent_id = binary_img_data = False
        if parent_woo_id:
            parent_id = self.search([('woo_categ_id', '=', parent_woo_id),
                                     ('woo_instance_id', '=', instance.id)], limit=1).id
        vals = {'name': category.get('name'), 'woo_instance_id': instance.id, 'parent_id': parent_id,
                'woo_categ_id': woo_categ_id, 'display': category.get('display'), 'slug': slug, 'exported_in_woo': True,
                'description': category.get('description', '')}
        if sync_images_with_product:
            res_image = category.get('image') and category.get('image', {}).get('src', "")
            if res_image:
                try:
                    res_img = requests.get(res_image, stream=True, verify=True, timeout=10)
                    if res_img.status_code == 200:
                        binary_img_data = base64.b64encode(res_img.content)
                except Exception as error:
                    _logger.info(str(error))
            if binary_img_data:
                vals.update({'image': binary_img_data})
        woo_categ = self.search(["&", ('woo_instance_id', '=', instance.id), "|", ('woo_categ_id', '=', woo_categ_id),
                                 ('slug', '=', slug)], limit=1)
        if woo_categ:
            woo_categ.write(vals)
        else:
            woo_categ = self.create(vals)

        return woo_categ

    def sync_woo_product_category(self, instance, woo_product_categ=False, sync_images_with_product=True):
        """
        This method imports category data and processes them.
        @param instance: Record of Instance.
        @param woo_product_categ: For importing particular category.
        @param sync_images_with_product: If image needed to import.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        if woo_product_categ and woo_product_categ.exported_in_woo:
            try:
                response = wc_api.get("products/categories/%s" % woo_product_categ.woo_categ_id)
            except Exception as error:
                raise UserError(_("Something went wrong while importing Categories.\n\nPlease Check your Connection and"
                                  "Instance Configuration.\n\n" + str(error)))

            data = self.check_woocommerce_response(response, "Import Category", instance)
            if not isinstance(data, dict):
                return False
        else:
            try:
                response = wc_api.get("products/categories", params={'per_page': 100})
            except Exception as error:
                raise UserError(_("Something went wrong while importing Categories.\n\nPlease Check your Connection and"
                                  "Instance Configuration.\n\n" + str(error)))

            data = self.check_woocommerce_response(response, "Import Category", instance)
            if not isinstance(data, list):
                return False

        total_pages = response.headers.get('x-wp-totalpages') or 1
        if woo_product_categ:
            results = [data]
        else:
            results = data

        if int(total_pages) >= 2:
            for page in range(2, int(total_pages) + 1):
                results += self.import_all_woo_categories(wc_api, page, instance)

        processed_categs = []
        for res in results:
            if not isinstance(res, dict):
                continue
            if res.get('id', False) in processed_categs:
                continue

            categ_results = [res]
            for categ_result in categ_results:
                if categ_result.get('parent'):
                    parent_categ = list(filter(lambda categ: categ['id'] == categ_result.get('parent'), results))
                    if not parent_categ:
                        try:
                            response = wc_api.get("products/categories/%s" % (categ_result.get('parent')))
                        except Exception as error:
                            raise UserError(_("Something went wrong while importing Categories.\n\nPlease Check your "
                                              "Connection and Instance Configuration.\n\n" + str(error)))

                        parent_categ = self.check_woocommerce_response(response, "Import Category", instance)
                        if not isinstance(parent_categ, dict):
                            continue
                    else:
                        parent_categ = parent_categ[0]
                    if parent_categ not in categ_results:
                        categ_results.append(parent_categ)

            categ_results.reverse()
            for result in categ_results:
                if result.get('id') in processed_categs:
                    continue

                woo_categ_id = result.get('id')
                self.create_or_update_woo_category(result, sync_images_with_product, instance)

                processed_categs.append(woo_categ_id)
        return True

    def export_product_categs(self, instance, woo_product_categs):
        """
        This method is used to export categories to WooCommerce.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        for woo_product_categ in woo_product_categs:
            product_categs = [woo_product_categ]
            for categ in product_categs:
                if categ.parent_id and categ.parent_id not in product_categs and not categ.parent_id.woo_categ_id:
                    product_categs.append(categ.parent_id)

            product_categs.reverse()
            for product_categ in product_categs:
                data = {'name': str(product_categ.name), 'description': str(product_categ.description or ''),
                        'display': str(product_categ.display)}
                if product_categ.image:
                    mime_type = guess_mimetype(base64.b64decode(product_categ.image))
                    res = img_file_upload.upload_image(instance, product_categ.image,
                                                       "%s_%s" % (product_categ.name, product_categ.id), mime_type)
                    data.update({'image': {'src': res.get('url', "")}})
                if product_categ.slug:
                    data.update({'slug': str(product_categ.slug)})
                if product_categ.parent_id.woo_categ_id:
                    data.update({'parent': product_categ.parent_id.woo_categ_id})

                try:
                    res = wc_api.post("products/categories", data)
                except Exception as error:
                    raise UserError(_("Something went wrong while Exporting Category.\n\nPlease Check your Connection "
                                      "and Instance Configuration.\n\n" + str(error)))
                category_res = self.check_woocommerce_response(res, "Export Category", instance)
                if not isinstance(category_res, dict):
                    continue

                product_categ_id = category_res.get('id')
                if product_categ_id:
                    slug = category_res.get('slug', '')
                    response_data = {'woo_categ_id': product_categ_id, 'slug': slug, 'exported_in_woo': True}
                    product_categ.write(response_data)
        self._cr.commit()
        return True

    def update_product_categs_in_woo(self, instance, woo_product_categs):
        """
        This method used to update product category from Odoo to Woocommerce.
        It will only update category which is already synced.
        @param : self
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 13/12/2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wc_api = instance.woo_connect()
        category_data = []

        for woo_categ in woo_product_categs:
            _logger.info("Start request for Categories in Batch")
            data = {'id': woo_categ.woo_categ_id, 'name': str(woo_categ.name),
                    'display': str(woo_categ.display), 'description': str(woo_categ.description or '')}
            if woo_categ.image:
                mime_type = guess_mimetype(base64.b64decode(woo_categ.image))
                res = img_file_upload.upload_image(instance, woo_categ.image, "%s_%s" % (woo_categ.name, woo_categ.id),
                                                   mime_type)
                img_url = res.get('url') if res else ""
                data.update({'image': {'src': img_url}})

            if woo_categ.slug:
                data.update({'slug': str(woo_categ.slug)})
            if woo_categ.parent_id.woo_categ_id:
                data.update({'parent': woo_categ.parent_id.woo_categ_id})
            category_data.append(data)

        try:
            res = wc_api.post('products/categories/batch', {'update': category_data})
        except Exception as error:
            raise UserError(_("Something went wrong while Updating Categories.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))
        response = self.check_woocommerce_response(res, "Update Category", instance)
        if not isinstance(response, dict):
            return False

        _logger.info("Done updating Batch Categories.")
        return True
