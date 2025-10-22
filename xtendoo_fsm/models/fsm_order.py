# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class XtendooFSMOrder(models.Model):
    _name = 'fsm.order'
    _description = 'Orden de Trabajo'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'priority_level desc, date_scheduled asc, id desc'
    _rec_name = 'name'

    # Campos básicos
    name = fields.Char(
        string='Número',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
        tracking=True
    )

    # Información del cliente y ubicación
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        help="Cliente final para quien se realiza el servicio"
    )
    location_id = fields.Many2one(
        'res.partner',
        string='Dirección del Servicio',
        tracking=True,
        domain="[('parent_id', '=', partner_id)]",
        help="Dirección de entrega donde se realizará el servicio"
    )
    contact_id = fields.Many2one(
        'res.partner',
        string='Contacto',
        help="Persona o empresa de contacto en la ubicación del servicio"
    )

    # Información del servicio
    description = fields.Text(
        string='Descripción del Trabajo',
        required=True,
        tracking=True
    )
    internal_note = fields.Text(
        string='Notas Internas',
        help="Notas internas no visibles para el cliente"
    )
    customer_note = fields.Text(
        string='Notas del Cliente',
        help="Notas visibles para el cliente"
    )

    # Gestión de estados y prioridades
    stage_id = fields.Many2one(
        'fsm.stage',
        string='Etapa',
        required=True,
        tracking=True,
        group_expand='_read_group_stage_ids',
        default=lambda self: self._get_default_stage()
    )
    priority_level = fields.Selection(
        selection=[
            ('0', 'Muy Baja'),
            ('1', 'Baja'),
            ('2', 'Normal'),
            ('3', 'Alta'),
            ('4', 'Muy Alta'),
            ('5', 'Urgente')
        ],
        string='Prioridad',
        default='2',
        tracking=True
    )

    color = fields.Char(string='Color', related='stage_id.color', store=True)
    is_closed = fields.Boolean(string='Cerrado', related='stage_id.is_closed', store=True)

    # Fechas y tiempo
    date_created = fields.Datetime(
        string='Fecha de Creación',
        default=fields.Datetime.now,
        readonly=True
    )
    date_scheduled = fields.Datetime(
        string='Fecha Programada',
        tracking=True,
        help="Fecha y hora programada para el servicio"
    )
    date_start = fields.Datetime(
        string='Fecha de Inicio',
        tracking=True
    )
    date_end = fields.Datetime(
        string='Fecha de Finalización',
        tracking=True
    )
    duration = fields.Float(
        string='Duración (Horas)',
        compute='_compute_duration',
        store=True,
        help="Duración del trabajo en horas"
    )

    responsible_id = fields.Many2one(
        'hr.employee',
        string='Técnico Responsable',
        tracking=True,
        help="Empleado responsable de esta orden de trabajo"
    )

    # Técnicos (eliminamos la referencia al equipo inexistente)
    person_ids = fields.Many2many(
        'hr.employee',
        'xtendoo_fsm_order_employee_rel',
        'order_id',
        'employee_id',
        string='Técnicos Asignados',
        tracking=True,
        help="Empleados asignados a esta orden de trabajo"
    )

    # Equipos y servicios
    tag_ids = fields.Many2many(
        'fsm.tag',
        string='Etiquetas',
        help="Etiquetas para clasificar y analizar órdenes"
    )

    # Integración con reparaciones
    repair_order_ids = fields.One2many(
        'repair.order',
        'fsm_order_id',
        string='Partes de Reparación',
        help="Partes de reparación relacionados con esta orden de trabajo"
    )
    repair_count = fields.Integer(
        string='Número de Reparaciones',
        compute='_compute_repair_count'
    )

    # Integración con órdenes de venta
    sale_order_ids = fields.One2many(
        'sale.order',
        'fsm_order_id',
        string='Órdenes de Venta',
        help="Órdenes de venta relacionadas con esta orden de trabajo"
    )
    sale_count = fields.Integer(
        string='Número de Órdenes de Venta',
        compute='_compute_sale_count'
    )

    # Portal
    access_url = fields.Char(
        string='URL de Acceso',
        compute='_compute_access_url'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        help="Compañía para la que se realiza esta orden de trabajo"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('fsm.order') or _('Nuevo')
            # Garantizar etapa por defecto si no viene informada
            if not vals.get('stage_id'):
                vals['stage_id'] = self._get_default_stage()
        return super().create(vals_list)

    def _get_default_stage(self):
        """Obtiene la etapa por defecto de forma robusta y devuelve su id"""
        Stage = self.env['fsm.stage'].sudo()
        # Primero intentar buscar una etapa marcada como por defecto
        stage = Stage.search([
            ('is_default', '=', True),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)

        # Si no hay etapa por defecto, buscar por código 'new'
        if not stage:
            stage = Stage.search([
                ('code', '=', 'new'),
                ('company_id', 'in', [self.env.company.id, False])
            ], limit=1)

        # Si tampoco existe, tomar la primera etapa disponible
        if not stage:
            stage = Stage.search([
                ('company_id', 'in', [self.env.company.id, False])
            ], limit=1)

        return stage.id if stage else False

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                record.duration = delta.total_seconds() / 3600.0
            else:
                record.duration = 0.0

    def _compute_repair_count(self):
        """Calcula el número de reparaciones relacionadas"""
        for record in self:
            record.repair_count = len(record.repair_order_ids)

    def _compute_sale_count(self):
        """Calcula el número de órdenes de venta relacionadas"""
        for record in self:
            record.sale_count = len(record.sale_order_ids)

    def _compute_access_url(self):
        for record in self:
            record.access_url = f'/my/fsm/{record.id}'

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Expand stage_ids for kanban view"""
        stage_ids = self.env['fsm.stage'].search([
            ('company_id', 'in', [self.env.company.id, False])
        ])
        return stage_ids

    def action_start_work(self):
        """Inicia el trabajo"""
        if self.date_start:
            raise UserError(_('El trabajo ya ha sido iniciado.'))

        self.write({
            'date_start': fields.Datetime.now(),
        })

        # Cambiar a etapa "En Progreso" si existe
        progress_stage = self.env['fsm.stage'].search([
            ('code', '=', 'progress'),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)
        if progress_stage:
            self.stage_id = progress_stage

        return True

    def action_finish_work(self):
        """Finaliza el trabajo"""
        if not self.date_start:
            raise UserError(_('Debe iniciar el trabajo antes de finalizarlo.'))

        if self.date_end:
            raise UserError(_('El trabajo ya ha sido finalizado.'))

        self.write({
            'date_end': fields.Datetime.now(),
        })

        # Cambiar a etapa "Completado" si existe
        done_stage = self.env['fsm.stage'].search([
            ('code', '=', 'done'),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)
        if done_stage:
            self.stage_id = done_stage

        return True

    def action_print_order(self):
        """Imprimir orden de trabajo"""
        return self.env.ref('xtendoo_fsm.action_report_fsm_order').report_action(self)

    def action_create_repair(self):
        """Crea un parte de reparación basado en la orden de trabajo"""
        # Valores básicos para la creación de la reparación
        repair_vals = {
            'partner_id': self.partner_id.id,
            'fsm_order_id': self.id,  # Vincular con la orden FSM
            'name': f'{self.description or _("Reparación desde Orden de Trabajo")} - Ref: {self.name}',
        }

        try:
            repair_order = self.env['repair.order'].create(repair_vals)

            return {
                'type': 'ir.actions.act_window',
                'name': _('Parte de Reparación'),
                'res_model': 'repair.order',
                'res_id': repair_order.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            raise UserError(_('Error al crear el parte de reparación: %s') % str(e))

    def action_view_repairs(self):
        """Ver partes de reparación relacionados"""
        if len(self.repair_order_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Parte de Reparación'),
                'res_model': 'repair.order',
                'res_id': self.repair_order_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Partes de Reparación'),
                'res_model': 'repair.order',
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.repair_order_ids.ids)],
                'target': 'current',
            }

    def action_create_sale_order(self):
        """Crea una orden de venta basada en la orden de trabajo"""
        self.ensure_one()
        sale_order_vals = {
            'partner_id': self.partner_id.id,
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Venta'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
        }

    def action_view_sale_orders(self):
        """Ver órdenes de venta relacionadas"""
        if len(self.sale_order_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Orden de Venta'),
                'res_model': 'sale.order',
                'res_id': self.sale_order_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Órdenes de Venta'),
                'res_model': 'sale.order',
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.sale_order_ids.ids)],
                'target': 'current',
            }
