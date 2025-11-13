# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _update_product_cost_from_purchase(self):
        """Actualiza el coste del producto y el precio del proveedor con el precio de la última compra"""
        for line in self:
            if line.product_id and line.price_unit > 0 and line.order_id.partner_id:
                # Obtener el precio unitario de la compra
                purchase_price = line.price_unit

                # Convertir a la UdM del producto si es necesario
                if line.product_uom != line.product_id.uom_id:
                    purchase_price = line.product_uom._compute_price(
                        purchase_price,
                        line.product_id.uom_id
                    )

                # 1. Actualizar el precio de coste (standard_price) del producto
                old_cost = line.product_id.standard_price
                line.product_id.with_context(disable_auto_svl=True).standard_price = purchase_price

                _logger.info(
                    f"Actualizado coste del producto '{line.product_id.display_name}' "
                    f"de {old_cost:.2f} a {purchase_price:.2f} "
                    f"desde pedido de compra {line.order_id.name}"
                )

                # 2. Actualizar el precio en la ficha del proveedor (product.supplierinfo)
                line._update_supplier_price(purchase_price)

    def _update_supplier_price(self, price):
        """Actualiza o crea el precio del proveedor en product.supplierinfo"""
        self.ensure_one()

        SupplierInfo = self.env['product.supplierinfo']
        partner = self.order_id.partner_id
        product = self.product_id

        # Buscar si ya existe una línea de proveedor para este producto y proveedor
        supplierinfo = SupplierInfo.search([
            ('partner_id', '=', partner.id),
            ('product_id', '=', product.id),
            ('company_id', 'in', [self.company_id.id, False]),
        ], limit=1)

        if not supplierinfo:
            # Si no existe, buscar por product_tmpl_id
            supplierinfo = SupplierInfo.search([
                ('partner_id', '=', partner.id),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('product_id', '=', False),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)

        if supplierinfo:
            # Actualizar precio existente
            old_price = supplierinfo.price
            supplierinfo.price = price
            _logger.info(
                f"Actualizado precio del proveedor '{partner.display_name}' "
                f"para producto '{product.display_name}': {old_price:.2f} → {price:.2f}"
            )
        else:
            # Crear nueva línea de proveedor
            supplierinfo = SupplierInfo.create({
                'partner_id': partner.id,
                'product_id': product.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'price': price,
                'company_id': self.company_id.id,
                'currency_id': self.order_id.currency_id.id,
            })
            _logger.info(
                f"Creada nueva línea de proveedor '{partner.display_name}' "
                f"para producto '{product.display_name}' con precio {price:.2f}"
            )

    def write(self, vals):
        """Actualizar el coste cuando se confirma el pedido o se modifica el precio"""
        res = super().write(vals)

        # Si se modifica el precio unitario y el pedido está confirmado
        if 'price_unit' in vals:
            confirmed_lines = self.filtered(
                lambda l: l.order_id.state in ['purchase', 'done']
            )
            if confirmed_lines:
                confirmed_lines._update_product_cost_from_purchase()

        return res

    @api.model
    def create(self, vals):
        """Actualizar el coste cuando se crea una línea en un pedido confirmado"""
        line = super().create(vals)

        # Si el pedido ya está confirmado, actualizar el coste
        if line.order_id.state in ['purchase', 'done']:
            line._update_product_cost_from_purchase()

        return line


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        """Actualizar el coste de los productos cuando se confirma el pedido"""
        res = super().button_confirm()

        # Actualizar el coste de todos los productos del pedido
        for order in self:
            order.order_line._update_product_cost_from_purchase()

        return res

