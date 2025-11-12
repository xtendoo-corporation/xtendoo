# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PartnerMergeWizard(models.TransientModel):
    _name = 'partner.merge.wizard'
    _description = 'Partner Merge Wizard'

    duplicate_count = fields.Integer(
        string='Duplicate Partners Found',
        readonly=True,
    )
    email_groups_count = fields.Integer(
        string='Email Groups',
        readonly=True,
    )
    preview_ids = fields.One2many(
        'partner.merge.preview',
        'wizard_id',
        string='Preview',
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('preview', 'Preview'),
        ('done', 'Done'),
    ], default='draft', readonly=True)
    merged_count = fields.Integer(
        string='Merged Partners',
        readonly=True,
    )

    def action_find_duplicates(self):
        """Find all partners with duplicate emails"""
        self.ensure_one()

        # Clear previous preview
        self.preview_ids.unlink()

        # Find partners with duplicate emails
        query = """
            SELECT email, array_agg(id ORDER BY create_date ASC) as partner_ids, count(*) as count
            FROM res_partner
            WHERE email IS NOT NULL
                AND email != ''
                AND active = true
            GROUP BY LOWER(email)
            HAVING count(*) > 1
        """

        self.env.cr.execute(query)
        results = self.env.cr.fetchall()

        duplicate_count = 0
        preview_lines = []

        for email, partner_ids, count in results:
            duplicate_count += len(partner_ids) - 1

            preview_lines.append((0, 0, {
                'email': email,
                'partner_ids': [(6, 0, partner_ids)],
                'master_partner_id': partner_ids[0],  # El más antiguo será el master
                'duplicate_count': count - 1,
            }))

        self.write({
            'duplicate_count': duplicate_count,
            'email_groups_count': len(results),
            'preview_ids': preview_lines,
            'state': 'preview',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'partner.merge.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_merge_all(self):
        """Merge all duplicate partners automatically"""
        self.ensure_one()

        if not self.preview_ids:
            raise UserError(_('No duplicate partners found. Please search for duplicates first.'))

        merged_count = 0

        for preview in self.preview_ids:
            try:
                # El primer partner (más antiguo) será el master
                master = preview.master_partner_id
                duplicates = preview.partner_ids - master

                if duplicates:
                    _logger.info(f'Merging partners with email {preview.email}: '
                               f'{duplicates.ids} into {master.id}')

                    # Usar el método _merge de Odoo si está disponible en v18
                    # o implementar la lógica de merge manual
                    self._merge_partners(master, duplicates)
                    merged_count += len(duplicates)

            except Exception as e:
                _logger.error(f'Error merging partners with email {preview.email}: {str(e)}')
                continue

        self.write({
            'merged_count': merged_count,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'partner.merge.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _merge_partners(self, master, duplicates):
        """Merge duplicate partners into master partner"""
        # Reemplazar referencias en otros modelos
        models_to_update = [
            ('sale.order', 'partner_id'),
            ('sale.order', 'partner_invoice_id'),
            ('sale.order', 'partner_shipping_id'),
            ('account.move', 'partner_id'),
            ('account.move.line', 'partner_id'),
            ('crm.lead', 'partner_id'),
            ('project.project', 'partner_id'),
            ('helpdesk.ticket', 'partner_id'),
            ('account.payment', 'partner_id'),
            ('stock.picking', 'partner_id'),
            ('purchase.order', 'partner_id'),
            ('res.partner.bank', 'partner_id'),
        ]

        for model_name, field_name in models_to_update:
            try:
                if model_name in self.env:
                    model = self.env[model_name]
                    records = model.search([(field_name, 'in', duplicates.ids)])
                    if records:
                        records.write({field_name: master.id})
            except Exception as e:
                _logger.warning(f'Could not update {model_name}.{field_name}: {str(e)}')
                continue

        # Transferir hijos (contactos) al master
        duplicates.child_ids.write({'parent_id': master.id})

        # Fusionar categorías
        master.category_id = [(4, cat.id) for cat in duplicates.category_id]

        # Desactivar o eliminar duplicados
        duplicates.write({'active': False})

    def action_close(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}


class PartnerMergePreview(models.TransientModel):
    _name = 'partner.merge.preview'
    _description = 'Partner Merge Preview'

    wizard_id = fields.Many2one(
        'partner.merge.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    email = fields.Char(string='Email', readonly=True)
    partner_ids = fields.Many2many(
        'res.partner',
        string='Duplicate Partners',
        readonly=True,
    )
    master_partner_id = fields.Many2one(
        'res.partner',
        string='Master Partner',
        readonly=True,
    )
    duplicate_count = fields.Integer(
        string='Duplicates',
        readonly=True,
    )

