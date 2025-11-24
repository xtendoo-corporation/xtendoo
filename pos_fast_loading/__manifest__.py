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
    "name"              :  "POS Fast Loading",
    "summary"           :  """This module is used to load the data fast into pos. It can load more than 1 Lac products and 50k customers in just few seconds. Keywords:Fast Data Loading | Load Data Faster | Faster Loading Data | Speed Up Loading | POS Data Load | Fast POS | POS Load Faster | Rapid POS Data Loading | Quick POS Sync | Efficient POS Data Load | Accelerated POS Loading | High-Speed POS Sync | Instant POS Data Load | Optimized POS Loading | POS Performance Boost | Lightning-Fast POS Load | Seamless POS Data Loading | Ultra-Fast POS Sync | Enhanced POS Speed | POS Data Sync Accelerator | Speedy POS Data Management | POS Optimize | Fast POS Data Integration""",
    "category"          :  "Point Of Sale",
    "version"           :  "1.0.0",
    "sequence"          :  1,
    "author"            :  "Webkul Software Pvt. Ltd.",
    "license": "AGPL-3",
    "website"           :  "https://store.webkul.com/Odoo-POS-Fast-Loading.html",
    "description"       :  """fast load, fast load data, data fast into pos, data faster loading, fast loading""",
    # "live_test_url"     :  "http://odoodemo.webkul.com/?module=pos_fast_loading&custom_url=/pos/auto",
    "depends"           :  ['pos_sale'],
    "data"              :  [
                                'data/cron.xml',
                                'security/ir.model.access.csv',
                                'views/pos_fast_loading_view.xml',
                            ],
    "demo"              :  [
                            'demo/demo.xml',
                        ],
    'assets'            :  {
                                'point_of_sale._assets_pos': [
                                    'web/static/lib/jquery/jquery.js',
                                    "/pos_fast_loading/static/src/**/*"
                                ],
                            },
    "images"            :  ['static/description/banner.png'],
    "application"       :  True,
    "installable"       :  True,
    "auto_install"      :  False,
    "price"             :  249,
    "currency"          :  "USD",
    "pre_init_hook"     :  "pre_init_check",
}
