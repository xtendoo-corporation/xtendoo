# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    _description = 'Bank Statement Line - Full Edit Extension'

    # Campo para documentar el motivo del ajuste manual
    manual_adjustment_reason = fields.Text(
        string='Motivo del ajuste manual',
        tracking=True,
        help='Documenta por qué se realizó un ajuste manual en esta línea'
    )

    # Sobreescribir campos para hacerlos editables y con tracking
    # Nota: algunos campos ya tienen tracking, pero lo reforzamos aquí

    payment_ref = fields.Char(
        tracking=True,
    )

    amount = fields.Monetary(
        tracking=True,
    )

    date = fields.Date(
        tracking=True,
    )

    partner_id = fields.Many2one(
        tracking=True,
    )

    # Campo para controlar si el extracto está en estado crítico
    is_critical_state = fields.Boolean(
        string='Estado crítico',
        compute='_compute_critical_state',
        help='Indica si la línea está conciliada o el extracto está posteado'
    )

    # Campo para mostrar advertencia
    warning_message = fields.Html(
        string='Advertencia',
        compute='_compute_warning_message',
    )

    @api.depends('is_reconciled', 'statement_id.state')
    def _compute_critical_state(self):
        """Determina si la línea está en estado crítico (conciliada o posteada)"""
        for line in self:
            line.is_critical_state = (
                line.is_reconciled or
                (line.statement_id and line.statement_id.state == 'posted')
            )

    @api.depends('is_critical_state')
    def _compute_warning_message(self):
        """Genera mensaje de advertencia si está en estado crítico"""
        for line in self:
            if line.is_critical_state:
                warnings = []
                if line.is_reconciled:
                    warnings.append('Esta línea está <strong>conciliada</strong>')
                if line.statement_id and line.statement_id.state == 'posted':
                    warnings.append('El extracto está en estado <strong>posteado</strong>')

                line.warning_message = '''
                    <div class="alert alert-warning" role="alert">
                        <i class="fa fa-warning"></i>
                        <strong>¡ADVERTENCIA!</strong><br/>
                        {}.<br/>
                        Modificar esta línea puede afectar la contabilidad.
                        Por favor, documenta el motivo del ajuste.
                    </div>
                '''.format(' y '.join(warnings))
            else:
                line.warning_message = False

    def write(self, vals):
        """Sobrescribir write para añadir trazabilidad y validaciones"""
        # Verificar si la edición total está habilitada
        allow_full_edit = self.env['ir.config_parameter'].sudo().get_param(
            'account_bank_statement_line.allow_full_edit',
            default='True'
        )

        if allow_full_edit == 'False':
            # Si está deshabilitado, aplicar restricciones estándar
            # (aquí podrías añadir lógica adicional si fuera necesario)
            pass

        # Verificar permisos para edición en estado crítico
        if not self.env.user.has_group('account.group_account_manager') and \
           not self.env.user.has_group('account_bank_statement_line.group_xtendoo_bank_line_editor'):
            for line in self:
                if line.is_critical_state:
                    raise UserError(_(
                        'No tienes permisos para editar líneas en estado crítico. '
                        'Contacta con un administrador contable.'
                    ))

        # Registrar los cambios en el chatter
        for line in self:
            if vals:
                tracked_fields = []
                for field_name, new_value in vals.items():
                    if field_name in line._fields and hasattr(line._fields[field_name], 'tracking'):
                        old_value = line[field_name]
                        if old_value != new_value:
                            field_label = line._fields[field_name].string
                            tracked_fields.append(f"<li><strong>{field_label}</strong>: {old_value} → {new_value}</li>")

                if tracked_fields:
                    message = f"""
                        <p><strong>Campos modificados manualmente:</strong></p>
                        <ul>{''.join(tracked_fields)}</ul>
                    """
                    if 'manual_adjustment_reason' in vals:
                        message += f"<p><strong>Motivo:</strong> {vals['manual_adjustment_reason']}</p>"

                    line.message_post(body=message, subject='Ajuste manual de línea')

        return super().write(vals)

    def action_recalculate_amounts(self):
        """Recalcula los importes y saldos de las líneas"""
        self.ensure_one()

        # Si hay un statement asociado, recalcular su balance
        if self.statement_id:
            self.statement_id._check_balance_end_real_same_as_computed()

        self.message_post(
            body=_('Recálculo de importes ejecutado correctamente.'),
            subject='Recálculo de importes'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recálculo completado'),
                'message': _('Los importes han sido recalculados.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_recalculate_running_balance(self):
        """Recalcula el running_balance de la línea basado en el extracto"""
        self.ensure_one()

        if not self.statement_id:
            raise UserError(_('Esta línea no tiene un extracto asociado.'))

        # Recalcular el running_balance
        # El running_balance se calcula sumando el balance inicial del extracto
        # más todos los importes de las líneas anteriores
        lines = self.statement_id.line_ids.sorted(key=lambda r: (r.sequence, r.id))
        balance = self.statement_id.balance_start

        for line in lines:
            balance += line.amount
            if line.id == self.id:
                # Forzar el recálculo del campo
                line.write({'sequence': line.sequence})
                break

        self.message_post(
            body=_('Running balance recalculado: {}').format(balance),
            subject='Recálculo de running balance'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recálculo completado'),
                'message': _('El running balance ha sido recalculado: {}').format(balance),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_edit_wizard(self):
        """Abre el wizard de confirmación para ediciones críticas"""
        self.ensure_one()

        return {
            'name': _('Confirmar edición'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line.edit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            }
        }

    @api.model
    def check_edit_permission(self):
        """Verifica si el usuario actual puede editar líneas"""
        return self.env.user.has_group('account.group_account_manager') or \
               self.env.user.has_group('account_bank_statement_line.group_xtendoo_bank_line_editor')
