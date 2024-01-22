# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name":  "POS Refund Via Voucher",
    "summary":  """The module allow you to process customer refund with a voucher or coupon instead of cash. The customer can use the voucher amount on the successive purchases.POS Store credit|Refund gift card|POS refund|POS RMA|Instant refund""",
    "category":  "Point of Sale",
    "version":  "1.1.1",
    "sequence":  1,
    "author":  "Webkul Software Pvt. Ltd.",
    "license":  "Other proprietary",
    "website":  "https://store.webkul.com/Odoo-POS-Refund-Via-Voucher.html",
    "description":  """Odoo POS Refund Via Voucher
POS Refund voucher
POS refund coupon
POS Store credit
POS Refund gift card
Refund with voucher
POS refund
POS RMA
Instant refund voucher""",
    "live_test_url":  "http://odoodemo.webkul.com/?module=pos_voucher_refund&custom_url=/pos/auto",
    "depends":  ['pos_coupons'],
    "data":  ['views/res_config_view.xml', ],
    "demo":  ['data/demo.xml'],
    "images":  ['static/description/Banner.png'],
    "application":  True,
    "installable":  True,
    "assets":  {
        'point_of_sale.assets': [
            "/pos_voucher_refund/static/src/js/screens.js",
            "/pos_voucher_refund/static/src/js/models.js",
            "/pos_voucher_refund/static/src/js/popups.js",
            "/pos_voucher_refund/static/src/css/pos_voucher_refund.css",
            '/pos_voucher_refund/static/src/xml/pos.xml',
        ],
        # 'web.assets_qweb': [
        #     'pos_voucher_refund/static/src/xml/pos.xml',
        # ],
    },
    "auto_install":  False,
    "price":  45,
    "currency":  "USD",
    "pre_init_hook":  "pre_init_check",
}
