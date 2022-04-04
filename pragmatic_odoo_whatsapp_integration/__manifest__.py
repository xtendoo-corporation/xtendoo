{
    'name': 'Whatsapp Odoo All In One Integration',
    'version': '15.0.10',
    'category': 'Connector',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'pragtech.co.in',
    'summary': 'whatsapp connector integration odoo Whatsapp crm Whatsapp lead Whatsapp task Whatsapp sale order Whatsapp purchase order Whatsapp invoice Whatsapp payment reminder Whatsapp pos Whatsapp automation Whatsapp point of sale livechat whatsapp business',
    'description': """
Whatsapp Odoo All In One Integration
====================================
Whatsapp is an immensely popular chatting app used by 1.5 Billion people worldwide.
It has an easy interface and can be used powerfully with Odoo.
Pragmatic has developed an Odoo app which allows users to use the Whatsapp Application to send messages via Odoo.
We can send messages from Contacts, Sales, Accounts invoice, Accounts Payments, Credit Notes, Delivery orders, 
Point of sale, Purchase orders, Project Task, CRM Lead, Payment Reminder, User signup page via the same application. 
Let us have a look at how this works inside Odoo.

Features of Whatsapp Odoo All in one Integration
------------------------------------------------
    * Robust, Reliable and Server based and it can handle large volumes of Messages
    * Permission to enable whatsapp messages on Sales orders, Purchase order, Accounts invoice/payments, Delivery orders
    * Send message Configuration
        I Set Signature:to whatsapp Messages
        II Add to chatter
        III Add order product information in message such as order amount.
        IV Add product details in message such as name and other details:
    * In CRM, when lead or opportunity will be created then a message will be sent to the salesperson.
    * In Project Management when when task is created then a WhatsApp message will be sent to the assigned user.
    * If user sends a reply to task message as done then in odoo project task state is changed to done
    * Send Payment reminder message to customer.
    * Send messages to single or multiple Contacts within Odoo along with multiple attachments in different formats such as doc, pdf, image, audio, video
    * In the Point of sale Odoo app when an order is confirmed, send order details message to customer
    * Send message when a user signs up on the Odoo website page.


On Ubuntu server need to execute following command

``sudo pip3 install phonenumbers``

    """,
    'depends': ['contacts', 'delivery', 'crm', 'project', 'sale_management', 'purchase_stock',
                'im_livechat', 'website', 'point_of_sale', 'phone_validation'],
    'data': [
        'security/ir.model.access.csv',
        'data/project_task_type_data.xml',
        'wizard/send_wp_msg_views.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_views.xml',
        'views/sale_order_view.xml',
        'views/account_invoice_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_order_view.xml',
        'views/whatsapp_scheduler.xml',
        'views/project_task_view.xml',
        'security/security.xml',
        'security/sale_security.xml',
        'views/sale_res_config_settings_view.xml',
        'views/purchase_order_res_config_settings_view.xml',
        'views/stock_picking_res_config_settings_view.xml',
        'views/account_invoicing_res_config_settings_view.xml',
        'views/crm_res_config_settings_view.xml',
        'views/project_task_res_config_settings_view.xml',
        'views/account_payment_view.xml',
        'views/login_template.xml',
        'views/whatsapp_message_view.xml',
        'views/mail_message_view.xml'
    ],

    'assets': {
        'point_of_sale.assets': [
            'pragmatic_odoo_whatsapp_integration/static/src/js/pos_test.js'
        ],
        'web.assets_qweb': [
            'pragmatic_odoo_whatsapp_integration/static/src/xml/pos_view.xml'
        ],
    },

    'images': ['static/description/whatsapp-odoo-integration-gif.gif'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=103&name=odoo-whatsapp-integration',
    'price': 99,
    'currency': 'USD',
    'license': 'OPL-1',
    'application': False,
    'auto_install': False,
    'installable': True,
}
