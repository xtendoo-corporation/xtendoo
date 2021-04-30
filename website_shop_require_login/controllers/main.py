# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class RequireLoginToShop(WebsiteSale):
    @http.route(auth="user")
    def shop(self, **post):
        return super().shop(**post)

    # @http.route(auth='user')
    # def shop(self, page=0, category=None, search='', ppg=False, **post):
    #     return super().shop(
    #         page=page, category=category, search=search, ppg=ppg, **post)
