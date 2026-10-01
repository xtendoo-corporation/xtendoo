# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Datos adicionales para el informe de ventas diarias (X/Z) del TPV.

El informe estándar agrupa los productos por categoría, muestra un
código de barras por línea, desglosa los pagos por sesión y lista
todas las facturas una a una. Aquí se añaden los datos necesarios para
una versión más compacta y orientada al cierre de caja:

* Resumen de la sesión: total cobrado, número de tickets, ticket medio,
  base imponible, IVA y devoluciones.
* Cobros agrupados por forma de pago, con el número de cobros, el
  importe y el porcentaje sobre el total.
* Ventas y devoluciones con una sola línea por producto.
* Resumen de facturas (número, primera, última y total).

Las claves estándar no se modifican, de modo que el resto de módulos
que extienden el informe siguen funcionando.
"""

from odoo import api, models


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        **kwargs,
    ):
        result = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )
        orders = self._xtendoo_get_orders(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )
        sale_orders = orders.filtered(lambda order: not order.is_refund)
        refund_orders = orders - sale_orders
        payment_methods = self._xtendoo_get_payment_methods(orders)
        result.update(
            {
                "xtendoo_summary": self._xtendoo_get_summary(
                    result, orders, refund_orders
                ),
                "xtendoo_payment_methods": payment_methods,
                "xtendoo_payment_totals": {
                    "count": sum(method["count"] for method in payment_methods),
                    "amount": sum(method["amount"] for method in payment_methods),
                },
                "xtendoo_products": self._xtendoo_get_products(sale_orders.lines),
                "xtendoo_refund_products": (
                    self._xtendoo_get_products(refund_orders.lines)
                ),
                "xtendoo_invoice_summary": (self._xtendoo_get_invoice_summary(result)),
            }
        )
        return result

    def _xtendoo_get_orders(
        self, date_start, date_stop, config_ids, session_ids, **kwargs
    ):
        """Pedidos incluidos en el informe, con el mismo criterio que el
        estándar (``_get_domain``), para que todos los bloques cuadren."""
        if not session_ids:
            date_start, date_stop = self._get_date_start_and_date_stop(
                date_start, date_stop
            )
        domain = self._get_domain(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )
        return self.env["pos.order"].search(domain)

    def _xtendoo_get_summary(self, result, orders, refund_orders):
        total = result["currency"]["total_paid"]
        order_count = result["nbr_orders"]
        base_amount = sum(orders.lines.mapped("price_subtotal"))
        total_with_taxes = sum(orders.lines.mapped("price_subtotal_incl"))
        return {
            "total": total,
            "order_count": order_count,
            "average_ticket": total / order_count if order_count else 0.0,
            "base_amount": base_amount,
            "tax_amount": total_with_taxes - base_amount,
            "refund_count": len(refund_orders),
            "refund_amount": sum(refund_orders.mapped("amount_total")),
        }

    def _xtendoo_get_payment_methods(self, orders):
        """Cobros agrupados por forma de pago (todas las sesiones juntas).

        El importe es neto del cambio devuelto, igual que en el estándar;
        las líneas de cambio no cuentan como un cobro adicional.
        """
        Payment = self.env["pos.payment"]
        domain = [("pos_order_id", "in", orders.ids)]
        amounts = dict(
            Payment._read_group(domain, ["payment_method_id"], ["amount:sum"])
        )
        counts = dict(
            Payment._read_group(
                domain + [("is_change", "=", False)],
                ["payment_method_id"],
                ["__count"],
            )
        )
        grand_total = sum(amounts.values())
        methods = self.env["pos.payment.method"].union(*amounts).sorted()
        return [
            {
                "id": method.id,
                "name": method.name,
                "count": counts.get(method, 0),
                "amount": amounts[method],
                "percentage": (
                    amounts[method] * 100.0 / grand_total if grand_total else 0.0
                ),
            }
            for method in methods
        ]

    def _xtendoo_get_products(self, lines):
        """Una entrada por producto, ordenadas por nombre.

        A diferencia del estándar, no se separan las líneas por categoría,
        precio o descuento: lo que interesa en el cierre es cuánto se ha
        vendido de cada producto.
        """
        products = {}
        for line in lines:
            product = line.product_id
            values = products.setdefault(
                product,
                {
                    "product_id": product.id,
                    "default_code": product.default_code or "",
                    "name": product.with_context(
                        display_default_code=False
                    ).display_name,
                    "uom": product.uom_id.name,
                    "quantity": 0.0,
                    "base_amount": 0.0,
                    "total_amount": 0.0,
                },
            )
            values["quantity"] += abs(line.qty)
            values["base_amount"] += line.price_subtotal
            values["total_amount"] += line.price_subtotal_incl
        return sorted(
            products.values(),
            key=lambda values: (values["name"].lower(), values["product_id"]),
        )

    def _xtendoo_get_invoice_summary(self, result):
        """Resumen de facturas en lugar de la relación completa."""
        invoices = [
            invoice
            for session in result["invoiceList"]
            for invoice in session["invoices"]
        ]
        names = sorted(invoice["name"] for invoice in invoices if invoice["name"])
        return {
            "count": len(invoices),
            "first": names[0] if names else False,
            "last": names[-1] if names else False,
            "total": result["invoiceTotal"],
        }
