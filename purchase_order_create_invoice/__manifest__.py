# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Invoice from Multiple Sales and Purchases in Odoo',
    'version': '13.0.0.0',
    'summary': 'Apps helps to Generate single invoice from sales generate single invoice from purchase create single invoice from multiple sales order create single invoice from multiple purchase order single invoice from multi sales single invoice from multi purchase',
    'author': 'BrowseInfo',
    "price": 29,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.in',
    'category': 'Sales',
    'description':"""

Generate single invoice from multiple sales order, Create single invoice from multiple sales order, Single invoice for multiple orders, single invoice from Order, multiple sales generate single invoice, easy invoice from Sales order
Generate single invoice from multiple purchase order, Create single invoice from multiple purchase order, Single invoice for multiple orders, single invoice from Orders, multiple purchase generate single invoice, easy invoice from purchase order
    اتورة واحدة من أمر مبيعات متعدد ، فاتورة واحدة لأوامر متعددة ، فاتورة واحدة من الطلب ، مبيعات متعددة توليد فاتورة واحدة ، فاتورة سهلة من أمر المبيعات
إنشاء فاتورة فردية من طلب شراء متعدد ، إنشاء فاتورة واحدة من طلب شراء متعدد ، فاتورة واحدة لعدة طلبات ، فاتورة واحدة من الطلبات ، شراء متعدد إنشاء فاتورة واحدة ، فاتورة سهلة من أمر الشراء
 فاتورة واحدة للعديد من SO SO
 invoice from many SO PO
 create single invoice from Multiple Sales and Purchases
 create single invoice from Multiple Sales orders and Purchases
 create single invoice from Multiple Purchases orders
 create single invoice for Multiple Purchases orders
 create single invoice for Multiple Sales orders
 create single invoice for Multiple Sales orders and purchases
 generate invoice from Multiple Sales and Purchases
 generate invoice from Multiple Sales orders and Purchases
 generate invoice from Multiple Purchases orders
 generate invoice for Multiple Purchases orders
 generate invoice for Multiple Sales orders
 generate invoice for Multiple Sales orders and purchases
 Invoice for Multiple Sales Orders
 Invoice for Multiple purchase Orders
 invoice from multiple purchase orders
 invoice for multiple purchase orders
 invoice for multiple sale orders
 invoice from multiple sale orders
 invoice from multiple sale orders
 Generate invoice from many sale orders
 Generate invoice from multiple purchase orders
 create one invoice for multiple sale orders
 one invoice for many sale orders
 create one invoice from many SO
 create Invoice for Multiple SO
 create Invoice for Multiple pO
 create invoice from po
 create invoice from purchase
 create invoice from sale
 create invoice from po
 invoice from picking
 create invoice from sales
 create invoice from purchase
add invoice from sales easy invoice from multiple sales easy vendor bills from invoice
create vendor bills from purchase order
 create one vendor bill from many PO
 create vendor bills for Multiple PO
 create vendor bills for Multiple pO
 create vendor bill from po
 create vendor bill from purchase
 create vendor bills from purchase order create purchase bill
 create vendor bill from po
 vendor bill from picking
 
 create supplier invoice from purchase order
 create one supplier invoice from many SO
 create supplier Invoice for Multiple PO
 create supplier Invoices for Multiple pO
 create supplier invoice from po
 create supplier invoice from purchase
 create supplier invoices from purchase
 create supplier invoice from po
 supplier invoice from picking
 create supplier invoices from sales
 create supplier invoice from purchase
add supplier invoice from purchases easy supplier invoice from multiple purchase easy supplier invoice from invoice
'iinsha' fatwrat fardiat min talab mabieat mutaeadid , 'iinsha' faturat wahidat min 'amr mabieat mutaeadid , faturat wahidat li'awamir mutaeadidat , faturat wahidat min altalab , mabieat mutaeadidat tawlid faturt wahidat , faturt sahlatan min 'amr almubieat
'iinsha' fatwrt fardiat min talab shira' mutaeadid , 'iinsha' faturat wahidat min talab shira' mutaeadid , faturat wahidat ledt talabat , faturt wahidat min altalabat , shira' mutaeadid 'iinsha' fatwrat wahidat , fatwrt sahlatan min 'amr alshira'
 faturat wahidat lileadid min SO SOGenerar una sola factura desde varias órdenes de venta, crear una sola factura desde varias órdenes de venta, una sola factura para varias órdenes, una sola factura desde la orden, varias ventas generar una sola factura, una factura fácil desde una orden de venta
Genere una sola factura desde una orden de compra múltiple, cree una sola factura desde una orden de compra múltiple, una sola factura por pedidos múltiples, una sola factura desde pedidos, compra múltiple genere una sola factura, factura fácil desde la orden de compra
 una factura para muchos SO PO
Gerar fatura única a partir de vários pedidos de vendas, criar fatura única a partir de vários pedidos de vendas, fatura única para vários pedidos, fatura única a partir do pedido, várias vendas geram fatura única, fatura simples de pedido de venda
Gere uma única fatura de vários pedidos de compra, crie uma única fatura a partir de vários pedidos de compra, fatura única para vários pedidos, fatura única de pedidos, várias compras geram uma única fatura, fatura fácil a partir do pedido de compra
 uma fatura para muitos SO PO
Générer une facture unique à partir de plusieurs commandes client, Créer une facture unique à partir d'une commande client multiple, Facture unique pour plusieurs commandes, Facture unique à partir de la commande, Plusieurs ventes générer une facture unique, Facture facile à partir de Commande client
Générer une facture unique à partir d'un bon de commande multiple, Créer une facture unique à partir d'un bon de commande multiple, Facture unique pour plusieurs commandes, Facture unique à partir de commandes, Plusieurs achats générer une facture unique, Facture facile à partir du bon de commande
 une facture pour plusieurs SO POEinzelne Rechnung aus mehreren Kundenaufträgen generieren, Einzelne Rechnung aus mehreren Kundenaufträgen erstellen, Einzelne Rechnung für mehrere Bestellungen, einzelne Rechnung aus Auftrag, mehrere Verkäufe generieren eine einzelne Rechnung, einfache Rechnung aus Kundenauftrag
Generieren Sie einzelne Rechnungen aus mehreren Bestellungen, erstellen Sie einzelne Rechnungen aus mehreren Bestellungen, einzelne Rechnungen für mehrere Bestellungen, einzelne Rechnungen aus Bestellungen, mehrere Bestellungen generieren eine einzelne Rechnung, einfache Rechnung aus der Bestellung
 eine Rechnung für viele SO PO


""",
    'depends':['sale','sale_management','purchase','account'],
    'data':[
        'wizard/multiple_purchase_one_invoice_wizard.xml',
        'wizard/multiple_sale_one_invoice_wizard.xml',
        'views/sale_purchase_invoice.xml',
        ],
    'installable': True,
    'auto_install': False,
    "images":["static/description/Banner.png"],
    'live_test_url':'https://youtu.be/Fhdi6LzexbE',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
