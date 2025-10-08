from odoo import models, fields, api
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import float_repr


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo para marcar si se han aplicado descuentos del cliente
    partner_global_discounts_applied = fields.Boolean(
        string='Descuentos del Cliente Aplicados',
        default=False,
        help="Indica si se han aplicado descuentos globales configurados en el cliente",
        copy=False
    )

    def action_apply_partner_global_discounts(self):
        """
        Lanza el wizard para confirmar y aplicar los descuentos globales del cliente
        """
        self.ensure_one()

        if not self.partner_id:
            raise UserError('Debe seleccionar un cliente antes de aplicar descuentos.')

        if not self.partner_id.has_global_discounts:
            raise UserError('Este cliente no tiene descuentos globales configurados.')

        # Calcular el subtotal base (sin descuentos globales ya aplicados)
        base_amount = self._get_base_amount_for_partner_discounts()

        if base_amount <= 0:
            raise UserError('No hay importe base para aplicar descuentos.')

        # Determinar el tipo de documento
        doc_type = 'quotation' if self.state in ['draft', 'sent'] else 'sale_order'

        # Obtener descuentos aplicables del cliente
        applicable_discounts = self.partner_id.get_applicable_discounts(
            doc_type, base_amount, self.date_order.date() if self.date_order else None
        )

        if not applicable_discounts:
            raise UserError('No hay descuentos aplicables para este pedido.')

        # Lanzar el wizard de confirmación
        return {
            'type': 'ir.actions.act_window',
            'name': 'Aplicar Descuentos del Cliente',
            'res_model': 'apply.partner.discounts.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'active_model': 'sale.order',
                'active_id': self.id,
            }
        }

    def _get_base_amount_for_partner_discounts(self):
        """Calcula el importe base para aplicar descuentos del cliente"""
        # Excluir líneas de descuento y líneas de sección/nota
        normal_lines = self.order_line.filtered(
            lambda l: not self._is_line_global_discount(l) and
                     l.display_type not in ['line_section', 'line_note']
        )
        return sum(normal_lines.mapped('price_subtotal'))

    def _is_line_global_discount(self, line):
        """Verifica si una línea es de descuento global"""
        # Verificar si es una línea de descuento global del módulo estándar
        if hasattr(self, 'global_discount_ids') and self.global_discount_ids:
            return False  # Las líneas de descuento estándar no son líneas normales

        # Verificar si es una línea creada por nuestro módulo
        return (line.price_unit < 0 and 'Descuento Global' in (line.name or '')) or \
               (hasattr(line, 'product_id') and line.product_id and 'GLOBAL_DISCOUNT' in (line.product_id.default_code or ''))

    def _apply_partner_discount(self, discount_config, base_amount):
        """
        Aplica un descuento individual creando líneas por cada grupo de impuestos
        Similar al método _create_discount_lines de Odoo estándar
        """
        # Agrupar líneas por tipo de impuesto
        total_price_per_tax_groups = defaultdict(float)

        for line in self.order_line:
            # Excluir líneas de descuento, sección y nota
            if self._is_line_global_discount(line) or line.display_type in ['line_section', 'line_note']:
                continue

            if not line.product_uom_qty or not line.price_unit:
                continue

            # Excluir impuestos fijos que no se pueden descontar
            taxes = line.tax_id.flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda t: t.amount_type == 'fixed')
            taxes -= fixed_taxes

            # Calcular el precio total de la línea considerando el descuento de línea
            line_price = line.price_unit * (1 - (line.discount or 0.0) / 100) * line.product_uom_qty
            total_price_per_tax_groups[taxes] += line_price

        if not total_price_per_tax_groups:
            # No hay líneas válidas para aplicar el descuento
            return 0

        # Calcular el porcentaje de descuento basado en el importe base
        if discount_config.discount_type == 'percentage':
            discount_percentage = discount_config.discount_value / 100.0
        else:  # fixed_amount
            # Convertir importe fijo a porcentaje basado en el total
            total_base = sum(total_price_per_tax_groups.values())
            discount_percentage = discount_config.discount_value / total_base if total_base > 0 else 0

        total_discount_applied = 0
        discount_dp = self.env['decimal.precision'].precision_get('Discount')

        # Crear líneas de descuento por cada grupo de impuestos
        if len(total_price_per_tax_groups) == 1:
            # Un solo grupo de impuestos o sin impuestos
            taxes = next(iter(total_price_per_tax_groups.keys()))
            subtotal = total_price_per_tax_groups[taxes]
            discount_amount = subtotal * discount_percentage

            if discount_amount > 0:
                description = f"Descuento Global - {discount_config.name} ({float_repr(discount_percentage * 100, discount_dp)}%)"
                self._create_single_discount_line(
                    discount_name=description,
                    discount_amount=discount_amount,
                    taxes=taxes
                )
                total_discount_applied += discount_amount
        else:
            # Múltiples grupos de impuestos - crear una línea por cada uno
            for taxes, subtotal in total_price_per_tax_groups.items():
                discount_amount = subtotal * discount_percentage

                if discount_amount > 0:
                    description = f"Descuento Global - {discount_config.name} ({float_repr(discount_percentage * 100, discount_dp)}%)"

                    self._create_single_discount_line(
                        discount_name=description,
                        discount_amount=discount_amount,
                        taxes=taxes
                    )
                    total_discount_applied += discount_amount

        return total_discount_applied

    def _create_single_discount_line(self, discount_name, discount_amount, taxes):
        """
        Crea una única línea de descuento con los impuestos especificados
        """
        discount_product = self._get_global_discount_product()

        line_vals = {
            'order_id': self.id,
            'product_id': discount_product.id,
            'name': discount_name,
            'product_uom_qty': 1,
            'price_unit': -discount_amount,
            'discount': 0,
            'tax_id': [(6, 0, taxes.ids)] if taxes else False,
            'sequence': 999,  # Al final del pedido
        }

        # Crear la línea de descuento
        self.env['sale.order.line'].create(line_vals)

    def _create_global_discount_line(self, discount_name, discount_amount, discount_type, discount_value):
        """
        Crea una línea de descuento global usando la funcionalidad estándar
        DEPRECATED: Usar _apply_partner_discount que crea líneas por grupo de impuestos
        """
        # Intentar usar el método estándar del módulo sale_global_discount
        if hasattr(self, 'global_discount_ids'):
            # Verificar la estructura del modelo global.discount
            global_discount_model = self.env['global.discount']

            # Preparar valores compatibles con la estructura real del modelo
            discount_vals = {
                'name': discount_name,
                'company_id': self.company_id.id,
            }

            # Añadir campos específicos del módulo sale_global_discount según su estructura
            if 'discount' in global_discount_model._fields:
                discount_vals['discount'] = discount_value if discount_type == 'percentage' else (discount_amount / self.amount_untaxed * 100) if self.amount_untaxed > 0 else 0

            if 'discount_scope' in global_discount_model._fields:
                discount_vals['discount_scope'] = 'sale_order'

            if 'sequence' in global_discount_model._fields:
                discount_vals['sequence'] = 999

            try:
                # Crear o encontrar el descuento global
                global_discount = global_discount_model.create(discount_vals)

                # Añadir el descuento al pedido usando el método estándar
                self.write({
                    'global_discount_ids': [(4, global_discount.id)]
                })
                return
            except Exception as e:
                # Si falla, usar el método alternativo
                pass

        # Método alternativo: crear línea manual compatible
        discount_product = self._get_global_discount_product()

        # Crear descripción con el porcentaje o valor del descuento
        if discount_type == 'percentage':
            description = f'Descuento Global - {discount_name} ({discount_value}%)'
        else:  # fixed_amount
            description = f'Descuento Global - {discount_name} ({self.currency_id.symbol}{discount_value})'

        line_vals = {
            'order_id': self.id,
            'product_id': discount_product.id,
            'name': description,
            'product_uom_qty': 1,
            'price_unit': -discount_amount,
            'discount': 0,
            'sequence': 999,  # Al final del pedido
        }

        # Crear la línea de descuento
        self.env['sale.order.line'].create(line_vals)

    def _get_global_discount_product(self):
        """Obtiene el producto de descuento global del módulo sale_global_discount"""
        # Intentar obtener el producto estándar del módulo sale_global_discount
        try:
            return self.env.ref('sale_global_discount.product_product_global_discount')
        except:
            # Si no existe, crear uno compatible
            return self._create_compatible_discount_product()

    def _create_compatible_discount_product(self):
        """Crea un producto compatible con los módulos de descuento global"""
        return self.env['product.product'].create({
            'name': 'Global Discount',
            'default_code': 'GLOBAL_DISCOUNT',
            'type': 'service',
            'categ_id': self.env.ref('product.product_category_all').id,
            'list_price': 0.0,
            'sale_ok': True,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'taxes_id': False,
        })

    def _remove_partner_discount_lines(self):
        """Elimina las líneas de descuento del cliente aplicadas anteriormente"""
        # Si usa el sistema estándar de descuentos globales
        if hasattr(self, 'global_discount_ids'):
            # Limpiar descuentos globales estándar creados por nuestro módulo
            partner_discounts = self.global_discount_ids.filtered(
                lambda d: 'Descuento Global' in (d.name or '')
            )
            if partner_discounts:
                self.write({
                    'global_discount_ids': [(3, d.id) for d in partner_discounts]
                })
                partner_discounts.unlink()
            return

        # Método alternativo: buscar líneas creadas manualmente
        discount_lines = self.order_line.filtered(
            lambda l: 'Descuento Global' in (l.name or '') or
                     (l.product_id and 'GLOBAL_DISCOUNT' in (l.product_id.default_code or ''))
        )

        if discount_lines:
            discount_lines.unlink()

    @api.onchange('partner_id')
    def _onchange_partner_id_global_discounts(self):
        """Auto-aplicar descuentos del cliente cuando cambie"""
        if (self.partner_id and
            self.partner_id.has_global_discounts and
            not self.partner_global_discounts_applied):

            # Solo auto-aplicar si hay líneas normales de producto
            normal_lines = self.order_line.filtered(
                lambda l: l.product_id and l.display_type not in ['line_section', 'line_note']
            )

            if normal_lines:
                try:
                    self.action_apply_partner_global_discounts()
                except UserError:
                    # Si hay error, no aplicar automáticamente
                    pass

    def _prepare_invoice(self):
        """Transferir información de descuentos a la factura"""
        invoice_vals = super()._prepare_invoice()

        if self.partner_global_discounts_applied:
            invoice_vals['partner_global_discounts_applied'] = True

        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_global_discount_line(self):
        """Verifica si la línea es de descuento global"""
        return (hasattr(self, 'is_global_discount') and self.is_global_discount) or \
               (self.price_unit < 0 and 'Descuento' in (self.name or ''))
