from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartnerDiscount(models.Model):
    _name = 'res.partner.discount'
    _description = 'Descuentos Globales por Cliente'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nombre del Descuento',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade'
    )
    discount_type = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Importe Fijo')
    ], string='Tipo de Descuento', required=True, default='percentage')

    discount_value = fields.Float(
        string='Valor del Descuento',
        required=True,
        help="Porcentaje (0-100) o importe fijo según el tipo"
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help="Orden de aplicación de los descuentos"
    )

    active = fields.Boolean(
        string='Activo',
        default=True
    )

    date_start = fields.Date(
        string='Fecha Inicio',
        help="Fecha desde la cual el descuento es válido"
    )

    date_end = fields.Date(
        string='Fecha Fin',
        help="Fecha hasta la cual el descuento es válido"
    )

    document_types = fields.Selection([
        ('all', 'Todos los Documentos'),
        ('quotation', 'Solo Presupuestos'),
        ('sale_order', 'Solo Pedidos de Venta'),
        ('invoice', 'Solo Facturas')
    ], string='Aplicar en', default='all', help="Tipo de documento donde aplicar el descuento")

    min_amount = fields.Float(
        string='Importe Mínimo',
        default=0.0,
        help="Importe mínimo del documento para aplicar el descuento"
    )

    max_amount = fields.Float(
        string='Importe Máximo',
        default=0.0,
        help="Importe máximo del documento para aplicar el descuento (0 = sin límite)"
    )

    journal_ids = fields.Many2many(
        'account.journal',
        'partner_discount_journal_rel',
        'discount_id',
        'journal_id',
        string='Diarios de Facturación',
        domain="[('type', '=', 'sale')]",
        help="Diarios de facturación donde se aplica el descuento. Si no se especifica ninguno, se aplica en todos los diarios"
    )

    @api.constrains('discount_value')
    def _check_discount_value(self):
        for record in self:
            if record.discount_type == 'percentage' and (record.discount_value < 0 or record.discount_value > 100):
                raise ValidationError("El porcentaje de descuento debe estar entre 0 y 100.")
            if record.discount_type == 'fixed' and record.discount_value < 0:
                raise ValidationError("El importe fijo no puede ser negativo.")

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

    def is_applicable(self, document_type, amount, date=None, journal_id=None):
        """
        Verifica si el descuento es aplicable para el tipo de documento, importe, fecha y diario dados
        """
        self.ensure_one()

        # Verificar si está activo
        if not self.active:
            return False

        # Verificar tipo de documento
        if self.document_types != 'all' and self.document_types != document_type:
            return False

        # Verificar diario de facturación (solo aplica para facturas)
        if document_type == 'invoice' and journal_id and self.journal_ids:
            if journal_id not in self.journal_ids.ids:
                return False

        # Verificar importe mínimo
        if self.min_amount > 0 and amount < self.min_amount:
            return False

        # Verificar importe máximo
        if self.max_amount > 0 and amount > self.max_amount:
            return False

        # Verificar fechas
        if date:
            if self.date_start and date < self.date_start:
                return False
            if self.date_end and date > self.date_end:
                return False

        return True

    def calculate_discount_amount(self, base_amount):
        """
        Calcula el importe del descuento basado en el importe base
        """
        self.ensure_one()

        if self.discount_type == 'percentage':
            return base_amount * (self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return min(self.discount_value, base_amount)  # No puede ser mayor al importe base

        return 0.0
