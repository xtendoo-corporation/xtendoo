# © 2024 Xtendoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    package_carrier_type = fields.Selection(selection_add=[('envia', 'Envia')])
    shipper_package_code = fields.Char(compute='_compute_package_code', store=True, readonly=False)
    envia_mail_type = fields.Selection(
        selection=[
            ('pallet', 'Pallet'),
            ('box', 'Box'),
            ('envelope', 'Envelope'),
        ],
        string="Envia Package Type",
        help="Selecciona el tipo de paquete para el envío",
        default="box",
    )

    @api.depends('envia_mail_type', 'package_carrier_type')
    def _compute_package_code(self):
        for package in self:
            if package.package_carrier_type == 'envia':
                package.shipper_package_code = package.envia_mail_type
            else:
                package.shipper_package_code = package.shipper_package_code

    @api.constrains('packaging_length', 'width', 'height', 'package_carrier_type')
    def _check_envia_required_value(self):
        for record in self:
            if record.package_carrier_type == 'envia' and \
                    any(dim <= 0 for dim in (record.packaging_length, record.width, record.height)):
                raise ValidationError(_('La longitud, anchura y altura son necesarias para un paquete Envia.'))

    @api.depends('package_carrier_type')
    def _compute_length_uom_name(self):
        """Mantiene la UoM de longitud por defecto y la convierte más adelante."""
        super()._compute_length_uom_name()
        uom_name = self.env['product.template']._get_length_uom_name_from_ir_config_parameter()
        for package in self:
            if package.package_carrier_type == 'envia':
                package.length_uom_name = uom_name

