# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class WooCronConfigurationEpt(models.TransientModel):
    """
    Common model for managing cron configuration.
    """
    _name = "woo.cron.configuration.ept"
    _description = "WooCommerce Cron Configuration"

    def _get_woo_instance(self):
        """
        This method is used to get instance from context.
        :return: Instance
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd 16-Nov-2019
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        return self.env.context.get('active_id', False)

    woo_instance_id = fields.Many2one('woo.instance.ept', 'Woo Instance',
                                      default=_get_woo_instance, readonly=True)
    # auto stock process fields
    woo_stock_auto_export = fields.Boolean('Woo Stock Auto Update.', default=False,
                                           help="Check if you want to automatically update stock levels from Odoo to "
                                                "WooCommerce.")
    woo_update_stock_interval_number = fields.Integer(help="Repeat every x.", default=10)
    woo_update_stock_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                       ('hours', 'Hours'), ('days', 'Days'),
                                                       ('weeks', 'Weeks'), ('months', 'Months')],
                                                      'Woo Update Stock Interval Unit')
    woo_update_stock_next_execution = fields.Datetime(help='Next execution time')
    woo_update_stock_user_id = fields.Many2one('res.users', string="Woo User", help='Woo Stock Update User',
                                               default=lambda self: self.env.user)

    # Auto Import Order
    woo_auto_import_order = fields.Boolean("Auto Import Order from Woo?",
                                           help="Imports orders at certain interval.")

    woo_import_order_interval_number = fields.Integer(help="Repeat every x.", default=10)
    woo_import_order_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                       ('hours', 'Hours'),
                                                       ('days', 'Days'),
                                                       ('weeks', 'Weeks'),
                                                       ('months', 'Months')])
    woo_import_order_next_execution = fields.Datetime(help="Next execution time of Auto Import Order Cron.")
    woo_import_order_user_id = fields.Many2one('res.users',
                                               help="Responsible User for Auto imported orders.",
                                               default=lambda self: self.env.user)
    # Auto Import Complete Order
    woo_auto_import_complete_order = fields.Boolean("Auto Import Complete Order from Woo?",
                                                    help="Imports complete orders at certain interval.")

    woo_import_complete_order_interval_number = fields.Integer(help="Repeat every x.", default=10)
    woo_import_complete_order_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                                ('hours', 'Hours'),
                                                                ('days', 'Days'),
                                                                ('weeks', 'Weeks'),
                                                                ('months', 'Months')])
    woo_import_complete_order_next_execution = fields.Datetime(
        help="Next execution time of Auto Import Complete Order Cron.")
    woo_import_complete_order_user_id = fields.Many2one('res.users',
                                                        help="Responsible User for Auto imported complete orders.",
                                                        default=lambda self: self.env.user)

    # Auto Import Cancel Order
    woo_auto_import_cancel_order = fields.Boolean("Auto Import Cancel Order from Woo?",
                                                  help="Imports Cancel orders at certain interval.")

    woo_import_cancel_order_interval_number = fields.Integer(help="Repeat every x.", default=10)
    woo_import_cancel_order_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                              ('hours', 'Hours'),
                                                              ('days', 'Days'),
                                                              ('weeks', 'Weeks'),
                                                              ('months', 'Months')])
    woo_import_cancel_order_next_execution = fields.Datetime(
        help="Next execution time of Auto Import Cancel Order Cron.")
    woo_import_cancel_order_user_id = fields.Many2one('res.users',
                                                      help="Responsible User for Auto imported Cancel orders.",
                                                      default=lambda self: self.env.user)

    # Auto Update Order
    woo_auto_update_order_status = fields.Boolean(string="Auto Update Order Status in Woo?",
                                                  help="Automatically update order status to WooCommerce.")
    woo_update_order_status_interval_number = fields.Integer(help="Repeat every x.", default=10)
    woo_update_order_status_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                              ('hours', 'Hours'),
                                                              ('days', 'Days'),
                                                              ('weeks', 'Weeks'),
                                                              ('months', 'Months')])
    woo_update_order_status_next_execution = fields.Datetime(help="Next execution time of Auto Update Order Cron.")
    woo_update_order_status_user_id = fields.Many2one('res.users',
                                                      help="Responsible User for Auto updating order status.",
                                                      default=lambda self: self.env.user)

    @api.onchange("woo_instance_id")
    def onchange_woo_instance_id(self):
        """
        This method execute on change of instance.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd 16-Nov-2019
        :Task id: 156886
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        instance = self.woo_instance_id
        self.woo_stock_auto_export = instance.woo_stock_auto_export if instance else False
        self.woo_auto_import_order = instance.auto_import_order if instance else False
        self.woo_auto_import_complete_order = instance.auto_import_complete_order if instance else False
        self.woo_auto_import_cancel_order = instance.auto_import_cancel_order if instance else False
        self.woo_auto_update_order_status = instance.auto_update_order_status if instance else False

        inventory_cron = self.search_active_existing_cron('ir_cron_update_woo_stock_instance', instance)

        if inventory_cron:
            self.woo_update_stock_interval_number = inventory_cron.interval_number or False
            self.woo_update_stock_interval_type = inventory_cron.interval_type or False
            self.woo_update_stock_next_execution = inventory_cron.nextcall or False
            self.woo_update_stock_user_id = inventory_cron.user_id or False

        import_order_cron = self.search_active_existing_cron('ir_cron_woo_import_order_instance', instance)

        if import_order_cron:
            self.woo_import_order_interval_number = import_order_cron.interval_number
            self.woo_import_order_interval_type = import_order_cron.interval_type
            self.woo_import_order_next_execution = import_order_cron.nextcall
            self.woo_import_order_user_id = import_order_cron.user_id

        import_complete_order_cron = self.search_active_existing_cron('ir_cron_woo_import_complete_order_instance',
                                                                      instance)

        if import_complete_order_cron:
            self.woo_import_complete_order_interval_number = import_complete_order_cron.interval_number
            self.woo_import_complete_order_interval_type = import_complete_order_cron.interval_type
            self.woo_import_complete_order_next_execution = import_complete_order_cron.nextcall
            self.woo_import_complete_order_user_id = import_complete_order_cron.user_id

        import_cancel_order_cron = self.search_active_existing_cron('ir_cron_woo_import_cancel_order_instance',
                                                                    instance)

        if import_cancel_order_cron:
            self.woo_import_cancel_order_interval_number = import_cancel_order_cron.interval_number
            self.woo_import_cancel_order_interval_type = import_cancel_order_cron.interval_type
            self.woo_import_cancel_order_next_execution = import_cancel_order_cron.nextcall
            self.woo_import_cancel_order_user_id = import_cancel_order_cron.user_id

        update_order_status_cron = self.search_active_existing_cron('ir_cron_woo_update_order_status_instance',
                                                                    instance)
        if update_order_status_cron:
            self.woo_update_order_status_interval_number = update_order_status_cron.interval_number
            self.woo_update_order_status_interval_type = update_order_status_cron.interval_type
            self.woo_update_order_status_next_execution = update_order_status_cron.nextcall
            self.woo_update_order_status_user_id = update_order_status_cron.user_id

    def search_active_existing_cron(self, xml_id, instance):
        """
        This method is used to search the active existing cron job.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        return self.env.ref('woo_commerce_ept.%s_%d' % (xml_id, instance.id), raise_if_not_found=False)

    def save(self):
        """
        This method is used to save values of cron job in the instance.
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd 16-Nov-2019
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_action_obj = self.env["ir.actions.actions"]
        instance = self.woo_instance_id
        if instance:
            values = {"woo_stock_auto_export": self.woo_stock_auto_export,
                      "auto_import_order": self.woo_auto_import_order,
                      "auto_import_complete_order": self.woo_auto_import_complete_order,
                      "auto_import_cancel_order": self.woo_auto_import_cancel_order,
                      "auto_update_order_status": self.woo_auto_update_order_status}
            instance.write(values)
            self.setup_woo_update_stock_cron(instance)
            self.setup_woo_import_order_cron(instance)
            self.setup_woo_import_complete_order_cron(instance)
            self.setup_woo_update_order_status_cron(instance)
            self.setup_woo_import_cancel_order_cron(instance)
            # Below code is used for only onboarding panel purpose.
            if self._context.get('is_calling_from_onboarding_panel', False):
                action = ir_action_obj._for_xml_id(
                    "woo_commerce_ept.woo_onboarding_confirmation_wizard_action")
                action['context'] = {'woo_instance_id': instance.id}
                return action
        return True

    def setup_woo_import_order_cron(self, instance):
        """
        Configure the cron for auto import order.
        @author: Maulik Barad on Date 16-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if self.woo_auto_import_order:
            import_order_cron = self.search_active_existing_cron('ir_cron_woo_import_order_instance', instance)
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.woo_import_order_interval_type](self.woo_import_order_interval_number)
            vals = self.prepare_vals_for_cron(self.woo_import_order_interval_number,
                                              self.woo_import_order_interval_type,
                                              self.woo_import_order_user_id)
            vals.update({
                'nextcall': self.woo_import_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'code': "model.import_woo_orders(%d)" % (instance.id),
            })
            if import_order_cron:
                import_order_cron.write(vals)
            else:
                import_order_cron = self.search_cron_with_xml_id('woo_commerce_ept.ir_cron_woo_import_order')
                self.create_ir_model_record_for_cron(instance, import_order_cron, vals,
                                                     'ir_cron_woo_import_order_instance')
        else:
            import_order_cron = self.search_active_existing_cron('ir_cron_woo_import_order_instance', instance)
            import_order_cron and import_order_cron.write({'active': False})

        return True

    def setup_woo_import_cancel_order_cron(self, instance):
        """
        Configure the cron for auto import cancel order.
        @author: Meera Sidapara on Date 04-Apr-2022.
        """
        if self.woo_auto_import_cancel_order:
            import_cancel_order_cron = self.search_active_existing_cron('ir_cron_woo_import_cancel_order_instance',
                                                                        instance)
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.woo_import_cancel_order_interval_type](
                self.woo_import_cancel_order_interval_number)
            vals = self.prepare_vals_for_cron(self.woo_import_cancel_order_interval_number,
                                              self.woo_import_cancel_order_interval_type,
                                              self.woo_import_cancel_order_user_id)
            vals.update({
                'nextcall': self.woo_import_cancel_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'code': "model.import_cancel_order_cron_action(%d)" % (instance.id),
            })
            if import_cancel_order_cron:
                import_cancel_order_cron.write(vals)
            else:
                import_cancel_order_cron = self.search_cron_with_xml_id(
                    'woo_commerce_ept.ir_cron_woo_import_cancel_order')
                self.create_ir_model_record_for_cron(instance, import_cancel_order_cron, vals,
                                                     'ir_cron_woo_import_cancel_order_instance')
        else:
            import_cancel_order_cron = self.search_active_existing_cron('ir_cron_woo_import_cancel_order_instance',
                                                                        instance)
            if import_cancel_order_cron:
                import_cancel_order_cron.write({'active': False})
        return True

    def setup_woo_update_order_status_cron(self, instance):
        """
        Configure the cron for auto update order status.
        @author: Maulik Barad on Date 16-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if self.woo_auto_update_order_status:
            update_order_status_cron = self.search_active_existing_cron('ir_cron_woo_update_order_status_instance',
                                                                        instance)
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.woo_update_order_status_interval_type](
                self.woo_update_order_status_interval_number)
            vals = self.prepare_vals_for_cron(self.woo_update_order_status_interval_number,
                                              self.woo_update_order_status_interval_type,
                                              self.woo_update_order_status_user_id)
            vals.update({
                'nextcall': self.woo_update_order_status_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'code': "model.update_woo_order_status(%d)" % (instance.id),
            })
            if update_order_status_cron:
                update_order_status_cron.write(vals)
            else:
                update_order_status_cron = self.search_cron_with_xml_id(
                    'woo_commerce_ept.ir_cron_woo_update_order_status')
                self.create_ir_model_record_for_cron(instance, update_order_status_cron, vals,
                                                     'ir_cron_woo_update_order_status_instance')
        else:
            update_order_status_cron = self.search_active_existing_cron('ir_cron_woo_update_order_status_instance',
                                                                        instance)
            if update_order_status_cron:
                update_order_status_cron.write({'active': False})
        return True

    def setup_woo_update_stock_cron(self, instance):
        """
        This method is used for create or write cron of stock export process.
        :param instance: WooCommerce Instance
        :return: Boolean
        @author: Pragnadeep Pitroda @Emipro Technologies Pvt. Ltd 16-Nov-2019
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if self.woo_stock_auto_export:
            inventory_cron = self.search_active_existing_cron('ir_cron_update_woo_stock_instance', instance)
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.woo_update_stock_interval_type](self.woo_update_stock_interval_number)
            vals = self.prepare_vals_for_cron(self.woo_update_stock_interval_number,
                                              self.woo_update_stock_interval_type,
                                              self.woo_update_stock_user_id)
            vals.update({
                'nextcall': self.woo_update_stock_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'code': "model.auto_update_stock(ctx={'woo_instance_id':%d})" % (instance.id),
            })
            if inventory_cron:
                inventory_cron.write(vals)
            else:
                update_order_status_cron = self.search_cron_with_xml_id(
                    'woo_commerce_ept.ir_cron_update_woo_stock')
                self.create_ir_model_record_for_cron(instance, update_order_status_cron, vals,
                                                     'ir_cron_update_woo_stock_instance')
        else:
            inventory_cron = self.search_active_existing_cron('ir_cron_update_woo_stock_instance', instance)
            inventory_cron and inventory_cron.write({'active': False})
        return True

    def prepare_vals_for_cron(self, interval_number, interval_type, user_id):
        """
        This method is used to prepare a vals for setup a auto cron job.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        vals = {
            'active': True,
            'interval_number': interval_number,
            'interval_type': interval_type,
            'user_id': user_id.id if user_id else False
        }
        return vals

    def search_cron_with_xml_id(self, xml_id):
        """
        Search the cron job record which is created while install/upgrade the module.
        :param xml_id: XML Id of the cron job.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Task_id: 168189 - Woo Commerce Wizard py files refactor
        """
        try:
            cron = self.env.ref(xml_id)
        except:
            cron = False
        if not cron:
            raise UserError(_(
                'Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to '
                'back this settings.'))
        return cron

    def create_ir_model_record_for_cron(self, instance, import_order_cron, vals, xml_id):
        """
        This method is used to create a record of id model data for the auto cron job.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 9 November 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        ir_model_obj = self.env['ir.model.data']
        name = instance.name + ' : ' + import_order_cron.name
        vals.update({'name': name})
        new_cron = import_order_cron.copy(default=vals)
        ir_model_obj.create({
            'module': 'woo_commerce_ept',
            'name': '%s_%d' % (xml_id, instance.id),
            'model': 'ir.cron',
            'res_id': new_cron.id,
            'noupdate': True
        })

    @api.model
    def action_woo_open_cron_configuration_wizard(self):
        """
       Usage: Return the action for open the cron configuration wizard
       @author: Dipak Gogiya
       Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        """ Called by onboarding panel above the Instance."""
        instance_obj = self.env['woo.instance.ept']
        ir_action_obj = self.env["ir.actions.actions"]
        action = ir_action_obj._for_xml_id(
            "woo_commerce_ept.action_wizard_woo_cron_configuration_ept")
        instance = instance_obj.search_woo_instance()
        action['context'] = {'is_calling_from_onboarding_panel': True}
        if instance:
            action.get('context').update({'default_woo_instance_id': instance.id,
                                          'is_instance_exists': True})
        return action

    def setup_woo_import_complete_order_cron(self, instance):
        """
        Configure the cron for auto import order.
        @author: Maulik Barad on Date 16-Nov-2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        if self.woo_auto_import_complete_order:
            import_complete_order_cron = self.search_active_existing_cron('ir_cron_woo_import_complete_order_instance',
                                                                          instance)
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.woo_import_complete_order_interval_type](
                self.woo_import_complete_order_interval_number)
            vals = self.prepare_vals_for_cron(self.woo_import_complete_order_interval_number,
                                              self.woo_import_complete_order_interval_type,
                                              self.woo_import_complete_order_user_id)
            vals.update({
                'nextcall': self.woo_import_complete_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'code': "model.import_woo_orders(%d,order_type=%s)" % (instance.id, '"completed"'),
            })
            if import_complete_order_cron:
                import_complete_order_cron.write(vals)
            else:
                import_complete_order_cron = self.search_cron_with_xml_id(
                    'woo_commerce_ept.ir_cron_woo_import_complete_order')
                self.create_ir_model_record_for_cron(instance, import_complete_order_cron, vals,
                                                     'ir_cron_woo_import_complete_order_instance')
        else:
            import_complete_order_cron = self.search_active_existing_cron('ir_cron_woo_import_complete_order_instance',
                                                                          instance)
            import_complete_order_cron and import_complete_order_cron.write({'active': False})
        return True
