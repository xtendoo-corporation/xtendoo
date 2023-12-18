# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging

import requests
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.web_editor.tools import get_video_embed_code
from odoo.exceptions import UserError

from .. import woocommerce

_logger = logging.getLogger("WooCommerce")


class WooInstanceConfig(models.TransientModel):
    _name = 'res.config.woo.instance'
    _description = "WooCommerce Res Config Instance"

    @api.model
    def _woo_tz_get(self):
        """
        Gives all timezones from base.
        @author: Maulik Barad on Date 18-Nov-2019.
        @return: Calls base method for all timezones.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        return _tz_get(self)

    name = fields.Char("Instance Name", help="Set the Instance Name.")
    woo_consumer_key = fields.Char("Consumer Key", required=True,
                                   help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> "
                                        "Advanced >> REST API >> Click on Add Key")
    woo_consumer_secret = fields.Char("Consumer Secret", required=True,
                                      help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings "
                                           ">> Advanced >> REST API >> Click on Add Key")
    woo_host = fields.Char("Host", required=True, help="URL of your WooCommerce Store.")
    is_export_update_images = fields.Boolean("Do you want to export/update Images?", default=False,
                                             help="Check this if you want to export/update product images from Odoo "
                                                  "to Woocommerce store.")
    woo_admin_username = fields.Char("Username", help="WooCommerce username for exporting Image files.")
    woo_admin_password = fields.Char("Password", help="WooCommerce password for exporting Image files.")
    woo_version = fields.Selection([("v3", "Below 2.6"), ("wc/v1", "2.6 To 2.9"),
                                    ("wc/v2", "3.0 To 3.4"), ("wc/v3", "3.5+")],
                                   default="wc/v3", string="WooCommerce Version",
                                   help="Set the appropriate WooCommerce Version you are using currently or\n"
                                        "Login into WooCommerce site,Go to Admin Panel >> Plugins")
    woo_verify_ssl = fields.Boolean("Verify SSL", default=False, help="Check this if your WooCommerce site is using SSL"
                                                                      " certificate")
    store_timezone = fields.Selection("_woo_tz_get", help="Timezone of Store for requesting data.")
    woo_company_id = fields.Many2one("res.company", string="Woo Instance Company",
                                     help="Orders and Invoices will be generated of this company.")

    woo_instance_video_url = fields.Char('Video URL',
                                         default='https://www.youtube.com/watch?v=hctH0-SLwcA&'
                                                 'list=PLZGehiXauylYm3npB78qUh0bPULqC-qo-&index=1',
                                         help='URL of a video for showcasing by instance.')
    woo_instance_video_embed_code = fields.Html(compute="_compute_woo_instance_video_embed_code", sanitize=False)

    @api.depends('woo_instance_video_url')
    def _compute_woo_instance_video_embed_code(self):
        for image in self:
            image.woo_instance_video_embed_code = get_video_embed_code(image.woo_instance_video_url)

    def woo_test_connection(self):
        """
        This method is used to check the connection between Odoo and Woocommerce store.
        If the connection is a success then it will create an instance.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        instance_obj = self.env['woo.instance.ept']
        payment_gateway_obj = self.env['woo.payment.gateway']
        shipping_method_obj = self.env['woo.shipping.method']
        host = self.woo_host
        consumer_key = self.woo_consumer_key
        consumer_secret = self.woo_consumer_secret
        verify_ssl = self.woo_verify_ssl
        version = self.woo_version
        # Check the connection between Odoo and Woocommerce store.
        self.request_connection_check(version, host, consumer_key, consumer_secret, verify_ssl)

        if self.is_export_update_images:
            # Checking if username and password are correct or not.
            instance_obj.check_credentials_for_image(self.woo_admin_username, self.woo_admin_password, host)

        instance_vals = self.prepare_val_for_instance_create(consumer_key, consumer_secret, host, verify_ssl, version)
        instance = instance_obj.create(instance_vals)

        if instance.woo_version in ["wc/v2", "wc/v3"]:
            payment_gateway_obj.woo_get_payment_gateway(instance)
            shipping_method_obj.woo_get_shipping_method(instance)
        instance.confirm()

        if self._context.get('is_calling_from_onboarding_panel', False):
            company = instance.company_id
            instance.write({'is_instance_create_from_onboarding_panel': True})
            company.set_onboarding_step_done('woo_instance_onboarding_state')
            company.write({'is_create_woo_more_instance': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def request_connection_check(self, version, host, consumer_key, consumer_secret, verify_ssl):
        """
        This method is used to check the connection between Odoo and Woocommmerce.
        :param version: Woocommerce version
        :param host: URL of store.
        :param consumer_key: Consumer key of Store.
        :param consumer_secret: Consumer secret key of Store.
        :param verify_ssl: True if WooCommerce site is using SSL certificate else False
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 November 2020 .
        Task_id: 168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        wp_api = not version == 'v3'
        wcapi = woocommerce.api.API(url=host, consumer_key=consumer_key, consumer_secret=consumer_secret,
                                    verify_ssl=verify_ssl, wp_api=wp_api, version=version, query_string_auth=True)
        try:
            response = wcapi.get("products", params={"_fields": "id"})
        except Exception as error:
            raise UserError(_(error))
        if not isinstance(response, requests.models.Response):
            raise UserError(_("Response is not in proper format :: %s")) % response
        if response.status_code != 200:
            raise UserError(_("%s\n%s") % (response.status_code, response.reason))

    def prepare_val_for_instance_create(self, consumer_key, consumer_secret, host, verify_ssl, version):
        """
        It used to prepare a vals for create a instance.
        @return: instance_vals
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 November 2020 .
        Task_id: 168147 - Code refactoring : 5th - 6th November
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        stock_warehouse_obj = self.env['stock.warehouse']
        warehouse = stock_warehouse_obj.search([('company_id', '=', self.woo_company_id.id)], limit=1, order='id')
        instance_vals = {'name': self.name,
                         'woo_consumer_key': consumer_key,
                         'woo_consumer_secret': consumer_secret,
                         'woo_host': host,
                         'woo_verify_ssl': verify_ssl,
                         'company_id': self.woo_company_id.id,
                         'woo_warehouse_id': warehouse.id,
                         'woo_version': version,
                         "store_timezone": self.store_timezone,
                         'woo_admin_username': self.woo_admin_username,
                         'woo_admin_password': self.woo_admin_password,
                         'is_export_update_images': self.is_export_update_images
                         }
        return instance_vals

    def test_and_reset_woo_credentials(self):
        """
        This method used to check connection and reset credentials.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 1 October 2020 .
        Task_id: 166949
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_instance_obj = self.env['woo.instance.ept']
        instance = woo_instance_obj.browse(self._context.get('active_id'))
        self.request_connection_check(instance.woo_version, instance.woo_host, self.woo_consumer_key,
                                      self.woo_consumer_secret, instance.woo_verify_ssl)
        if self.is_export_update_images:
            """Checking if username and password are correct or not."""
            instance.check_credentials_for_image(self.woo_admin_username, self.woo_admin_password)
        if self._context.get('is_test_connection'):
            title = _("Woo Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }
        credentials = {'woo_consumer_key': self.woo_consumer_key,
                       'woo_consumer_secret': self.woo_consumer_secret,
                       'store_timezone': self.store_timezone,
                       'is_export_update_images': False,
                       'woo_admin_username': False,
                       'woo_admin_password': False}

        if self.is_export_update_images:
            credentials.update({'woo_admin_username': self.woo_admin_username,
                                'woo_admin_password': self.woo_admin_password,
                                'is_export_update_images': True
                                })
        instance.write(credentials)
        return True

    @api.model
    def action_open_woo_instance_wizard(self):
        """ Called by onboarding panel above the Instance."""
        ir_action_obj = self.env["ir.actions.actions"]
        instance_obj = self.env['woo.instance.ept']
        action = ir_action_obj._for_xml_id(
            "woo_commerce_ept.woo_on_board_instance_configuration_action")
        action['context'] = {'is_calling_from_onboarding_panel': True}
        instance = instance_obj.search_woo_instance()
        if instance:
            action.get('context').update({
                'default_name': instance.name,
                'default_woo_host': instance.woo_host,
                'default_store_timezone': instance.store_timezone,
                'default_woo_company_id': instance.company_id.id,
                'default_woo_consumer_key': instance.woo_consumer_key,
                'default_woo_consumer_secret': instance.woo_consumer_secret,
                'default_woo_verify_ssl': instance.woo_verify_ssl,
                'default_is_export_update_images': instance.is_export_update_images,
                'default_woo_admin_username': instance.woo_admin_username,
                'default_woo_admin_password': instance.woo_admin_password,
                'is_already_instance_created': True,
            })
            company = instance.company_id
            if company.woo_instance_onboarding_state != 'done':
                company.set_onboarding_step_done('woo_instance_onboarding_state')
        return action


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_woo_default_financial_statuses(self):
        if self._context.get('default_woo_instance_id', False):
            financial_status_ids = self.env['woo.sale.auto.workflow.configuration'].search(
                [('woo_instance_id', '=', self._context.get('default_woo_instance_id', False))]).ids
            return [(6, 0, financial_status_ids)]
        return [(6, 0, [])]

    woo_instance_id = fields.Many2one('woo.instance.ept', 'Woo Instance',
                                      help="Select WooCommerce Instance that you want to configure.")
    woo_company_id = fields.Many2one('res.company', string='Woo Company',
                                     default=lambda self: self.env.company,
                                     help="Orders and Invoices will be generated of this company.")
    woo_warehouse_id = fields.Many2one('stock.warehouse', string="Woo Warehouse",
                                       domain="[('company_id','=',woo_company_id)]",
                                       help="Stock Management, Order Processing & Fulfillment will be carried out "
                                            "from this warehouse.")
    woo_lang_id = fields.Many2one('res.lang', string='Woo Instance Language',
                                  help="Select language for WooCommerce customer.")
    woo_stock_field = fields.Many2one("ir.model.fields",
                                      help="Choose the field by which you want to update the stock in WooCommerce "
                                           "based on Free To Use(Quantity On Hand - Outgoing + Incoming) or "
                                           "Forecasted Quantity (Quantity On Hand - Reserved quantity).")

    woo_pricelist_id = fields.Many2one('product.pricelist', string='Woo Instance Pricelist',
                                       help="During product sync operation,regular price will be"
                                            "Imported/Exported using this Pricelist. This pricelist will"
                                            " apply in WooCommerce Order")
    woo_extra_pricelist_id = fields.Many2one('product.pricelist', string='Extra Pricelist',
                                             help="During product sync operation,sale price will be "
                                                  "Imported/Exported using this Pricelist")
    woo_payment_term_id = fields.Many2one('account.payment.term', string='Woo Instance Payment Term',
                                          help="Select the condition of payment for invoice.")
    woo_auto_import_product = fields.Boolean(
        string="Automatically Create Odoo Products If Not Found?",
        help="This option creates a new product in your Odoo catalog "
             "if system couldn't find the product based on SKU Internal "
             "Reference Default Product Code. If you are selling on multiple "
             "sales channels and having different SKU / Internal Reference / "
             "Default Product Code on each sales channel, it may lead to creation "
             "of duplicate products in your product catalogue in your database. "
             "- So we request you to enable this option, as per your product "
             "catalogue configuration")
    woo_sync_price_with_product = fields.Boolean("Woo Sync/Import Product Price?",
                                                 help="If checked, it will set the product price in the pricelist "
                                                      "configured under the given instance, while product import "
                                                      "process else not",
                                                 default=False)
    woo_sync_images_with_product = fields.Boolean("Woo Sync/Import Images?",
                                                  help="Check if you want to import images along "
                                                       "with products.", default=False)
    # For Orders.
    woo_import_order_status_ids = fields.Many2many('import.order.status.ept',
                                                   'woo_config_settings_order_status_rel', 'woo_config_id', 'status_id',
                                                   help="Select Order Status of the type of orders"
                                                        "you want to import from WooCommerce.")
    woo_sales_team_id = fields.Many2one('crm.team',
                                        help="Choose Sales Team that handles the order you import.")
    woo_custom_order_prefix = fields.Boolean("Use Odoo Default Sequence in Woo Orders?",
                                             help="If checked, it will set default order sequence in sale order. "
                                                  "If unchecked, it will set WooCommerce order number with given prefix")
    woo_order_prefix = fields.Char(size=10, help="Custom order prefix for Woocommerce orders.")
    woo_apply_tax = fields.Selection([("odoo_tax", "Odoo Default Tax"),
                                      ("create_woo_tax", "Create new tax if not found")],
                                     default="create_woo_tax", copy=False,
                                     help=""" For Woocommerce Orders :-
        1) Odoo Default Tax Behaviour - The Taxes will be set based on Odoo's default functional behavior i.e. based on
        Odoo's Tax and Fiscal Position configurations.
        2) Create New Tax If Not Found - System will search the tax data received from Woocommerce in Odoo, 
        will create a new one if it fails in finding it."""
                                     )
    woo_invoice_tax_account_id = fields.Many2one('account.account',
                                                 string="Invoice Tax Account For Woo Tax",
                                                 help="Tax Account to set in Invoice.")
    woo_credit_note_tax_account_id = fields.Many2one('account.account',
                                                     string="Credit Note Tax Account For Woo Tax",
                                                     help="Tax Account to set in Credit Note.")
    woo_user_ids = fields.Many2many('res.users', string="Responsible Users",
                                    help="To whom the activities will be assigned.")
    woo_activity_type_id = fields.Many2one('mail.activity.type', string="Woo Activity Type",
                                           help="Type of activity which you can set")
    woo_date_deadline = fields.Integer('Woo Deadline Lead Days',
                                       help="Days, that will be added in Schedule activity as Deadline days.")
    woo_is_create_schedule_activity = fields.Boolean(string="Is Create Schedule Activity?",
                                                     help="If marked, it will create a schedule activity of mismatch "
                                                          "details of critical situations.")
    create_woo_product_webhook = fields.Boolean("Manage Woo Products via Webhooks",
                                                help="True : It will create all product related webhooks.\nFalse : "
                                                     "All product related webhooks will be deactivated.")
    create_woo_customer_webhook = fields.Boolean("Manage Woo Customers via Webhooks",
                                                 help="True : It will create all customer related webhooks.\nFalse : "
                                                      "All customer related webhooks will be deactivated.")
    create_woo_order_webhook = fields.Boolean("Manage Woo Orders via Webhooks",
                                              help="True : It will create all order related webhooks.\nFalse : All "
                                                   "order related webhooks will be deactivated.")
    create_woo_coupon_webhook = fields.Boolean("Manage Coupons via Webhooks",
                                               help="True : It will create all coupon related webhooks.\nFalse : All "
                                                    "coupon related webhooks will be deactivated.")
    woo_attribute_type = fields.Selection([("select", "Select"), ("text", "Text")], string="Attribute Type",
                                          default="select",
                                          help="Select Attribute type for exporting attributes while exporting"
                                               "/updating products from Odoo to WooCommerce. 1) Select : It "
                                               "will create attribute at Global level at WooCommerce Store, "
                                               "which will be accessible across all products. 2) Text : It "
                                               "will add attribute in particular product. So, the attribute "
                                               "and its values will be exclusively available for that individual "
                                               "product and will not be shared with any other product.")
    woo_weight_uom_id = fields.Many2one("uom.uom", string="WooCommerce Weight Unit",
                                        domain=lambda self: [
                                            ("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)],
                                        help="Select Weight unit same as WooCommerce Store for setting "
                                             "proper Weight in Product. - If this value is "
                                             "different than what is configured in Odoo, system will do "
                                             "the conversion between both units of measure and then "
                                             "perform the Import/Export Operation of Products")
    woo_set_sales_description_in_product = fields.Boolean("Use Sales Description of Odoo Product",
                                                          config_parameter="woo_commerce_ept.set_sales_description",
                                                          help="In both odoo products and Woocommerce layer products, "
                                                               "it is used to set the description. For more details, "
                                                               "please read the following summary.")
    woo_tax_rounding_method = fields.Selection(
        [("round_per_line", "Round per Line"), ("round_globally", "Round Globally")], default="round_per_line",
        help="1) Round per Line: If it select then it will round tax amount per order line."
             "2) Round Globally: If it select then it will round tax amount on order total.")

    woo_financial_status_ids = fields.Many2many(
        'woo.sale.auto.workflow.configuration',
        'woo_sale_auto_workflow_conf_rel',
        'financial_onboarding_status_id', 'wokflow_id',
        string='Woo Financial Status', default=_get_woo_default_financial_statuses)
    woo_import_order_after_date = fields.Datetime(string="WooCommerce Import Order After Date",
                                                  help="Connector only imports those orders which have created "
                                                       "after a given date.")
    # Analytic
    woo_analytic_account_id = fields.Many2one('account.analytic.account', string='Woo Analytic Account',
                                              domain="['|', ('company_id', '=', False), ('company_id', '=', woo_company_id)]",
                                              help="Set the Analytic Account for WooCommerce orders. Note :- The "
                                                   "configuration of the analytic account for this instance will "
                                                   "be applied to all sales orders created by the connector. With"
                                                   "this configuration, the Analytic Default Rule configured in"
                                                   "Odoo will not apply to WooCommerce orders Invoices. If you "
                                                   "wish to use Odoo Analytic Default Rule, you will not have to "
                                                   "configure any analytic account here.")
    is_woo_digest = fields.Boolean(help="If checked, then it will send periodic digest per KPI.")

    woo_stock_export_warehouse_ids = fields.Many2many("stock.warehouse", string="Stock Export Warehouse",
                                                      help="Stock Management will be carried out from this warehouse.")

    show_woo_net_profit_report = fields.Boolean(config_parameter="woo_commerce_ept.show_woo_net_profit_report")
    woo_import_partner_as_company = fields.Boolean(
        help="If checked, it will create an individual Company type partner from the Company"
             "name and customer will be created as a child partner of Company.")
    woo_instance_product_categ_id = fields.Many2one("product.category", string="Product Category",
                                                    help="This category will set on new create products.")
    use_default_terms_and_condition_of_odoo = fields.Boolean("Use Default Terms & Condition of Odoo",
                                                             config_parameter="woo_commerce_ept.use_default_terms_and_condition_of_odoo",
                                                             help="If checked, it will set the custom note and default terms and condition in order note")

    @api.onchange('woo_instance_id')
    def onchange_woo_instance_id(self):
        """
        This method is to set data in Woocommerce configuration base in onchange of instance.
        """
        instance = self.woo_instance_id or False

        if instance:
            self.woo_lang_id = instance.woo_lang_id.id if instance.woo_lang_id else False
            self.woo_stock_field = instance.woo_stock_field.id if instance.woo_stock_field else False
            self.woo_warehouse_id = instance.woo_warehouse_id.id if instance.woo_warehouse_id else False
            self.woo_pricelist_id = instance.woo_pricelist_id.id if instance.woo_pricelist_id else False
            self.woo_extra_pricelist_id = instance.woo_extra_pricelist_id
            self.woo_payment_term_id = instance.woo_payment_term_id.id if instance.woo_payment_term_id else False
            self.woo_auto_import_product = instance.auto_import_product
            self.woo_sync_price_with_product = instance.sync_price_with_product or False
            self.woo_sync_images_with_product = instance.sync_images_with_product or False
            self.woo_company_id = instance.company_id.id if instance.company_id else False

            self.woo_import_order_status_ids = instance.import_order_status_ids.ids
            self.woo_sales_team_id = instance.sales_team_id
            self.woo_auto_import_product = instance.auto_import_product
            self.woo_custom_order_prefix = instance.custom_order_prefix
            self.woo_order_prefix = instance.order_prefix
            self.woo_apply_tax = instance.apply_tax
            self.woo_invoice_tax_account_id = instance.invoice_tax_account_id
            self.woo_credit_note_tax_account_id = instance.credit_note_tax_account_id
            self.woo_user_ids = instance.user_ids or False
            self.woo_activity_type_id = instance.activity_type_id
            self.woo_date_deadline = instance.date_deadline
            self.woo_is_create_schedule_activity = instance.is_create_schedule_activity

            self.create_woo_product_webhook = instance.create_woo_product_webhook
            self.create_woo_customer_webhook = instance.create_woo_customer_webhook
            self.create_woo_order_webhook = instance.create_woo_order_webhook
            self.create_woo_coupon_webhook = instance.create_woo_coupon_webhook

            self.woo_attribute_type = instance.woo_attribute_type
            self.woo_weight_uom_id = instance.weight_uom_id
            self.woo_tax_rounding_method = instance.tax_rounding_method
            self.woo_import_order_after_date = instance.import_order_after_date
            self.woo_analytic_account_id = instance.woo_analytic_account_id.id \
                if instance.woo_analytic_account_id else False
            self.is_woo_digest = instance.is_woo_digest or False
            self.woo_stock_export_warehouse_ids = instance.woo_stock_export_warehouse_ids.ids
            self.woo_import_partner_as_company = instance.import_partner_as_company
            self.woo_instance_product_categ_id = instance.woo_instance_product_categ_id.id if instance.woo_instance_product_categ_id else False

    def execute(self):
        """
        This method is used to set the configured values in the Instance.
        """
        instance = self.woo_instance_id
        values = {}
        res = super(ResConfigSettings, self).execute()
        IrModule = self.env['ir.module.module']
        exist_module = IrModule.search(
            [('name', '=', 'woo_commerce_net_profit_report_ept'), ('state', '=', 'installed')])
        if instance:
            values['woo_lang_id'] = self.woo_lang_id.id if self.woo_lang_id else False
            values['woo_stock_field'] = self.woo_stock_field.id if self.woo_stock_field else False
            values['woo_warehouse_id'] = self.woo_warehouse_id.id if self.woo_warehouse_id else False
            values['woo_pricelist_id'] = self.woo_pricelist_id.id if self.woo_pricelist_id else False
            values['woo_extra_pricelist_id'] = self.woo_extra_pricelist_id.id if self.woo_extra_pricelist_id else False
            values[
                'woo_payment_term_id'] = self.woo_payment_term_id.id if self.woo_payment_term_id else False
            values['sync_price_with_product'] = self.woo_sync_price_with_product or False
            values['sync_images_with_product'] = self.woo_sync_images_with_product or False
            values['company_id'] = self.woo_company_id.id if self.woo_company_id else False

            values['import_order_status_ids'] = [(6, 0, self.woo_import_order_status_ids.ids)]
            values['sales_team_id'] = self.woo_sales_team_id or False
            values['auto_import_product'] = self.woo_auto_import_product or False
            values['custom_order_prefix'] = self.woo_custom_order_prefix or False
            values['order_prefix'] = self.woo_order_prefix or False
            values["apply_tax"] = self.woo_apply_tax
            values["invoice_tax_account_id"] = self.woo_invoice_tax_account_id
            values["credit_note_tax_account_id"] = self.woo_credit_note_tax_account_id
            values["activity_type_id"] = self.woo_activity_type_id.id if self.woo_activity_type_id else False
            values["date_deadline"] = self.woo_date_deadline or False
            values.update({'user_ids': [(6, 0, self.woo_user_ids.ids)]})
            values['is_create_schedule_activity'] = self.woo_is_create_schedule_activity

            values["create_woo_product_webhook"] = self.create_woo_product_webhook
            values["create_woo_customer_webhook"] = self.create_woo_customer_webhook
            values["create_woo_order_webhook"] = self.create_woo_order_webhook
            values["create_woo_coupon_webhook"] = self.create_woo_coupon_webhook

            values["woo_attribute_type"] = self.woo_attribute_type
            values["weight_uom_id"] = self.woo_weight_uom_id
            values["tax_rounding_method"] = self.woo_tax_rounding_method
            values["import_order_after_date"] = self.woo_import_order_after_date
            values["woo_analytic_account_id"] = self.woo_analytic_account_id or False
            # values["woo_analytic_tag_ids"] = [(6, 0, self.woo_analytic_tag_ids.ids)]
            values['is_woo_digest'] = self.is_woo_digest or False
            values["woo_stock_export_warehouse_ids"] = [(6, 0, self.woo_stock_export_warehouse_ids.ids)]
            values["import_partner_as_company"] = self.woo_import_partner_as_company
            values["woo_instance_product_categ_id"] = self.woo_instance_product_categ_id or False

            product_webhook_changed = customer_webhook_changed = order_webhook_changed = coupon_webhook_changed = False
            if instance.create_woo_product_webhook != self.create_woo_product_webhook:
                product_webhook_changed = True
            if instance.create_woo_customer_webhook != self.create_woo_customer_webhook:
                customer_webhook_changed = True
            if instance.create_woo_order_webhook != self.create_woo_order_webhook:
                order_webhook_changed = True
            if instance.create_woo_coupon_webhook != self.create_woo_coupon_webhook:
                coupon_webhook_changed = True

            instance.write(values)

            if product_webhook_changed:
                instance.configure_woo_product_webhook()
            if customer_webhook_changed:
                instance.configure_woo_customer_webhook()
            if order_webhook_changed:
                instance.configure_woo_order_webhook()
            if coupon_webhook_changed:
                instance.configure_woo_coupon_webhook()

        if not self.show_woo_net_profit_report and exist_module:
            exist_module.with_user(SUPERUSER_ID).button_immediate_uninstall()

        return res

    def download_woo_net_profit_report_module(self):
        """
        This Method relocates download zip file of WooCommerce Net Profit Report module.
        @return: This Method return file download file.
        @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 26 August 2022.
        """
        attachment = self.env['ir.attachment'].search(
            [('name', '=', 'woo_commerce_net_profit_report_ept.zip')])
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
            'nodestroy': False,
        }

    @api.onchange("is_woo_digest")
    def onchange_is_woo_digest(self):
        """
        This method is used to create digest record based on woo instance.
        @author: Meera Sidapara on date 13-July-2022.
        @task: 194458 - Digest email development
        """
        try:
            digest_exist = self.env.ref('woocommerce_ept.digest_woo_instance_%d' % self.woo_instance_id.id)
        except:
            digest_exist = False
        if self.is_woo_digest:
            woo_cron = self.env['woo.cron.configuration.ept']
            vals = self.prepare_val_for_digest()
            if digest_exist:
                vals.update({'name': digest_exist.name})
                digest_exist.write(vals)
            else:
                core_record = woo_cron.search_cron_with_xml_id(
                    "common_connector_library.connector_digest_digest_default")

                new_instance_digest = core_record.copy(default=vals)
                name = 'digest_woo_instance_%d' % (self.woo_instance_id.id)
                self.create_digest_data(name, new_instance_digest)
        else:
            if digest_exist:
                digest_exist.write({'state': 'deactivated'})

    def prepare_val_for_digest(self):
        """ This method is used to prepare a vals for the digest configuration.
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 13 July 2022.
            Task_id: 194458 - Digest email development
        """
        vals = {'state': 'activated',
                'name': 'woo : ' + self.woo_instance_id.name + ' Periodic Digest',
                'module_name': 'woocommerce_ept',
                'woo_instance_id': self.woo_instance_id.id,
                'company_id': self.woo_instance_id.company_id.id}
        return vals

    def create_digest_data(self, name, new_instance_digest):
        """ This method is used to create a digest record of ir model data
            @author: Meera Sidapara @Emipro Technologies Pvt. Ltd on date 13 July 2022.
            Task_id: 194458 - Digest email development
        """
        self.env['ir.model.data'].create({'module': 'woocommerce_ept',
                                          'name': name,
                                          'model': 'digest.digest',
                                          'res_id': new_instance_digest.id,
                                          'noupdate': True})

    @api.model
    def action_woo_open_basic_configuration_wizard(self):
        """Called by onboarding panel above the Instance.
           Usage: return the action for open the basic configurations wizard
           @Task:  166918 - Odoo v14 : Dashboard analysis
           @author: Dipak Gogiya
           :return: True
        """

        try:
            view_id = self.env.ref('woo_commerce_ept.woo_basic_configurations_onboarding_wizard_view')
        except:
            return True
        return self.woo_res_config_view_action(view_id)

    @api.model
    def action_woo_open_financial_status_wizard(self):
        """
           Usage: return the action for open the basic configurations wizard
           @Task:  166918 - Odoo v14 : Dashboard analysis
           @author: Dipak Gogiya
           :return: True
        """
        """ Called by onboarding panel above the Instance."""
        try:
            view_id = self.env.ref('woo_commerce_ept.woo_financial_status_onboarding_wizard_view')
        except:
            return True
        return self.woo_res_config_view_action(view_id)

    def woo_res_config_view_action(self, view_id):
        """
           Usage: return the action for open the configurations wizard
           @Task:  166918 - Odoo v14 : Dashboard analysis
           @author: Dipak Gogiya
           :return: True
        """
        woo_instance_obj = self.env['woo.instance.ept']
        action = self.env["ir.actions.actions"]._for_xml_id(
            "woo_commerce_ept.action_woo_config")
        action_data = {'view_id': view_id.id, 'views': [(view_id.id, 'form')], 'target': 'new',
                       'name': 'Configurations'}
        instance = woo_instance_obj.search_woo_instance()
        if instance:
            action['context'] = {'default_woo_instance_id': instance.id}
        else:
            action['context'] = {}
        action.update(action_data)
        return action

    def woo_save_basic_configurations(self):
        """
           Usage: Save the basic condiguration changes in the instance
           @Task:  166918 - Odoo v14 : Dashboard analysis
           @author: Dipak Gogiya
           :return: True
        """
        instance = self.woo_instance_id
        if instance:
            basic_configuration_dict = {
                'woo_lang_id': self.woo_lang_id and self.woo_lang_id.id or False,
                'woo_warehouse_id': self.woo_warehouse_id and self.woo_warehouse_id.id or False,
                'auto_import_product': self.woo_auto_import_product,
                'sync_price_with_product': self.woo_sync_price_with_product or False,
                'sync_images_with_product': self.woo_sync_images_with_product or False,
                'company_id': self.woo_company_id and self.woo_company_id.id or False,
                'import_order_status_ids': [(6, 0, self.woo_import_order_status_ids.ids)],
                'sales_team_id': self.woo_sales_team_id or False,
                'custom_order_prefix': self.woo_custom_order_prefix or False,
                'order_prefix': self.woo_order_prefix or False,
                'apply_tax': self.woo_apply_tax,
                'invoice_tax_account_id': self.woo_invoice_tax_account_id,
                'credit_note_tax_account_id': self.woo_credit_note_tax_account_id,
                'woo_attribute_type': self.woo_attribute_type,
                'weight_uom_id': self.woo_weight_uom_id,
                'tax_rounding_method': self.woo_tax_rounding_method,
                'import_order_after_date': self.woo_import_order_after_date,
                'woo_pricelist_id': self.woo_pricelist_id,
                'woo_payment_term_id': self.woo_payment_term_id,
                'woo_analytic_account_id': self.woo_analytic_account_id and self.woo_analytic_account_id.id or False,
                # 'woo_analytic_tag_ids': [(6, 0, self.woo_analytic_tag_ids.ids)],
                "import_partner_as_company": self.woo_import_partner_as_company,
                "woo_stock_export_warehouse_ids": [(6, 0, self.woo_stock_export_warehouse_ids.ids)],
                "woo_extra_pricelist_id": self.woo_extra_pricelist_id.id,
                'woo_instance_product_categ_id': self.woo_instance_product_categ_id and self.woo_instance_product_categ_id.id or False,
            }

            instance.write(basic_configuration_dict)
            company = instance.company_id
            company.set_onboarding_step_done('woo_basic_configuration_onboarding_state')
        return True

    def woo_save_financial_status_configurations(self):
        """
            Usage: Save the changes in the Instance.
            @Task:  166918 - Odoo v14 : Dashboard analysis
            @author: Dipak Gogiya, 22/09/2020
            :return: True
        """
        sale_auto_workflow_configuration_obj = self.env['woo.sale.auto.workflow.configuration']
        instance = self.woo_instance_id
        if instance:
            product_webhook_changed = customer_webhook_changed = order_webhook_changed = coupon_webhook_changed = False
            if instance.create_woo_product_webhook != self.create_woo_product_webhook:
                product_webhook_changed = True
            if instance.create_woo_customer_webhook != self.create_woo_customer_webhook:
                customer_webhook_changed = True
            if instance.create_woo_order_webhook != self.create_woo_order_webhook:
                order_webhook_changed = True
            if instance.create_woo_coupon_webhook != self.create_woo_coupon_webhook:
                coupon_webhook_changed = True

            instance.write({
                "is_woo_digest": self.is_woo_digest,
                'woo_stock_field': self.woo_stock_field.id,
                'create_woo_product_webhook': self.create_woo_product_webhook,
                'create_woo_customer_webhook': self.create_woo_customer_webhook,
                'create_woo_order_webhook': self.create_woo_order_webhook,
                'create_woo_coupon_webhook': self.create_woo_coupon_webhook,
            })
            if product_webhook_changed:
                instance.configure_woo_product_webhook()
            if customer_webhook_changed:
                instance.configure_woo_customer_webhook()
            if order_webhook_changed:
                instance.configure_woo_order_webhook()
            if coupon_webhook_changed:
                instance.configure_woo_coupon_webhook()
            company = instance.company_id
            company.set_onboarding_step_done('woo_financial_status_onboarding_state')
            financials_status = sale_auto_workflow_configuration_obj.search(
                [('woo_instance_id', '=', instance.id)])
            unlink_for_financials_status = financials_status - self.woo_financial_status_ids
            unlink_for_financials_status.unlink()
        return True
