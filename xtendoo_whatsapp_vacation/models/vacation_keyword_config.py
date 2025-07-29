from odoo import models, fields, api


class VacationKeywordConfig(models.Model):
    _name = 'vacation.keyword.config'
    _description = 'Configuración de Palabras Clave para Vacaciones por WhatsApp'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre descriptivo de la configuración'
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de prioridad para el procesamiento'
    )

    keyword = fields.Char(
        string='Palabra Clave',
        required=True,
        help='Palabra o frase que activará la solicitud de vacaciones (ej: /vacaciones)'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está activo, esta palabra clave será reconocida por el sistema'
    )

    description = fields.Text(
        string='Descripción',
        help='Descripción de cuándo se usa esta palabra clave'
    )

    @api.model
    def get_active_vacation_keywords(self):
        """
        Obtiene todas las palabras clave activas para vacaciones
        """
        keywords = self.search([('active', '=', True)])
        return [keyword.keyword.lower() for keyword in keywords]

    @api.constrains('keyword')
    def _check_keyword_unique(self):
        for record in self:
            if record.keyword:
                existing = self.search([
                    ('keyword', '=ilike', record.keyword),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise models.ValidationError(
                        f"La palabra clave '{record.keyword}' ya existe en otra configuración activa."
                    )
