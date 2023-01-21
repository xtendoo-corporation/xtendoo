# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Cash on Delivery COD in Odoo',
    'summary':'App allow website COD store COD shop cash on delivery payment Shop COD Store COD eCommerce COD Shop cash on delivery store cash on delivery order cash on delivery COD order shop Order COD order cash payment COD payment method on website COD payment method',
    'description': """Website Payment Cash on Delivery
    Website Cash on Delivery
    eCommerce Cash on Delivery
    e-Commerce Cash on Delivery
    Odoo shop Cash on Delivery

    Website payment Cash on Delivery
    eCommerce payment Cash on Delivery
    e-Commerce payment Cash on Delivery
    Odoo shop payment Cash on Delivery

    Website payment COD
    eCommerce payment COD
    e-Commerce payment COD
    Odoo shop payment COD
    cash on delivery on website
    cash on delivery on eCommerce
    cash on delivery on e-Commerce
    cash on delivery on Odoo Shop
    cash on delivery on Shop Odoo

    cash on delivery payment on website
    cash on delivery payment on eCommerce
    cash on delivery payment on e-Commerce
    cash on delivery payment on Odoo Shop
    cash on delivery payment on Shop Odoo


    COD payment on website
    COD payment on eCommerce
    COD payment on e-Commerce
    COD payment on Odoo Shop
    COD payment on Shop Odoo

    cash on delivery payment method on website
    cash on delivery payment method on eCommerce
    cash on delivery payment method on e-Commerce
    cash on delivery payment method on Odoo Shop
    cash on delivery payment method on Shop Odoo


    COD payment method on website
    COD payment method on eCommerce
    COD payment method on e-Commerce
    COD payment method on Odoo Shop
    COD payment method on Shop Odoo
    Website COD payment method
    COD Odoo website
    COD payment on Website
    Website payment COD
    Shop COD Store COD online COD online store COD
    Shop cash on delivery
    online cash on delivery option
    Odoo store cash on delivery method
 This Odoo apps allows Cash On Delivery payment method Option in Website Transaction. 
 If you are using Odoo website/ecommerce and online store and want provide COD(cash on delivery) payment option to your customer as payment method then this will be the good module for use.
  By using this Odoo app  webshop customer or visitors can purchase product with cash on delivery method method.
  This payment method comes as separate payment acquirer on Odoo backend where you can set different rules for this payment method 
  like set minimum and maximum order amount, delivery charges on COD method, allow this payment for specific location using zip code, minimum and maximum product amount, extra fee. Everything is Configurable from the backend with Cash on Delivery payment acquirer as add different payment COD rules, Different COD policy , Delivery messages,Delivery Dates configuration etc.


""" , 
    'category': 'eCommerce',
    'version': '16.0.0.2',
    'price': 39,
    'currency': "EUR",
    'author': 'BrowseInfo',
    "website" : "https://www.browseinfo.in",
    'depends': ['sale', 'account', 'website','website_sale','payment','sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/cod_view.xml',
        'views/template.xml',
        'views/cod_collection_report.xml',
        'views/report_cod_collection.xml',
        'data/payment_acquirer_data.xml',
        'data/email.xml'
        
    ],
    'application': True,
    "auto_install": False,
    'installable': True,
    'license': 'OPL-1',
    'live_test_url':'https://youtu.be/NiVtyfw33D8',
    "images":['static/description/Banner.png'],
    'assets':{
        'web.assets_backend':[
        'bi_website_cash_on_delivery/static/src/js/custom.js',
        ]
    },
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
