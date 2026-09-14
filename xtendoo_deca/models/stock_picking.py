# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    deca_document_ids = fields.One2many(
        'xtendoo.deca.document', 'picking_id', string='Documentos DeCA')
    deca_document_count = fields.Integer(compute='_compute_deca_document_count')

    deca_cargador_partner_id = fields.Many2one(
        'res.partner', string='Cargador contractual (DeCA)',
        default=lambda self: self.env.company.partner_id,
        help='Empresa que contrata el transporte del envío (normalmente la '
             'propia compañía). Art. 6.a) Orden FOM/2861/2012.')
    deca_transportista_partner_id = fields.Many2one(
        'res.partner', string='Transportista efectivo (DeCA)',
        help='Empresa de transporte que realiza materialmente el porte. '
             'Art. 6.b) Orden FOM/2861/2012.')
    deca_matricula_vehiculo = fields.Char(string='Matrícula del vehículo (DeCA)')
    deca_autorizacion_especial = fields.Char(string='Autorización especial de circulación (DeCA)')
    deca_observaciones = fields.Text(string='Observaciones (DeCA)')

    def _compute_deca_document_count(self):
        for picking in self:
            picking.deca_document_count = len(picking.deca_document_ids)

    def _deca_get_mercancia_naturaleza(self):
        self.ensure_one()
        lines = self.move_ids.filtered(lambda m: m.product_uom_qty)
        return '\n'.join(
            '%s - %s %s' % (m.product_id.display_name, m.product_uom_qty, m.product_uom.name)
            for m in lines
        ) or 'N/D'

    def _deca_get_mercancia_peso(self):
        self.ensure_one()
        return sum(
            m.product_uom_qty * (m.product_id.weight or 0.0)
            for m in self.move_ids
        )

    def action_generar_deca(self):
        self.ensure_one()
        if not self.deca_transportista_partner_id:
            raise UserError(
                'Indique el transportista efectivo (DeCA) antes de generar el documento.')
        if not self.deca_cargador_partner_id:
            raise UserError(
                'Indique el cargador contractual (DeCA) antes de generar el documento.')
        doc = self.env['xtendoo.deca.document'].create({
            'picking_id': self.id,
            'company_id': self.company_id.id,
            'cargador_partner_id': self.deca_cargador_partner_id.id,
            'cargador_nif': self.deca_cargador_partner_id.vat or '',
            'transportista_partner_id': self.deca_transportista_partner_id.id,
            'transportista_nif': self.deca_transportista_partner_id.vat or '',
            'origen': (self.picking_type_id.warehouse_id.partner_id.display_name
                       or self.location_id.display_name),
            'destino': self.partner_id.display_name or self.location_dest_id.display_name,
            'mercancia_naturaleza': self._deca_get_mercancia_naturaleza(),
            'mercancia_peso': self._deca_get_mercancia_peso(),
            'matricula_vehiculo': self.deca_matricula_vehiculo,
            'autorizacion_especial': self.deca_autorizacion_especial,
            'fecha_servicio': self.scheduled_date,
            'observaciones': self.deca_observaciones,
        })
        doc._generate_pdf()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'xtendoo.deca.document',
            'res_id': doc.id,
            'view_mode': 'form',
            'target': 'current',
        }
