# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class AccountBankStatementLineEditWizard(models.TransientModel):
    _name = 'account.bank.statement.line.edit.wizard'
    _description = 'Wizard para confirmar edición de líneas críticas'

    line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Línea de extracto',
        required=True,
        readonly=True,
    )

    is_reconciled = fields.Boolean(
        string='¿Está conciliada?',
        related='line_id.is_reconciled',
        readonly=True,
    )

    statement_state = fields.Selection(
        related='line_id.statement_id.state',
        string='Estado del extracto',
        readonly=True,
    )

    warning_message = fields.Html(
        string='Advertencia',
        compute='_compute_warning_message',
    )

    adjustment_reason = fields.Text(
        string='Motivo del ajuste',
        required=True,
        help='Documenta por qué necesitas hacer este cambio'
    )

    confirm_risks = fields.Boolean(
        string='Confirmo que entiendo los riesgos',
        required=True,
    )

    @api.depends('is_reconciled', 'statement_state')
    def _compute_warning_message(self):
        """Genera mensaje de advertencia detallado"""
        for wizard in self:
            warnings = []
            risks = []

            if wizard.is_reconciled:
                warnings.append('La línea está <strong>conciliada</strong>')
                risks.append('• Descuadres en la conciliación bancaria')
                risks.append('• Posibles diferencias en el balance')

            if wizard.statement_state == 'posted':
                warnings.append('El extracto está <strong>posteado</strong>')
                risks.append('• Afectación a asientos contables ya registrados')
                risks.append('• Posibles inconsistencias en informes financieros')

            if warnings:
                wizard.warning_message = '''
                    <div class="alert alert-danger" role="alert">
                        <h4><i class="fa fa-exclamation-triangle"></i> <strong>ADVERTENCIA CRÍTICA</strong></h4>
                        <p>{}</p>
                        <p><strong>Riesgos de editar esta línea:</strong></p>
                        <ul>{}</ul>
                        <p><strong>Recomendaciones:</strong></p>
                        <ul>
                            <li>• Documenta detalladamente el motivo del cambio</li>
                            <li>• Verifica los totales después del cambio</li>
                            <li>• Notifica al departamento contable</li>
                            <li>• Revisa los informes afectados</li>
                        </ul>
                    </div>
                '''.format(
                    ' y '.join(warnings),
                    ''.join([f'<li>{r}</li>' for r in risks])
                )
            else:
                wizard.warning_message = '<div class="alert alert-info">No hay advertencias críticas.</div>'

    def action_confirm_edit(self):
        """Confirma la edición y registra la trazabilidad"""
        self.ensure_one()

        # Registrar en el chatter que se confirmó la edición crítica
        self.line_id.message_post(
            body=_('''
                <p><strong>EDICIÓN EN ESTADO CRÍTICO AUTORIZADA</strong></p>
                <p><strong>Usuario:</strong> {}</p>
                <p><strong>Motivo:</strong></p>
                <p>{}</p>
                <p><strong>Advertencias aceptadas:</strong></p>
                <ul>
                    <li>Línea conciliada: {}</li>
                    <li>Extracto posteado: {}</li>
                </ul>
            ''').format(
                self.env.user.name,
                self.adjustment_reason or 'No especificado',
                'Sí' if self.is_reconciled else 'No',
                'Sí' if self.statement_state == 'posted' else 'No',
            ),
            subject='Autorización de edición crítica'
        )

        # Actualizar el motivo en la línea
        self.line_id.write({
            'manual_adjustment_reason': self.adjustment_reason,
        })

        # Retornar acción para abrir el formulario de la línea
        return {
            'name': _('Editar línea de extracto'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'res_id': self.line_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Cancela la edición"""
        return {'type': 'ir.actions.act_window_close'}
