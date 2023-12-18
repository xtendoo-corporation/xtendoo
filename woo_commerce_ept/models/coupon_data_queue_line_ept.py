# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import time

from odoo import models, fields

_logger = logging.getLogger("WooCommerce")


class WooCouponDataQueueLineEpt(models.Model):
    _name = "woo.coupon.data.queue.line.ept"
    _description = "WooCommerce Coupon Data Queue Line"
    _rec_name = "number"

    coupon_data_queue_id = fields.Many2one("woo.coupon.data.queue.ept", ondelete="cascade")
    instance_id = fields.Many2one(related="coupon_data_queue_id.woo_instance_id", copy=False,
                                  help="Coupon imported from this Woocommerce Instance.")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"), ("cancel", "Cancelled"), ("done", "Done")],
                             default="draft", copy=False)
    woo_coupon = fields.Char(string="Woo Coupon Id", help="Id of imported coupon.", copy=False)
    coupon_id = fields.Many2one("woo.coupons.ept", copy=False, help="coupon created in Odoo.")
    coupon_data = fields.Text(help="Data imported from Woocommerce of current coupon.", copy=False)
    processed_at = fields.Datetime(help="Shows Date and Time, When the data is processed.", copy=False)
    common_log_lines_ids = fields.One2many("common.log.lines.ept", "woo_coupon_data_queue_line_id",
                                           help="Log lines created against which line.", string="Log Message")
    number = fields.Char(string='Coupon Name')

    def process_coupon_queue_line(self):
        """
        Process the imported coupon data and create the coupon.
        @author: Nilesh Parmar on Date 31 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        coupon_obj = self.env["woo.coupons.ept"]
        start = time.time()
        self.env.cr.execute(
            """update woo_coupon_data_queue_ept set is_process_queue = False where is_process_queue = True""")
        self._cr.commit()

        coupon_obj.create_or_write_coupon(self)

        end = time.time()
        _logger.info("Processed %s Coupons in %s seconds.", str(len(self)), str(end - start))

    def auto_coupon_queue_lines_process(self):
        """
        This method used to find a coupon queue line records.
        @author: Nilesh Parmar on Date 31 Dec 2019.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        coupon_data_queue_obj = self.env["woo.coupon.data.queue.ept"]
        query = """SELECT coupon_data_queue_id FROM woo_coupon_data_queue_line_ept WHERE state = 'draft' ORDER BY
        "create_date" ASC limit 1;"""
        self._cr.execute(query)
        coupon_queue_data = self._cr.fetchone()
        coupon_queue_id = coupon_data_queue_obj.browse(coupon_queue_data)
        coupon_queue_lines = coupon_queue_id and coupon_queue_id.coupon_data_queue_line_ids.filtered(
            lambda x: x.state == "draft")
        if coupon_queue_lines:
            coupon_queue_lines.process_coupon_queue_line()
        return True
