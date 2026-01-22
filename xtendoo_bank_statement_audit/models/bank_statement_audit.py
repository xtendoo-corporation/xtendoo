# -*- coding: utf-8 -*-
# Copyright 2024 Xtendoo - https://xtendoo.es
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


class BankStatementAudit(models.Model):
    """
    Modelo basado en SQL VIEW para auditoría de extractos bancarios.

    Utiliza window functions de PostgreSQL para calcular el saldo acumulado
    (running_balance_audit) de forma eficiente, particionado por journal_id
    y ordenado por fecha e id.

    Este modelo NO crea tabla física (_auto = False), solo una vista SQL.
    """
    _name = 'bank.statement.audit'
    _description = 'Bank Statement Audit Line'
    _auto = False
    _order = 'date asc, id asc'

    # =========================================================================
    # CAMPOS DEL MODELO
    # Todos son readonly ya que provienen de una vista SQL
    # =========================================================================

    # Campos básicos de la línea de extracto
    date = fields.Date(
        string='Fecha',
        readonly=True,
    )
    name = fields.Char(
        string='Descripción',
        readonly=True,
    )
    payment_ref = fields.Char(
        string='Concepto / Referencia',
        readonly=True,
        help='Referencia de pago o etiqueta del movimiento bancario',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Empresa',
        readonly=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Banco / Diario',
        readonly=True,
    )
    amount = fields.Monetary(
        string='Importe',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        readonly=True,
    )

    # Campo clave: Saldo acumulado calculado con SQL window function
    running_balance_audit = fields.Monetary(
        string='Saldo Acumulado',
        readonly=True,
        currency_field='currency_id',
        help='Saldo acumulado calculado por diario, ordenado por fecha e ID',
    )

    # Campos opcionales para auditoría
    statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
        string='Extracto',
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Asiento Contable',
        readonly=True,
    )

    # Campo de conciliación
    is_reconciled = fields.Boolean(
        string='Conciliado',
        readonly=True,
    )

    # Campos de compañía para multi-company
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        readonly=True,
    )

    # Referencia a la línea original
    statement_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        string='Línea Original',
        readonly=True,
    )

    # =========================================================================
    # MÉTODO DE INICIALIZACIÓN DE LA VISTA SQL
    # =========================================================================

    def init(self):
        """
        Crea la vista SQL que calcula el running_balance_audit.

        Usa SUM() OVER (PARTITION BY journal_id ORDER BY date, id) para
        calcular el saldo acumulado de forma eficiente sin loops Python.

        La vista incluye todos los campos necesarios para la auditoría
        y permite filtrar por company_id para multi-company.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)

        # SQL VIEW con window function para running balance
        # PARTITION BY journal_id: reinicia el saldo para cada diario
        # ORDER BY date, id: ordena cronológicamente con desempate por id
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    bsl.id AS id,
                    bsl.id AS statement_line_id,
                    am.date AS date,
                    COALESCE(am.name, '') AS name,
                    COALESCE(bsl.payment_ref, '') AS payment_ref,
                    bsl.partner_id AS partner_id,
                    bsl.journal_id AS journal_id,
                    bsl.amount AS amount,
                    COALESCE(
                        aj.currency_id,
                        rc.currency_id
                    ) AS currency_id,
                    -- Running balance con window function
                    -- Particiona por journal_id para calcular saldo por cada banco
                    SUM(bsl.amount) OVER (
                        PARTITION BY bsl.journal_id
                        ORDER BY am.date ASC, bsl.id ASC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS running_balance_audit,
                    bsl.statement_id AS statement_id,
                    bsl.move_id AS move_id,
                    bsl.is_reconciled AS is_reconciled,
                    bsl.company_id AS company_id
                FROM
                    account_bank_statement_line bsl
                    INNER JOIN account_move am ON am.id = bsl.move_id
                    INNER JOIN account_journal aj ON aj.id = bsl.journal_id
                    INNER JOIN res_company rc ON rc.id = bsl.company_id
                WHERE
                    am.state = 'posted'
            )
        """ % self._table)

    # =========================================================================
    # MÉTODOS DE ACCIÓN
    # =========================================================================

    def action_open_move(self):
        """Abre el asiento contable relacionado."""
        self.ensure_one()
        if self.move_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Asiento Contable',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_open_statement_line(self):
        """Abre la línea de extracto original."""
        self.ensure_one()
        if self.statement_line_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Línea de Extracto',
                'res_model': 'account.bank.statement.line',
                'res_id': self.statement_line_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    # =========================================================================
    # MÉTODOS PARA KPIs
    # =========================================================================

    @api.model
    def get_audit_kpis(self, domain=None):
        """
        Calcula KPIs para el dashboard de auditoría.

        Returns:
            dict: Contiene total_amount, move_count, final_balance por journal
        """
        if domain is None:
            domain = []

        # Añadir filtro de compañía
        domain = domain + [('company_id', 'in', self.env.companies.ids)]

        records = self.search(domain, order='date asc, id asc')

        if not records:
            return {
                'total_amount': 0.0,
                'move_count': 0,
                'final_balance': 0.0,
                'by_journal': {},
            }

        # Agrupar por journal
        by_journal = {}
        for record in records:
            journal_id = record.journal_id.id
            journal_name = record.journal_id.display_name

            if journal_id not in by_journal:
                by_journal[journal_id] = {
                    'name': journal_name,
                    'total_amount': 0.0,
                    'move_count': 0,
                    'final_balance': 0.0,
                    'currency_id': record.currency_id.id,
                    'currency_symbol': record.currency_id.symbol,
                }

            by_journal[journal_id]['total_amount'] += record.amount
            by_journal[journal_id]['move_count'] += 1
            by_journal[journal_id]['final_balance'] = record.running_balance_audit

        return {
            'total_amount': sum(j['total_amount'] for j in by_journal.values()),
            'move_count': len(records),
            'final_balance': sum(j['final_balance'] for j in by_journal.values()),
            'by_journal': by_journal,
        }
