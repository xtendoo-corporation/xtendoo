from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    global_discount_ids = fields.One2many(
        'res.partner.discount',
        'partner_id',
        string='Descuentos Globales',
        help="Descuentos que se aplicarán automáticamente en ventas"
    )

    has_global_discounts = fields.Boolean(
        string='Tiene Descuentos Globales',
        compute='_compute_has_global_discounts',
        store=True
    )

    @api.depends('global_discount_ids', 'global_discount_ids.active', 'parent_id', 'parent_id.global_discount_ids', 'parent_id.global_discount_ids.active')
    def _compute_has_global_discounts(self):
        for partner in self:
            # Verificar descuentos propios
            own_discounts = bool(partner.global_discount_ids.filtered('active'))

            # Verificar descuentos del padre si existe
            parent_discounts = False
            if partner.parent_id:
                parent_discounts = bool(partner.parent_id.global_discount_ids.filtered('active'))

            partner.has_global_discounts = own_discounts or parent_discounts

    def get_applicable_discounts(self, document_type, amount, date=None, journal_id=None):
        """
        Obtiene los descuentos aplicables para un tipo de documento y importe
        Incluye descuentos propios y del contacto padre si existe
        """
        self.ensure_one()
        applicable_discounts = []

        # Obtener descuentos propios
        for discount in self.global_discount_ids.filtered('active'):
            if discount.is_applicable(document_type, amount, date, journal_id):
                applicable_discounts.append(discount)

        # Obtener descuentos del contacto padre si existe
        if self.parent_id:
            for discount in self.parent_id.global_discount_ids.filtered('active'):
                if discount.is_applicable(document_type, amount, date, journal_id):
                    applicable_discounts.append(discount)

        # Ordenar por secuencia para aplicación correcta
        applicable_discounts.sort(key=lambda d: d.sequence if hasattr(d, 'sequence') else 0)

        return applicable_discounts

    def calculate_total_discount(self, document_type, base_amount, date=None, journal_id=None):
        """
        Calcula el descuento total aplicable
        """
        self.ensure_one()
        applicable_discounts = self.get_applicable_discounts(
            document_type, base_amount, date, journal_id
        )

        total_discount = 0.0
        remaining_amount = base_amount

        # Aplicar descuentos en orden de secuencia
        for discount in applicable_discounts:
            discount_amount = discount.calculate_discount_amount(remaining_amount)
            total_discount += discount_amount
            remaining_amount -= discount_amount

        return total_discount
