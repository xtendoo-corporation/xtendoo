# -*- coding: utf-8 -*-
# Copyright 2024 Xtendoo - https://xtendoo.es
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class BankStatementAuditExportXlsx(models.TransientModel):
    """
    Wizard para exportar las líneas de auditoría bancaria a Excel (XLSX).

    Características:
    - Exporta exactamente las columnas visibles
    - Respeta los filtros aplicados en la vista
    - Incluye el saldo acumulado
    - Nombre de archivo descriptivo con diario y rango de fechas
    - Optimizado para miles de líneas
    """
    _name = 'bank.statement.audit.export.xlsx'
    _description = 'Export Bank Statement Audit to XLSX'

    # =========================================================================
    # CAMPOS DEL WIZARD
    # =========================================================================

    # Campo para almacenar el archivo generado
    xlsx_file = fields.Binary(
        string='Archivo Excel',
        readonly=True,
    )
    xlsx_filename = fields.Char(
        string='Nombre del archivo',
        readonly=True,
    )

    # Campos para filtros (se rellenan desde el contexto)
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario Bancario',
    )
    date_from = fields.Date(
        string='Fecha Desde',
    )
    date_to = fields.Date(
        string='Fecha Hasta',
    )

    # IDs de las líneas a exportar (pasados desde la vista)
    line_ids = fields.Many2many(
        comodel_name='bank.statement.audit',
        string='Líneas a exportar',
    )

    # Estado del wizard
    state = fields.Selection([
        ('config', 'Configuración'),
        ('done', 'Completado'),
    ], default='config', string='Estado')

    # =========================================================================
    # MÉTODOS PRINCIPALES
    # =========================================================================

    @api.model
    def default_get(self, fields_list):
        """
        Obtiene valores por defecto desde el contexto.
        Recoge los IDs seleccionados o el dominio activo.
        """
        res = super().default_get(fields_list)

        context = self.env.context
        active_ids = context.get('active_ids', [])
        active_domain = context.get('active_domain', [])

        if active_ids:
            res['line_ids'] = [(6, 0, active_ids)]
        elif active_domain:
            # Si hay un dominio activo, buscar las líneas que coinciden
            lines = self.env['bank.statement.audit'].search(active_domain)
            res['line_ids'] = [(6, 0, lines.ids)]

        return res

    def action_export(self):
        """
        Acción principal para generar el archivo Excel.

        Returns:
            dict: Acción para descargar el archivo o recargar el wizard
        """
        self.ensure_one()

        if not xlsxwriter:
            raise UserError(_(
                'La librería xlsxwriter no está instalada. '
                'Por favor, instálela con: pip install xlsxwriter'
            ))

        # Obtener las líneas a exportar
        if self.line_ids:
            lines = self.line_ids.sorted(lambda x: (x.date, x.id))
        else:
            # Si no hay líneas seleccionadas, exportar todas visibles
            domain = [('company_id', 'in', self.env.companies.ids)]
            if self.journal_id:
                domain.append(('journal_id', '=', self.journal_id.id))
            if self.date_from:
                domain.append(('date', '>=', self.date_from))
            if self.date_to:
                domain.append(('date', '<=', self.date_to))
            lines = self.env['bank.statement.audit'].search(
                domain, order='date asc, id asc'
            )

        if not lines:
            raise UserError(_('No hay líneas para exportar.'))

        # Generar el archivo Excel
        xlsx_data = self._generate_xlsx(lines)

        # Generar nombre del archivo
        filename = self._generate_filename(lines)

        # Guardar en el wizard
        self.write({
            'xlsx_file': base64.b64encode(xlsx_data),
            'xlsx_filename': filename,
            'state': 'done',
        })

        # Retornar acción para descargar
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=%s&id=%d&field=xlsx_file&filename=%s&download=true' % (
                self._name, self.id, filename
            ),
            'target': 'self',
        }

    def _generate_xlsx(self, lines):
        """
        Genera el contenido del archivo Excel.

        Args:
            lines: Recordset de bank.statement.audit

        Returns:
            bytes: Contenido binario del archivo XLSX
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # =====================================================================
        # FORMATOS
        # =====================================================================

        # Formato para cabeceras
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4A90D9',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        # Formato para fechas
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1,
            'align': 'center',
        })

        # Formato para moneda (positivo)
        money_format = workbook.add_format({
            'num_format': '#,##0.00 €',
            'border': 1,
            'align': 'right',
        })

        # Formato para moneda (negativo)
        money_format_negative = workbook.add_format({
            'num_format': '#,##0.00 €',
            'border': 1,
            'align': 'right',
            'font_color': 'red',
        })

        # Formato para texto
        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })

        # Formato para texto centrado
        text_center_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        # Formato para totales
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8E8E8',
            'border': 1,
            'num_format': '#,##0.00 €',
            'align': 'right',
        })

        total_text_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8E8E8',
            'border': 1,
            'align': 'left',
        })

        # =====================================================================
        # CREAR HOJA Y ESCRIBIR DATOS
        # =====================================================================

        sheet = workbook.add_worksheet('Auditoría Bancaria')

        # Definir columnas
        columns = [
            ('Fecha', 12),
            ('Descripción', 40),
            ('Concepto / Referencia', 35),
            ('Empresa', 30),
            ('Banco / Diario', 25),
            ('Importe', 15),
            ('Saldo Acumulado', 18),
            ('Extracto', 20),
            ('Asiento', 15),
            ('Conciliado', 12),
        ]

        # Establecer anchos de columna y escribir cabeceras
        for col, (header, width) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write(0, col, header, header_format)

        # Fijar primera fila (cabeceras)
        sheet.freeze_panes(1, 0)

        # Escribir datos
        row = 1
        total_amount = 0.0

        for line in lines:
            # Fecha
            if line.date:
                sheet.write_datetime(row, 0, line.date, date_format)
            else:
                sheet.write(row, 0, '', text_format)

            # Descripción
            sheet.write(row, 1, line.name or '', text_format)

            # Concepto / Referencia
            sheet.write(row, 2, line.payment_ref or '', text_format)

            # Empresa
            sheet.write(row, 3, line.partner_id.display_name if line.partner_id else '', text_format)

            # Banco / Diario
            sheet.write(row, 4, line.journal_id.display_name if line.journal_id else '', text_format)

            # Importe (con formato según signo)
            amount = line.amount or 0.0
            if amount < 0:
                sheet.write(row, 5, amount, money_format_negative)
            else:
                sheet.write(row, 5, amount, money_format)
            total_amount += amount

            # Saldo Acumulado
            balance = line.running_balance_audit or 0.0
            if balance < 0:
                sheet.write(row, 6, balance, money_format_negative)
            else:
                sheet.write(row, 6, balance, money_format)

            # Extracto
            sheet.write(row, 7, line.statement_id.display_name if line.statement_id else '', text_format)

            # Asiento
            sheet.write(row, 8, line.move_id.name if line.move_id else '', text_format)

            # Conciliado
            sheet.write(row, 9, 'Sí' if line.is_reconciled else 'No', text_center_format)

            row += 1

        # =====================================================================
        # FILA DE TOTALES
        # =====================================================================

        sheet.write(row, 0, '', total_text_format)
        sheet.write(row, 1, '', total_text_format)
        sheet.write(row, 2, '', total_text_format)
        sheet.write(row, 3, '', total_text_format)
        sheet.write(row, 4, 'TOTAL:', total_text_format)
        sheet.write(row, 5, total_amount, total_format)

        # Último saldo acumulado
        if lines:
            last_balance = lines[-1].running_balance_audit or 0.0
            sheet.write(row, 6, last_balance, total_format)
        else:
            sheet.write(row, 6, 0.0, total_format)

        sheet.write(row, 7, '', total_text_format)
        sheet.write(row, 8, '', total_text_format)
        sheet.write(row, 9, f'{len(lines)} movimientos', total_text_format)

        # =====================================================================
        # HOJA DE RESUMEN POR DIARIO (KPIs)
        # =====================================================================

        summary_sheet = workbook.add_worksheet('Resumen por Diario')

        # Cabeceras de resumen
        summary_columns = [
            ('Diario', 30),
            ('Nº Movimientos', 18),
            ('Total Importe', 18),
            ('Saldo Final', 18),
        ]

        for col, (header, width) in enumerate(summary_columns):
            summary_sheet.set_column(col, col, width)
            summary_sheet.write(0, col, header, header_format)

        summary_sheet.freeze_panes(1, 0)

        # Agrupar por diario
        journals_data = {}
        for line in lines:
            journal_id = line.journal_id.id
            if journal_id not in journals_data:
                journals_data[journal_id] = {
                    'name': line.journal_id.display_name,
                    'count': 0,
                    'total': 0.0,
                    'last_balance': 0.0,
                }
            journals_data[journal_id]['count'] += 1
            journals_data[journal_id]['total'] += line.amount or 0.0
            journals_data[journal_id]['last_balance'] = line.running_balance_audit or 0.0

        # Escribir resumen
        summary_row = 1
        for journal_id, data in journals_data.items():
            summary_sheet.write(summary_row, 0, data['name'], text_format)
            summary_sheet.write(summary_row, 1, data['count'], text_center_format)
            summary_sheet.write(summary_row, 2, data['total'], money_format)
            summary_sheet.write(summary_row, 3, data['last_balance'], money_format)
            summary_row += 1

        # Totales de resumen
        summary_sheet.write(summary_row, 0, 'TOTAL', total_text_format)
        summary_sheet.write(summary_row, 1, sum(d['count'] for d in journals_data.values()), total_format)
        summary_sheet.write(summary_row, 2, sum(d['total'] for d in journals_data.values()), total_format)
        summary_sheet.write(summary_row, 3, sum(d['last_balance'] for d in journals_data.values()), total_format)

        workbook.close()
        output.seek(0)
        return output.read()

    def _generate_filename(self, lines):
        """
        Genera el nombre del archivo basado en el diario y rango de fechas.

        Formato: extracto_auditoria_<journal>_<YYYY-MM-DD>_<YYYY-MM-DD>.xlsx

        Args:
            lines: Recordset de bank.statement.audit

        Returns:
            str: Nombre del archivo
        """
        # Obtener diario(s)
        journals = lines.mapped('journal_id')
        if len(journals) == 1:
            journal_name = journals.name.replace(' ', '_').replace('/', '-')
        else:
            journal_name = 'varios_diarios'

        # Obtener rango de fechas
        dates = lines.mapped('date')
        dates = [d for d in dates if d]  # Filtrar None

        if dates:
            date_from = min(dates).strftime('%Y-%m-%d')
            date_to = max(dates).strftime('%Y-%m-%d')
        else:
            today = date.today().strftime('%Y-%m-%d')
            date_from = today
            date_to = today

        # Limpiar caracteres especiales del nombre
        import re
        journal_name = re.sub(r'[^\w\-]', '_', journal_name)

        return f'extracto_auditoria_{journal_name}_{date_from}_{date_to}.xlsx'

    def action_back(self):
        """Volver a la configuración."""
        self.write({'state': 'config'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
