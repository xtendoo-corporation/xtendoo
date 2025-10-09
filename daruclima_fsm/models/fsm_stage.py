# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _
import re


class DaruclimeFSMStage(models.Model):
    _name = 'daruclima.fsm.stage'
    _description = 'Etapas de Orden de Trabajo'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nombre',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Código',
        required=True,
        help="Código único para identificar la etapa"
    )
    description = fields.Text(string='Descripción')
    sequence = fields.Integer(string='Secuencia', default=10)

    # Estado de la etapa
    is_closed = fields.Boolean(
        string='Etapa Cerrada',
        help="Las órdenes en esta etapa se consideran completadas"
    )
    is_default = fields.Boolean(
        string='Etapa por Defecto',
        help="Esta etapa se asigna por defecto a nuevas órdenes"
    )

    # Apariencia
    color = fields.Char(
        string='Color',
        default='#FFFFFF',
        help="Color hexadecimal para mostrar en vistas kanban"
    )

    # Configuración
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    # Estadísticas
    order_count = fields.Integer(
        string='Número de Órdenes',
        compute='_compute_order_count'
    )

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'El código de la etapa debe ser único.'),
        ('default_unique', 'EXCLUDE (company_id WITH =) WHERE (is_default = true)',
         'Solo puede haber una etapa por defecto por compañía.'),
    ]

    @api.depends('name')
    def _compute_order_count(self):
        """Compute the number of FSM orders in this stage"""
        for record in self:
            orders = self.env['daruclima.fsm.order'].search([
                ('stage_id', '=', record.id)
            ])
            record.order_count = len(orders)

    def _generate_code_from_name(self, name):
        """Genera un código automáticamente basado en el nombre"""
        if not name:
            return 'stage'

        # Convertir a minúsculas y reemplazar espacios y caracteres especiales
        code = re.sub(r'[^a-zA-Z0-9\s]', '', name.lower())
        code = re.sub(r'\s+', '_', code.strip())

        # Asegurar que el código sea único
        base_code = code
        counter = 1
        while self.search([('code', '=', code)]):
            code = f"{base_code}_{counter}"
            counter += 1

        return code

    @api.model_create_multi
    def create(self, vals_list):
        """Crear etapas con validaciones"""
        for vals in vals_list:
            # Validar que el código sea válido
            if 'code' in vals and vals['code']:
                vals['code'] = re.sub(r'[^a-zA-Z0-9_]', '_', vals['code']).lower()
            # Generar código automáticamente si no se proporciona
            if not vals.get('code') and vals.get('name'):
                vals['code'] = self._generate_code_from_name(vals['name'])
            elif not vals.get('code'):
                vals['code'] = 'stage_' + str(len(self.search([])) + 1)

            # Asegurar que solo hay una etapa por defecto
            if vals.get('is_default'):
                self.search([
                    ('is_default', '=', True),
                    ('company_id', '=', vals.get('company_id', self.env.company.id))
                ]).write({'is_default': False})
        return super().create(vals_list)

    @api.constrains('code')
    def _check_code_format(self):
        """Validar formato del código"""
        for record in self:
            if not re.match(r'^[a-zA-Z0-9_]+$', record.code):
                raise ValidationError(_('El código debe contener solo letras, números y guiones bajos.'))

    def write(self, vals):
        """Asegurar que solo hay una etapa por defecto"""
        if vals.get('is_default'):
            for record in self:
                self.search([
                    ('is_default', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ]).write({'is_default': False})
        return super().write(vals)


class DaruclimeFSMTag(models.Model):
    _name = 'daruclima.fsm.tag'
    _description = 'Etiquetas de Servicio'
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
        translate=True
    )
    description = fields.Text(string='Descripción')

    # Apariencia
    color = fields.Integer(string='Color', default=0)

    # Configuración
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    # Estadísticas
    order_count = fields.Integer(
        string='Órdenes con esta Etiqueta',
        compute='_compute_order_count'
    )

    @api.depends('name')
    def _compute_order_count(self):
        for tag in self:
            tag.order_count = self.env['daruclima.fsm.order'].search_count([
                ('tag_ids', 'in', [tag.id])
            ])

    def action_view_orders(self):
        """Ver órdenes con esta etiqueta"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Órdenes - {self.name}',
            'res_model': 'daruclima.fsm.order',
            'view_mode': 'tree,form,kanban',
            'domain': [('tag_ids', 'in', [self.id])],
            'context': {'default_tag_ids': [(6, 0, [self.id])]}
        }
