from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.sale.controllers.portal import CustomerPortal


GROUP_NO_ECONOMICS = "cdv_portal_no_economics.group_portal_no_economics"


def _user_hides_economics():
    """Return True when the current user must not access economic data."""
    user = request.env.user
    return bool(user) and user.has_group(GROUP_NO_ECONOMICS)


class SalePortalNoEconomics(CustomerPortal):

    def portal_my_quotes(self, **kwargs):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().portal_my_quotes(**kwargs)

    def portal_my_orders(self, **kwargs):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().portal_my_orders(**kwargs)

    def portal_order_page(self, order_id, **kw):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().portal_order_page(order_id, **kw)


class AccountPortalNoEconomics(PortalAccount):

    def portal_my_invoices(self, **kw):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().portal_my_invoices(**kw)

    def portal_my_invoice_detail(self, invoice_id, **kw):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().portal_my_invoice_detail(invoice_id, **kw)

    def portal_my_overdue_invoices(self, **kw):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().portal_my_overdue_invoices(**kw)


class PaymentPortalNoEconomics(PaymentPortal):

    def payment_method(self, **kwargs):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().payment_method(**kwargs)

    def payment_pay(self, **kwargs):
        if _user_hides_economics():
            return request.redirect("/my")
        return super().payment_pay(**kwargs)
