# © 2024 Xtendoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class EnviaShippingWizard(models.TransientModel):
    _name = "envia.shipping.wizard"
    _description = "Selecciona el método de envío de Envia.com disponible"

    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string="Método de Envío",
    )
    # En Odoo 17, fields.Json está disponible sin el parámetro export_string_translation
    available_services = fields.Json(
        string="Servicios Disponibles",
        help="Contiene la lista de servicios disponibles para la cuenta Envia.com donde seleccionar.",
    )
    selected_service_code = fields.Char(string="Servicio Seleccionado")
    selected_carrier_code = fields.Char(string="Carrier Seleccionado")

    @api.constrains('selected_service_code', 'selected_carrier_code')
    def _check_codes(self):
        for record in self:
            for service in (record.available_services or []):
                if service['name'] == record.selected_service_code and service['carrier_name'] == record.selected_carrier_code:
                    break
            else:
                raise ValidationError(_("El carrier y servicio deben seleccionarse de la lista de métodos de envío disponibles."))

    def action_validate(self):
        self.ensure_one()
        selected_service = next(
            service for service in self.available_services
            if service['name'] == self.selected_service_code
            if service['carrier_name'] == self.selected_carrier_code
        )
        self.carrier_id.write({
            'envia_service_code': selected_service['name'],
            'envia_carrier_code': selected_service['carrier_name'],
            'envia_service_name': "{}: {} ({})".format(
                selected_service['carrier_name'].upper(),
                selected_service['description'],
                selected_service['name'],
            ),
        })

