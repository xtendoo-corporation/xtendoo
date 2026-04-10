# -*- coding: utf-8 -*-
# Copyright 2024 Xtendoo - https://xtendoo.es
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import re
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class InformeContabilidadWizard(models.TransientModel):
    """
    Wizard para generar el informe de diario de facturas de clientes en formato Excel (XLSX).

    Columnas del informe:
    - Serie de la factura
    - Número de la factura
    - Fecha de la factura
    - Fecha de operación
    - Referencia del cliente
    - CIF del cliente
    - Nombre del cliente
    - Comentario
    - Contrapartida (vacío)
    - Cod. Transacción (vacío)
    - ClaveOperaciónFact (vacío)
    - Importe Factura
    - Base Imponible1
    - %IVA1
    - Cuota IVA1
    - %RecEq1
    - Cuota Rec1
    - Código retención (vacío)
    - Base Ret (vacío)
    - Por retención (vacío)
    - Cuota retención (vacío)
    """

    _name = 'xtendoo.informe.contabilidad.wizard'
    _description = 'Asistente - Informe Diario de Facturas de Clientes'

    # =========================================================================
    # CAMPOS DEL WIZARD
    # =========================================================================

    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: date(date.today().year, 1, 1),
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=fields.Date.today,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario',
        domain="[('type', '=', 'sale')]",
        help='Filtrar por diario de ventas. Dejar vacío para incluir todos.',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        help='Filtrar por cliente. Dejar vacío para incluir todos.',
    )

    # Campos para el fichero generado
    xlsx_file = fields.Binary(
        string='Archivo Excel',
        readonly=True,
    )
    xlsx_filename = fields.Char(
        string='Nombre del archivo',
        readonly=True,
    )

    # Estado del wizard
    state = fields.Selection([
        ('config', 'Configuración'),
        ('done', 'Completado'),
    ], default='config', string='Estado')

    # =========================================================================
    # VALIDACIONES
    # =========================================================================

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_(
                    'La fecha de inicio no puede ser posterior a la fecha de fin.'
                ))

    # =========================================================================
    # MÉTODOS PRINCIPALES
    # =========================================================================

    def action_generate_report(self):
        """
        Acción principal para generar el informe Excel.

        Returns:
            dict: Acción para descargar el archivo generado.
        """
        self.ensure_one()

        if not xlsxwriter:
            raise UserError(_(
                'La librería xlsxwriter no está instalada. '
                'Por favor, instálela con: pip install xlsxwriter'
            ))

        # Construir dominio de búsqueda
        domain = self._build_domain()

        # Buscar facturas
        invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        if not invoices:
            raise UserError(_(
                'No se han encontrado facturas con los criterios indicados.\n'
                'Por favor, revise el rango de fechas y los filtros aplicados.'
            ))

        # Generar archivo Excel
        xlsx_data = self._generate_xlsx(invoices)

        # Generar nombre del archivo
        filename = self._generate_filename()

        # Guardar en el wizard y cambiar estado
        self.write({
            'xlsx_file': base64.b64encode(xlsx_data),
            'xlsx_filename': filename,
            'state': 'done',
        })

        # Retornar acción de descarga directa
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=%s&id=%d&field=xlsx_file&filename=%s&download=true' % (
                self._name, self.id, filename
            ),
            'target': 'self',
        }

    def action_back(self):
        """Volver al estado de configuración."""
        self.write({'state': 'config'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # =========================================================================
    # MÉTODOS PRIVADOS
    # =========================================================================

    def _build_domain(self):
        """
        Construye el dominio de búsqueda para las facturas de clientes.

        Returns:
            list: Dominio Odoo para filtrar account.move.
        """
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('company_id', 'in', self.env.companies.ids),
        ]

        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        if self.journal_id:
            domain.append(('journal_id', '=', self.journal_id.id))
        if self.partner_id:
            domain.append(('partner_id', 'child_of', self.partner_id.id))

        return domain

    def _generate_xlsx(self, invoices):
        """
        Genera el contenido del archivo Excel con el diario de facturas.

        Args:
            invoices: Recordset de account.move (facturas de clientes).

        Returns:
            bytes: Contenido binario del archivo XLSX.
        """
        # Deshabilitar prefetch para evitar conflictos con campos de módulos externos
        # que puedan no estar sincronizados en la BD
        invoices = invoices.with_context(prefetch_fields=False)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # =====================================================================
        # FORMATOS
        # =====================================================================

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'font_color': '#1F4E79',
            'align': 'center',
            'valign': 'vcenter',
        })

        subtitle_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font_color': '#2E74B5',
            'align': 'center',
            'valign': 'vcenter',
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2E74B5',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
        })

        money_format_alt = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#F2F2F2',
        })

        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
        })

        percent_format_alt = workbook.add_format({
            'num_format': '0.00%',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#F2F2F2',
        })

        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })

        text_format_alt = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#F2F2F2',
        })

        text_center_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        text_center_format_alt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F2F2F2',
        })

        date_format_alt = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F2F2F2',
        })

        total_label_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': 'white',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
        })

        total_money_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': 'white',
            'border': 1,
            'num_format': '#,##0.00',
            'align': 'right',
            'valign': 'vcenter',
        })

        total_empty_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': 'white',
            'border': 1,
        })

        # =====================================================================
        # CREAR HOJA PRINCIPAL
        # =====================================================================

        sheet = workbook.add_worksheet('Diario de Facturas')
        sheet.set_zoom(90)

        # Definir columnas: (encabezado, ancho)
        columns = [
            # Columnas 1-21: Básicas y primer IVA
            ('Serie', 10),
            ('Número de Factura', 18),
            ('Fecha Factura', 12),
            ('Fecha Operación', 12),
            ('Referencia Cliente', 20),
            ('CIF Cliente', 14),
            ('Nombre Cliente', 30),
            ('Comentario', 25),
            ('Contrapartida', 12),
            ('Cód. Transacción', 12),
            ('ClaveOperaciónFact', 15),
            ('Importe Factura', 14),
            ('Base Imponible1', 14),
            ('%IVA1', 8),
            ('Cuota IVA1', 12),
            ('%RecEq1', 8),
            ('Cuota Rec1', 12),
            ('Código Retención', 12),
            ('Base Ret', 10),
            ('Por Retención', 11),
            ('Cuota Retención', 12),
            # Columnas 22-26: Segundo IVA
            ('Base Imponible2', 14),
            ('%IVA2', 8),
            ('Cuota IVA2', 12),
            ('%RecEq2', 8),
            ('Cuota Rec2', 12),
            # Columnas 27-31: Tercer IVA
            ('Base Imponible3', 14),
            ('%IVA3', 8),
            ('Cuota IVA3', 12),
            ('%RecEq3', 8),
            ('Cuota Rec3', 12),
            # Columnas 32-50: Campos rectificativas (vacíos)
            ('TipoRectificativa', 14),
            ('ClaseAbonoRectificativa', 18),
            ('EjercicioFacturaRectificada', 20),
            ('SerieFacturaRectificada', 18),
            ('NumeroFacturaRectificada', 20),
            ('FechaFacturaRectificada', 18),
            ('BaseImponibleRectificada', 18),
            ('CuotaIvaRectificada', 16),
            ('RecargoEquRectificada', 16),
            ('NumeroFacturaInicial', 16),
            ('NumeroFacturaFinal', 16),
            ('IdFacturaExterno', 16),
            # Columnas 51-53: Localización
            ('CódigoPostal', 12),
            ('Cod. Provincia', 12),
            ('Provincia', 20),
            # Columnas 54-56: Organización (vacíos)
            ('CodigoCanal', 12),
            ('CodigoDelegación', 14),
            ('CodDepartamento', 14),
            # Columnas 57-61: Cuarto IVA
            ('Base Imponible4', 14),
            ('%IVA4', 8),
            ('Cuota IVA4', 12),
            ('%RecEq4', 8),
            ('Cuota Rec4', 12),
        ]

        num_cols = len(columns)

        # ---- Cabecera del informe ----
        sheet.set_row(0, 25)
        sheet.merge_range(0, 0, 0, num_cols - 1,
                          'DIARIO DE FACTURAS DE CLIENTES', title_format)

        # Subtítulo con rango de fechas
        date_from_str = self.date_from.strftime('%d/%m/%Y') if self.date_from else ''
        date_to_str = self.date_to.strftime('%d/%m/%Y') if self.date_to else ''
        subtitle_text = 'Período: %s — %s' % (date_from_str, date_to_str)
        if self.journal_id:
            subtitle_text += '   |   Diario: %s' % self.journal_id.name
        if self.partner_id:
            subtitle_text += '   |   Cliente: %s' % self.partner_id.display_name

        sheet.set_row(1, 18)
        sheet.merge_range(1, 0, 1, num_cols - 1, subtitle_text, subtitle_format)

        # Empresa
        company = self.env.company
        sheet.set_row(2, 15)
        sheet.merge_range(2, 0, 2, num_cols - 1,
                          company.name or '', subtitle_format)

        # Fila en blanco
        sheet.set_row(3, 5)

        # ---- Cabeceras de columnas ----
        header_row = 4
        sheet.set_row(header_row, 20)
        for col, (header, width) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write(header_row, col, header, header_format)

        # Fijar filas superiores (hasta la de cabeceras inclusive)
        sheet.freeze_panes(header_row + 1, 0)

        # ---- Escribir datos ----
        data_row = header_row + 1
        total_importe = 0.0
        total_base1 = 0.0
        total_cuota_iva1 = 0.0
        total_cuota_rec1 = 0.0

        for idx, invoice in enumerate(invoices):
            # Alternar color de filas para mejor legibilidad
            is_alt = (idx % 2 == 1)
            t_fmt = text_format_alt if is_alt else text_format
            tc_fmt = text_center_format_alt if is_alt else text_center_format
            d_fmt = date_format_alt if is_alt else date_format
            m_fmt = money_format_alt if is_alt else money_format
            p_fmt = percent_format_alt if is_alt else percent_format

            col = 0

            # 1. Serie: código del diario contable
            try:
                serie = invoice.journal_id.code or ''
            except Exception:
                serie = ''
            sheet.write(data_row, col, serie, tc_fmt)
            col += 1

            # 2. Número de factura
            try:
                num_factura = invoice.name or ''
            except Exception:
                num_factura = ''
            sheet.write(data_row, col, num_factura, t_fmt)
            col += 1

            # 3. Fecha Factura
            if invoice.invoice_date:
                sheet.write_datetime(data_row, col, invoice.invoice_date, d_fmt)
            else:
                sheet.write(data_row, col, '', tc_fmt)
            col += 1

            # 4. Fecha Operación (igual que fecha factura)
            if invoice.invoice_date:
                sheet.write_datetime(data_row, col, invoice.invoice_date, d_fmt)
            else:
                sheet.write(data_row, col, '', tc_fmt)
            col += 1

            # 5. Referencia del cliente
            sheet.write(data_row, col, invoice.ref or '', t_fmt)
            col += 1

            # 6. CIF del cliente
            cif = invoice.partner_id.vat or ''
            sheet.write(data_row, col, cif, t_fmt)
            col += 1

            # 7. Nombre del cliente
            nombre_cliente = invoice.partner_id.name or ''
            sheet.write(data_row, col, nombre_cliente, t_fmt)
            col += 1

            # 8. Comentario: "N/ FRA Nº" + número de factura
            comentario = 'N/ FRA Nº %s' % (invoice.name or '')
            sheet.write(data_row, col, comentario, t_fmt)
            col += 1

            # 9. Contrapartida (vacío)
            sheet.write(data_row, col, '', t_fmt)
            col += 1

            # 10. Cód. Transacción (vacío)
            sheet.write(data_row, col, '', t_fmt)
            col += 1

            # 11. ClaveOperaciónFact (vacío)
            sheet.write(data_row, col, '', t_fmt)
            col += 1

            # 12. Importe Factura (total)
            importe_factura = invoice.amount_total or 0.0
            sheet.write(data_row, col, importe_factura, m_fmt)
            total_importe += importe_factura
            col += 1

            # Calcular desglose de IVA y recargo de equivalencia
            # Agrupar impuestos por tipo y base imponible
            tax_details = {}

            # Recorrer las líneas de la factura para agrupar por impuesto
            for line in invoice.invoice_line_ids:
                base_line = line.price_subtotal
                for tax in line.tax_ids:
                    tax_name = tax.name or ''
                    tax_amount = tax.amount

                    # Verificar si es recargo de equivalencia
                    is_recargo = (
                        'RE' in tax_name.upper() or
                        'RECARGO' in tax_name.upper() or
                        'R.E.' in tax_name.upper()
                    )

                    if not is_recargo:
                        # Es un IVA normal
                        if tax.id not in tax_details:
                            tax_details[tax.id] = {
                                'tax': tax,
                                'base': 0.0,
                                'rate': tax_amount,
                                'amount': 0.0,
                                'rec_rate': 0.0,
                                'rec_amount': 0.0
                            }
                        tax_details[tax.id]['base'] += base_line

            # Calcular las cuotas de IVA desde las líneas contables
            tax_lines = invoice.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_repartition_line_id.use_in_tax_closing
            )

            for tax_line in tax_lines:
                tax_id = tax_line.tax_line_id.id
                tax_name = tax_line.tax_line_id.name or ''

                is_recargo = (
                    'RE' in tax_name.upper() or
                    'RECARGO' in tax_name.upper() or
                    'R.E.' in tax_name.upper()
                )

                if is_recargo:
                    # Buscar el IVA principal asociado (asumimos mismo % o siguiente en lista)
                    # Por ahora asociamos al primer IVA disponible
                    for tid, tdetail in tax_details.items():
                        if tdetail['rec_amount'] == 0.0:
                            tdetail['rec_rate'] = tax_line.tax_line_id.amount
                            tdetail['rec_amount'] = abs(tax_line.balance)
                            break
                else:
                    if tax_id in tax_details:
                        tax_details[tax_id]['amount'] = abs(tax_line.balance)

            # Ordenar por porcentaje de IVA (mayor a menor)
            sorted_taxes = sorted(
                tax_details.values(),
                key=lambda x: x['rate'],
                reverse=True
            )

            # Preparar datos para hasta 4 tipos de IVA
            iva_data = []
            for idx in range(4):
                if idx < len(sorted_taxes):
                    tax_info = sorted_taxes[idx]
                    iva_data.append({
                        'base': tax_info['base'],
                        'porc': tax_info['rate'] / 100.0,  # Convertir a decimal
                        'cuota': tax_info['amount'],
                        'porc_rec': tax_info['rec_rate'] / 100.0,
                        'cuota_rec': tax_info['rec_amount']
                    })
                else:
                    iva_data.append({
                        'base': 0.0,
                        'porc': 0.0,
                        'cuota': 0.0,
                        'porc_rec': 0.0,
                        'cuota_rec': 0.0
                    })

            # 13-17. IVA1 y RecEq1
            sheet.write(data_row, col, iva_data[0]['base'], m_fmt)
            total_base1 += iva_data[0]['base']
            col += 1
            sheet.write(data_row, col, iva_data[0]['porc'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[0]['cuota'], m_fmt)
            total_cuota_iva1 += iva_data[0]['cuota']
            col += 1
            sheet.write(data_row, col, iva_data[0]['porc_rec'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[0]['cuota_rec'], m_fmt)
            total_cuota_rec1 += iva_data[0]['cuota_rec']
            col += 1

            # 18-21. Retención (vacíos)
            sheet.write(data_row, col, '', t_fmt)  # Código Retención
            col += 1
            sheet.write(data_row, col, '', m_fmt)  # Base Ret
            col += 1
            sheet.write(data_row, col, '', p_fmt)  # Por Retención
            col += 1
            sheet.write(data_row, col, '', m_fmt)  # Cuota Retención
            col += 1

            # 22-26. IVA2 y RecEq2
            sheet.write(data_row, col, iva_data[1]['base'], m_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[1]['porc'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[1]['cuota'], m_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[1]['porc_rec'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[1]['cuota_rec'], m_fmt)
            col += 1

            # 27-31. IVA3 y RecEq3
            sheet.write(data_row, col, iva_data[2]['base'], m_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[2]['porc'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[2]['cuota'], m_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[2]['porc_rec'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[2]['cuota_rec'], m_fmt)
            col += 1

            # 32-43. Campos rectificativas (vacíos)
            for _ in range(12):  # 12 campos de rectificativas
                sheet.write(data_row, col, '', t_fmt)
                col += 1

            # 44-46. Localización
            # Código Postal
            zip_code = invoice.partner_id.zip or ''
            sheet.write(data_row, col, zip_code, t_fmt)
            col += 1

            # Cód. Provincia (vacío)
            sheet.write(data_row, col, '', t_fmt)
            col += 1

            # Provincia
            provincia = invoice.partner_id.state_id.name if invoice.partner_id.state_id else ''
            sheet.write(data_row, col, provincia, t_fmt)
            col += 1

            # 47-49. Organización (vacíos)
            sheet.write(data_row, col, '', t_fmt)  # CodigoCanal
            col += 1
            sheet.write(data_row, col, '', t_fmt)  # CodigoDelegación
            col += 1
            sheet.write(data_row, col, '', t_fmt)  # CodDepartamento
            col += 1

            # 50-54. IVA4 y RecEq4
            sheet.write(data_row, col, iva_data[3]['base'], m_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[3]['porc'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[3]['cuota'], m_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[3]['porc_rec'], p_fmt)
            col += 1
            sheet.write(data_row, col, iva_data[3]['cuota_rec'], m_fmt)
            col += 1

            data_row += 1

        # ---- Fila de totales ----
        sheet.set_row(data_row, 18)
        num_cols_total = len(columns)

        # Escribir totales o vacíos según la columna
        for i in range(num_cols_total):
            if i == 7:  # Columna Comentario
                sheet.write(data_row, i, 'TOTAL (%d facturas)' % len(invoices), total_label_format)
            elif i == 11:  # Importe Factura
                sheet.write(data_row, i, total_importe, total_money_format)
            elif i == 12:  # Base Imponible1
                sheet.write(data_row, i, total_base1, total_money_format)
            elif i == 14:  # Cuota IVA1
                sheet.write(data_row, i, total_cuota_iva1, total_money_format)
            elif i == 16:  # Cuota Rec1
                sheet.write(data_row, i, total_cuota_rec1, total_money_format)
            else:
                sheet.write(data_row, i, '', total_empty_format)


        # =====================================================================
        # HOJA DE RESUMEN POR SERIE / DIARIO
        # =====================================================================

        summary_sheet = workbook.add_worksheet('Resumen por Serie')

        summary_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2E74B5',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        summary_money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right',
        })
        summary_text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
        })
        summary_center_format = workbook.add_format({
            'border': 1,
            'align': 'center',
        })
        summary_total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': 'white',
            'border': 1,
            'num_format': '#,##0.00',
            'align': 'right',
        })
        summary_total_text_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E79',
            'font_color': 'white',
            'border': 1,
            'align': 'left',
        })

        summary_sheet.set_row(0, 20)
        summary_sheet.merge_range(0, 0, 0, 4,
                                  'RESUMEN POR SERIE / DIARIO', title_format)
        summary_sheet.set_row(1, 15)
        summary_sheet.merge_range(1, 0, 1, 4, subtitle_text, subtitle_format)

        summary_cols = [
            ('Serie', 12),
            ('Diario', 35),
            ('Nº Facturas', 14),
            ('Base Imponible', 18),
            ('Cuota IVA', 18),
            ('Total Factura', 18),
        ]

        header_row_s = 3
        for col, (header, width) in enumerate(summary_cols):
            summary_sheet.set_column(col, col, width)
            summary_sheet.write(header_row_s, col, header, summary_header_format)

        summary_sheet.freeze_panes(header_row_s + 1, 0)

        # Agrupar por diario
        journals_data = {}
        for invoice in invoices:
            jid = invoice.journal_id.id
            if jid not in journals_data:
                journals_data[jid] = {
                    'code': invoice.journal_id.code or '',
                    'name': invoice.journal_id.name or '',
                    'count': 0,
                    'base': 0.0,
                    'iva': 0.0,
                    'total': 0.0,
                }
            journals_data[jid]['count'] += 1

            # Calcular base del primer IVA
            tax_lines = invoice.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_repartition_line_id.use_in_tax_closing
            )
            iva_taxes = tax_lines.filtered(
                lambda l: l.tax_line_id and
                'RE' not in (l.tax_line_id.name or '').upper() and
                'RECARGO' not in (l.tax_line_id.name or '').upper() and
                'R.E.' not in (l.tax_line_id.name or '').upper()
            ).sorted(key=lambda l: l.tax_line_id.amount, reverse=True)

            if iva_taxes:
                first_iva = iva_taxes[0]
                invoice_lines_with_tax = invoice.invoice_line_ids.filtered(
                    lambda l: first_iva.tax_line_id in l.tax_ids
                )
                base = sum(invoice_lines_with_tax.mapped('price_subtotal'))
                cuota = abs(first_iva.balance)
            else:
                base = 0.0
                cuota = 0.0

            journals_data[jid]['base'] += base
            journals_data[jid]['iva'] += cuota
            journals_data[jid]['total'] += invoice.amount_total or 0.0

        s_row = header_row_s + 1
        for jid, data in journals_data.items():
            summary_sheet.write(s_row, 0, data['code'], summary_center_format)
            summary_sheet.write(s_row, 1, data['name'], summary_text_format)
            summary_sheet.write(s_row, 2, data['count'], summary_center_format)
            summary_sheet.write(s_row, 3, data['base'], summary_money_format)
            summary_sheet.write(s_row, 4, data['iva'], summary_money_format)
            summary_sheet.write(s_row, 5, data['total'], summary_money_format)
            s_row += 1

        # Totales resumen
        summary_sheet.write(s_row, 0, '', summary_total_text_format)
        summary_sheet.write(s_row, 1, 'TOTAL', summary_total_text_format)
        summary_sheet.write(s_row, 2,
                            sum(d['count'] for d in journals_data.values()),
                            summary_total_format)
        summary_sheet.write(s_row, 3, total_base1, summary_total_format)
        summary_sheet.write(s_row, 4, total_cuota_iva1, summary_total_format)
        summary_sheet.write(s_row, 5, total_importe, summary_total_format)

        workbook.close()
        output.seek(0)
        return output.read()

    def _generate_filename(self):
        """
        Genera el nombre del archivo basado en el rango de fechas.

        Returns:
            str: Nombre del archivo XLSX.
        """
        date_from_str = self.date_from.strftime('%Y-%m-%d') if self.date_from else 'inicio'
        date_to_str = self.date_to.strftime('%Y-%m-%d') if self.date_to else 'fin'

        if self.journal_id:
            journal_part = '_' + re.sub(r'[^\w]', '_', self.journal_id.code or 'diario')
        else:
            journal_part = ''

        return 'diario_facturas%s_%s_%s.xlsx' % (journal_part, date_from_str, date_to_str)

