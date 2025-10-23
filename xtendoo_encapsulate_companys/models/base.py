from odoo import models, api, fields, _
import logging

_logger = logging.getLogger(__name__)


# Aplicamos el override directamente al modelo base para evitar el bucle de herencia.
class Base(models.AbstractModel):
    _inherit = 'base'  # Indicamos que esta clase modifica la clase 'base'

    @api.model
    def create(self, vals):
        def get_company_id():
            company_id = self.env.context.get('allowed_company_ids')
            if company_id:
                if isinstance(company_id, list):
                    return company_id[0]
                return company_id
            if hasattr(self.env, 'user') and self.env.user and self.env.user.company_id:
                return self.env.user.company_id.id
            return self.env.company.id

        def assign_company(val_dict):
            # Solo asignar si no existe y no está en vals (None/False también cuenta como asignado)
            if 'company_id' in self._fields and ('company_id' not in val_dict or not val_dict['company_id']):
                val_dict['company_id'] = get_company_id()
                _logger.info(
                    f"Asignando company_id={val_dict['company_id']} automáticamente "
                    f"al crear un registro en el modelo {self._name}."
                )

        if isinstance(vals, dict):
            assign_company(vals)
        elif isinstance(vals, list):
            for val_dict in vals:
                assign_company(val_dict)

        return super(Base, self).create(vals)
