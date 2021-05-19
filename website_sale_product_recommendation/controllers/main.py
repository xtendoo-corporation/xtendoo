# © 2016 Serpent Consulting Services Pvt. Ltd. (http://www.serpentcs.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request

from datetime import datetime, timedelta
from odoo import api, fields, models

from odoo.addons.website_sale.controllers.main import QueryURL, WebsiteSale


class WebsiteSale(WebsiteSale):
    def _get_search_domain(
        self, search, category, attrib_values, search_in_description=True
    ):
        domain = super()._get_search_domain(
            search, category, attrib_values, search_in_description=search_in_description
        )
        if "recommendations" in request.env.context:
            print("*"*80)
            print("domain recommendations", self._get_sale_order_domain())

            print("*"*80)
            found_lines = request.env["sale.order.line"].read_group(
                self._get_sale_order_domain(),
                ["product_id", "qty_delivered"],
                ["product_id"],
            )
            print("found lines", found_lines)

            for l in found_lines:
                print("*" * 80)
                print(l)

            print("*"*80)
            products_ids = []
            for line in found_lines:
                products_ids.append(line["product_id"][0])

            print("*" * 80)
            print("found_dict", products_ids)
            print("*" * 80)

            domain.append(("id", "in", products_ids))

        print("*" * 80)
        print("domain", domain)
        print("*" * 80)

        return domain

    @http.route(["/recommendations"], type="http", auth="public", website=True)
    def shop(self, page=0, category=None, recommendations=True, search="", **post):
        if recommendations:
            context = dict(request.env.context)
            context.setdefault("recommendations", recommendations)
            request.env.context = context
        return super().shop(
            page=page, category=category, recommendations=recommendations, search=search, **post
        )

    # Method to get the recommendations.
    @http.route(["/page/product_recommendations"], type="http", auth="public", website=True)
    def product_recommendations(self, **post):
        keep = QueryURL("/page/product_recommendations")
        values = {"keep": keep}
        if post.get("search"):
            values.update({"search": post.get("search")})
        return request.render("website_sale_product_recommendation.product_recommendations", values)

    def _get_sale_order_domain(self):
        partner = request.env.user.partner_id
        start = fields.Datetime.to_string(datetime.now() - timedelta(60))
        other_sales = request.env["sale.order"].search(
            [
                ("partner_id", "=", partner.id),
                ("date_order", ">=", start),
            ]
        )
        return [
            ("order_id", "in", other_sales.ids),
            ("product_id.active", "=", True),
            ("product_id.sale_ok", "=", True),
            ("product_id.website_published", "=", True),
            ("qty_delivered", "!=", 0.0),
        ]
