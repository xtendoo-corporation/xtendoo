# -*- coding: utf-8 -*-
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class UpdateExpirationDate(models.AbstractModel):
    _name = 'update.expiration.date'
    _description = 'Actualizar fecha de expiración de la base de datos'

    @api.model
    def _update_expiration_date(self):
        """
        Método que actualiza la fecha de expiración de la base de datos
        a '2050-12-30 00:00:00'
        """
        try:
            # Buscamos el registro con la clave 'database.expiration_date'
            param = self.env['ir.config_parameter'].sudo().search([
                ('key', '=', 'database.expiration_date')
            ], limit=1)

            # Si existe, actualizamos su valor
            if param:
                param.write({
                    'value': '2050-12-30 00:00:00'
                })
                _logger.info("Fecha de expiración de la base de datos actualizada correctamente a '2050-12-30 00:00:00'")
            else:
                # Si no existe, lo creamos
                self.env['ir.config_parameter'].sudo().create({
                    'key': 'database.expiration_date',
                    'value': '2050-12-30 00:00:00'
                })
                _logger.info("Parámetro 'database.expiration_date' creado con valor '2050-12-30 00:00:00'")

            return True
        except Exception as e:
            _logger.error("Error al actualizar la fecha de expiración de la base de datos: %s", str(e))
            return False
