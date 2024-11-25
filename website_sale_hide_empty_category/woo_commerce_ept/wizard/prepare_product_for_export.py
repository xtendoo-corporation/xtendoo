# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
import logging
import io
from csv import DictWriter
from datetime import datetime
from io import StringIO
from _collections import OrderedDict
from odoo.tools.misc import xlsxwriter
from odoo.tools import is_html_empty
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger("WooCommerce")


class PrepareProductForExport(models.TransientModel):
    """
    Model for adding Odoo products into Woo Layer.
    @author: Haresh Mori on Date 13-Apr-2020.
    """
    _name = "woo.prepare.product.for.export.ept"
    _description = "WooCommerce Prepare Product For Export"

    export_method = fields.Selection(
        [("direct", "Export in WooCommerce Layer"), ("csv", "Export in CSV file"), ("xlsx", "Export in XLSX file")],
        default="direct")
    woo_instance_id = fields.Many2one("woo.instance.ept")
    file_name = fields.Char(help="Name of CSV file.")
    csv_data = fields.Binary('CSV File', readonly=True, attachment=False)

    def prepare_product_for_export(self):
        """
        This method is used to export products in Woo layer as per seleted product in Odoo product layer.
        If "direct" is selected, then it will direct export product into Woo layer.
        If "xlsx/csv" is selected, then it will export product data in CSV / xlsx file, if user want to do some
        modification in name, description, etc. before importing into Woocommmerce.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        product_template_obj = self.env["product.template"]
        _logger.info("Starting product exporting via %s method...", self.export_method)

        active_template_ids = self._context.get("active_ids", [])
        templates = product_template_obj.browse(active_template_ids)
        product_templates = templates.filtered(lambda template: template.detailed_type == "product")
        if not product_templates:
            raise UserError(_("It seems like selected products are not Storable products."))

        if self.export_method == "direct":
            return self.export_direct_in_woo(product_templates)
        return self.export_product_file_create_in_woo(product_templates)

    def export_product_file_create_in_woo(self, odoo_template_ids):
        """
        Create and download CSV/XLSX file for export product in WooCommerce.
        """
        data = str()
        templates_val = []
        if self.export_method:
            for odoo_template in odoo_template_ids:
                if len(odoo_template.product_variant_ids.ids) == 1 and not odoo_template.default_code:
                    continue
                position = 0
                for product in odoo_template.product_variant_ids.filtered(lambda variant: variant.default_code):
                    val = self.prepare_row_for_csv(odoo_template, product, position)
                    templates_val.append(val)
                    position = 1

            if not templates_val:
                raise UserError(
                    _("No data found to be exported.\n\nPossible Reasons:\n - SKU(s) are not set properly."))
            # Based on customer's selected file format apply to call method
            method_name = "_export_{}".format(self.export_method)
            if hasattr(self, method_name):
                data = getattr(self, method_name)(templates_val)
        self.write({'csv_data': data.get('file')})
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=woo.prepare.product.for.export.ept&'
                   'field=csv_data&download=true&id={}&filename={}'.format(self.id, data.get('file_name')),
            'target': 'self',
        }

    def _export_csv(self, products):
        """
        This method use for export selected product in CSV file for Map product
        Develop by : Meera Sidapara
        Date : 02/12/2021
        :param products: Selected product listing ids
        :return: selected product data and file name
        """
        buffer = StringIO()
        csv_writer = DictWriter(buffer, list(products[0].keys()), delimiter=',')
        csv_writer.writer.writerow(list(products[0].keys()))
        csv_writer.writerows(products)
        buffer.seek(0)
        file_data = buffer.read().encode("utf-8")
        b_data = base64.b64encode(file_data)
        filename = 'woo_product_export_{}_{}.csv'.format(self.id, datetime.now().strftime(
            "%m_%d_%Y-%H_%M_%S"))
        return {'file': b_data, 'file_name': filename}

    def _export_xlsx(self, products):
        """
        This method use for export selected product in XLSX file for Map product
        Develop by : Meera Sidapara
        Date : 02/12/2021
        :param products: Selected product listing ids
        :return: selected product data and file name
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Map Product')
        header = list(products[0].keys())
        header_format = workbook.add_format({'bold': True, 'font_size': 10})
        general_format = workbook.add_format({'font_size': 10})
        worksheet.write_row(0, 0, header, header_format)
        index = 0
        for product in products:
            index += 1
            worksheet.write_row(index, 0, list(product.values()), general_format)
        workbook.close()
        b_data = base64.b64encode(output.getvalue())
        filename = 'woo_product_export_{}_{}.xlsx'.format(self.id, datetime.now().strftime(
            "%m_%d_%Y-%H_%M_%S"))
        return {'file': b_data, 'file_name': filename}

    def export_direct_in_woo(self, product_templates):
        """
        This method use to create/update Woo layer products.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
        Task_id: 165896
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_template_id = False
        woo_product_obj = self.env["woo.product.product.ept"]
        woo_template_obj = self.env["woo.product.template.ept"]
        woo_category_dict = {}
        variants = product_templates.product_variant_ids
        woo_instance = self.woo_instance_id

        for variant in variants:
            if not variant.default_code:
                continue
            woo_template = self.create_update_woo_template(variant, woo_instance, woo_template_id, woo_category_dict)

            # For add template images in layer.
            if isinstance(woo_template, int):
                woo_template = woo_template_obj.browse(woo_template)

            self.create_woo_template_images(woo_template)

            woo_variant = woo_product_obj.search([('woo_instance_id', '=', woo_instance.id),
                                                  ('product_id', '=', variant.id),
                                                  ('woo_template_id', '=', woo_template.id)])
            woo_variant_vals = self.prepare_variant_vals_for_woo_layer(woo_instance, variant, woo_template)
            if not woo_variant:
                woo_variant = woo_product_obj.create(woo_variant_vals)
            else:
                woo_variant.write(woo_variant_vals)
            # For adding all odoo images into Woo layer.
            self.create_woo_variant_images(woo_template, woo_variant)

        return True

    def create_update_woo_template(self, variant, woo_instance, woo_template_id, woo_category_dict):
        """
        This method is used create/update woo template.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_template_obj = self.env["woo.product.template.ept"]
        product_template = variant.product_tmpl_id

        if product_template.attribute_line_ids and len(
                product_template.attribute_line_ids.filtered(lambda x: x.attribute_id.create_variant == "always")) > 0:
            product_type = 'variable'
        else:
            product_type = 'simple'

        woo_template = woo_template_obj.search([
            ("woo_instance_id", "=", woo_instance.id),
            ("product_tmpl_id", "=", product_template.id)])

        woo_template_vals = self.prepare_woo_template_layer_vals(woo_instance, product_template, product_type)

        if product_template.categ_id:
            self.create_categ_in_woo(product_template.categ_id, woo_instance.id, woo_category_dict)
            woo_categ_id = self.update_category_info(product_template.categ_id, woo_instance.id)
            woo_template_vals.update({'woo_categ_ids': [(6, 0, woo_categ_id.ids)]})

        if not woo_template:
            woo_template = woo_template_obj.create(woo_template_vals)
            woo_template_id = woo_template.id
        else:
            if woo_template_id != woo_template.id:
                woo_template.write(woo_template_vals)
                woo_template_id = woo_template.id

        self.set_value_base_on_language(product_template, woo_instance, woo_template_vals, woo_template)
        return woo_template_id

    def set_value_base_on_language(self, product_template, woo_instance, woo_template_vals, woo_template):
        """
        This method is used to set value based active languages
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 26 July 2022.
        Task_id: 196584 - Woo language issue.
        """
        translated_template_vals = {
            "name": product_template.with_context(lang=woo_instance.woo_lang_id.code).name,
        }
        if woo_template_vals.get('woo_description') and woo_template_vals.get("woo_short_description"):
            translated_template_vals.update(
                {"woo_description": product_template.with_context(
                    lang=woo_instance.woo_lang_id.code).description_sale if not is_html_empty(
                    product_template.description_sale) else '',
                 "woo_short_description": product_template.with_context(
                     lang=woo_instance.woo_lang_id.code).description if not is_html_empty(
                     product_template.description) else ''})
        woo_template.with_context(lang=woo_instance.woo_lang_id.code).write(translated_template_vals)
        return True

    def prepare_woo_template_layer_vals(self, woo_instance, product_template, product_type):
        """
        This method is used to prepare a vals for the woo product template.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_config_parameter_obj = self.env["ir.config_parameter"]
        woo_template_vals = (
            {
                'product_tmpl_id': product_template.id,
                'woo_instance_id': woo_instance.id,
                'name': product_template.name,
                'woo_product_type': product_type
            })

        if ir_config_parameter_obj.sudo().get_param("woo_commerce_ept.set_sales_description"):
            woo_template_vals.update({"woo_description": product_template.description_sale,
                                      "woo_short_description": product_template.description})

        return woo_template_vals

    def prepare_variant_vals_for_woo_layer(self, woo_instance, variant, woo_template):
        """
        This method is used to prepare variant vals for the create/update woo layer variant.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_variant_vals = ({
            'woo_instance_id': woo_instance.id,
            'product_id': variant.id,
            'woo_template_id': woo_template.id,
            'default_code': variant.default_code,
            'name': variant.name,
        })
        return woo_variant_vals

    def prepare_row_for_csv(self, odoo_template, product, position):
        """
        This method use to prepare a template data row for export data in CSV file.
        @param : self, odoo_template, product, position
        @return: row
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
        Task_id: 165896
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        row = {
            'template_name': odoo_template.name,
            'product_name': product.name,
            'product_default_code': product.default_code,
            'woo_product_default_code': product.default_code,
            'product_description': product.description if position == 0 else '',
            'sale_description': product.description_sale if position == 0 else '',
            'PRODUCT_TEMPLATE_ID': odoo_template.id,
            'PRODUCT_ID': product.id,
            'CATEGORY_ID': odoo_template.categ_id.id if position == 0 else '',
        }
        return row

    def create_categ_in_woo(self, category_id, instance, woo_category_dict, ctg_list=[]):
        """
        This method is used for find the parent category and its sub category based on category id and
        create or update the category in woo second layer of woo category model.
        :param categ_id: It contain the product category and its type is object
        :param instance: It contain the browsable object of the current instance
        :param ctg_list: It contain the category ids list
        :return: It will return True if the product category successful complete
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_categ = self.env['woo.product.categ.ept']
        product_category_obj = self.env['product.category']
        if category_id:
            ctg_list.append(category_id.id)
            self.create_categ_in_woo(category_id.parent_id, instance, woo_category_dict, ctg_list=ctg_list)
        else:
            for categ_id in list(OrderedDict.fromkeys(reversed(ctg_list))):
                if woo_category_dict.get((categ_id, instance)):
                    continue
                list_categ_id = product_category_obj.browse(categ_id)
                parent_category = list_categ_id.parent_id
                woo_product_parent_categ = parent_category and self.search_woo_category(parent_category.name, instance)
                if woo_product_parent_categ:
                    woo_product_category = self.search_woo_category(list_categ_id.name, instance,
                                                                    woo_product_parent_categ)
                    woo_category_dict.update({(categ_id, instance): woo_product_category.id})
                else:
                    woo_product_category = self.search_woo_category(list_categ_id.name, instance)
                    woo_category_dict.update({(categ_id, instance): woo_product_category.id})
                if not woo_product_category:
                    if not parent_category:
                        parent_id = self.create_woo_category(list_categ_id.name, instance)
                        woo_category_dict.update({(categ_id, instance): parent_id.id})
                    else:
                        parent_id = self.search_woo_category(parent_category.name, instance)
                        woo_cat_id = self.create_woo_category(list_categ_id.name, instance, parent_id)
                        woo_category_dict.update({(categ_id, instance): woo_cat_id.id})
                elif not woo_product_category.parent_id and parent_category:
                    parent_id = self.search_woo_category(parent_category.name, instance, woo_product_parent_categ)
                    if not parent_id:
                        woo_cat_id = self.create_woo_category(list_categ_id.name, instance, parent_id)
                        woo_category_dict.update({(categ_id, instance): woo_cat_id.id})
                    if not parent_id.parent_id.id == woo_product_category.id and woo_product_categ.woo_instance_id.id == \
                            instance:
                        woo_product_category.write({'parent_id': parent_id.id})
                        woo_category_dict.update({(categ_id, instance): parent_id.id})
        return woo_category_dict

    def search_woo_category(self, category_name, instance, parent_id=False):
        """
        This method is used to search woo layer category.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_categ = self.env['woo.product.categ.ept']
        domain = [('name', '=', category_name), ('woo_instance_id', '=', instance)]
        if parent_id:
            domain.append(("parent_id", "=", parent_id.id))
        woo_categ = woo_product_categ.search(domain, limit=1)

        return woo_categ

    def create_woo_category(self, category_name, instance, parent_id=False):
        """
        This method is used to create a category in the Woo layer.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_categ = self.env['woo.product.categ.ept']
        vals = {'name': category_name, 'woo_instance_id': instance}
        if parent_id:
            vals.update({'parent_id': parent_id.id})
        woo_categ_id = woo_product_categ.create(vals)

        return woo_categ_id

    def update_category_info(self, categ_obj, instance_id):
        """
        This methos is used for create a new category in woo connector or update the existing category.
        :param categ_obj: It contain the product category and its type is object
        :param instance_id: It contain the browsable object of the current instance
        :return: It will return browsable category object
        @author: Dipak Gogiya @Emipro Technologies Pvt. Ltd
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_categ = self.env['woo.product.categ.ept']
        woo_categ_id = woo_product_categ.search([('name', '=', categ_obj.name),
                                                 ('woo_instance_id', '=', instance_id)], limit=1)
        if not woo_categ_id:
            woo_categ_id = woo_product_categ.create({'name': categ_obj.name, 'woo_instance_id': instance_id})
        return woo_categ_id

    def create_woo_template_images(self, woo_template):
        """
        This method is use to create images in Woo layer.
        @param : self,woo_template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
        Task_id: 165896
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_image_list = []
        woo_product_image_obj = self.env["woo.product.image.ept"]
        common_product_image_obj = self.env["common.product.image.ept"]

        common_product_images = common_product_image_obj.search(
            [('template_id', '=', woo_template.product_tmpl_id.id)])
        images = common_product_images.filtered(lambda img: img.image == woo_template.product_tmpl_id.image_1920)
        if not images and woo_template.product_tmpl_id.image_1920:
            common_product_image_obj.create({
                "name": woo_template.name,
                "template_id": woo_template.product_tmpl_id.id,
                "image": woo_template.product_tmpl_id.image_1920,
            })

        product_template = woo_template.product_tmpl_id
        for odoo_image in product_template.ept_image_ids.filtered(lambda x: not x.product_id):
            woo_product_image = woo_product_image_obj.search_read(
                [("woo_template_id", "=", woo_template.id),
                 ("odoo_image_id", "=", odoo_image.id)], ["id"])
            if not woo_product_image:
                woo_product_image_list.append({
                    "odoo_image_id": odoo_image.id,
                    "woo_template_id": woo_template.id,
                    "image_mime_type": guess_mimetype(base64.b64decode(odoo_image.image)),
                })
        if woo_product_image_list:
            woo_product_image_obj.create(woo_product_image_list)
        return True

    def create_woo_variant_images(self, woo_template, woo_variant):
        """
        This method is use to create variant images in Woo layer.
        @param : self,woo_template
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 14 September 2020 .
        Task_id: 165896
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_product_image_obj = self.env["woo.product.image.ept"]
        common_product_image_obj = self.env["common.product.image.ept"]

        common_product_images = common_product_image_obj.search(
            [('product_id', '=', woo_variant.product_id.id)])

        images = common_product_images.filtered(lambda
                                                    img: img.image == woo_variant.product_id.image_1920 and img.product_id.id == woo_variant.product_id.id)
        if not images and woo_variant.product_id.image_1920:
            common_product_image_obj.create({
                "name": woo_template.name,
                "template_id": woo_template.product_tmpl_id.id,
                "image": woo_variant.product_id.image_1920,
                "product_id": woo_variant.product_id.id,
            })
        # product_id = woo_variant.product_id
        # odoo_image = product_id.ept_image_ids
        # if odoo_image:
        for variant_image in woo_variant.product_id.ept_image_ids:
            woo_product_image = woo_product_image_obj.search_read(
                [("woo_template_id", "=", woo_template.id),
                 ("woo_variant_id", "=", woo_variant.id),
                 ("odoo_image_id", "=", variant_image.id)], ["id"])
            if not woo_product_image:
                woo_product_image_obj.create({
                    "odoo_image_id": variant_image.id,
                    "woo_variant_id": woo_variant.id,
                    "woo_template_id": woo_template.id,
                    "image_mime_type": guess_mimetype(base64.b64decode(variant_image.image)),
                    "sequence": 0
                })
        return True
