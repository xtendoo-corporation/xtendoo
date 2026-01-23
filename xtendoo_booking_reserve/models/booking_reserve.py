from odoo import models, fields


class BookingReserve(models.Model):
    _name = 'xtendoo.booking.reserve'
    _description = 'Reserva Website'

    name = fields.Char(string='Nombre', required=True)
    phone = fields.Char(string='Teléfono', required=True)
    email = fields.Char(string='Email')
    date = fields.Date(string='Fecha seleccionada')
