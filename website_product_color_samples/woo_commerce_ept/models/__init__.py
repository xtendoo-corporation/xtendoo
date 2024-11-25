# -*- coding: utf-8 -*-

# Increased Buffer limit for large response
import os
os.environ['ODOO_LIMIT_LITEVAL_BUFFER'] = '10240000'
from . import res_company
from . import instance_ept
from . import payment_gateway
from . import sale_workflow_config
from . import res_partner
from . import sale_order
from . import product_image_ept
from . import product_ept
from . import product_data_queue_ept
from . import product_data_queue_line_ept
from . import product_tags_ept
from . import product_attribute_ept
from . import product_attribute_term_ept
from . import product_category_ept
from . import common_product_image_ept
from . import common_log_lines_ept
from . import customer_data_queue_ept
from . import customer_data_queue_line_ept
from . import order_data_queue_ept
from . import order_data_queue_line_ept
from . import webhook_ept
from . import import_order_status_ept
from . import delivery_carrier
from . import stock_move
from . import stock_picking
from . import product
from . import account_move
from . import res_partner_ept
from . import coupons_ept
from . import coupon_data_queue_ept
from . import coupon_data_queue_line_ept
from . import data_queue_mixin_ept
from . import queue_line_dashboard
from . import shipping_method
from . import meta_field_mapping_ept
from . import digest
from . import export_stock_queue_ept
from . import export_stock_queue_line_ept
