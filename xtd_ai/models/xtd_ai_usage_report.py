"""Weekly usage report of the cards (ANALISIS_PERMISOS §6.4, point 8).

Read-only SQL view over the pending actions: per week, company and tool, the
cards accepted, rejected (cancelled by the user), expired and failed. A tool
with more than 95 % of its decided cards accepted is a candidate to go down
from N2 to N1; one with more than 20 % rejected needs a better skill or
preview. Cards cannot be edited before accepting them, so an accepted card is
always «accepted without changes».
"""

from odoo import fields, models, tools
from odoo.tools import SQL

MIN_CARDS = 5  # below this a week says nothing about a tool


class XtdAiUsageReport(models.Model):
    _name = "xtd.ai.usage.report"
    _description = "AI agent weekly card usage"
    _auto = False
    _order = "week desc, total desc"
    _rec_name = "tool_name"

    week = fields.Date(string="Semana", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    tool_name = fields.Char(string="Herramienta", readonly=True)
    total = fields.Integer(string="Tarjetas", readonly=True)
    accepted = fields.Integer(string="Aceptadas", readonly=True)
    rejected = fields.Integer(string="Rechazadas", readonly=True)
    expired = fields.Integer(string="Expiradas", readonly=True)
    failed = fields.Integer(string="Fallidas", readonly=True)
    pending = fields.Integer(string="Pendientes", readonly=True)
    acceptance_rate = fields.Float(
        string="% aceptación", readonly=True, aggregator="avg"
    )
    rejection_rate = fields.Float(string="% rechazo", readonly=True, aggregator="avg")
    candidate_n1 = fields.Boolean(
        string="Candidata a N1",
        readonly=True,
        help="Más del 95 % de las tarjetas decididas aceptadas (mínimo 5).",
    )
    needs_improvement = fields.Boolean(
        string="Mejorar skill o vista previa",
        readonly=True,
        help="Más del 20 % de las tarjetas rechazadas (mínimo 5).",
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                """
            CREATE OR REPLACE VIEW %(table)s AS (
                SELECT
                    row_number() OVER () AS id,
                    s.week, s.company_id, s.tool_name, s.total, s.accepted,
                    s.rejected, s.expired, s.failed, s.pending,
                    CASE WHEN s.decided > 0
                        THEN round(100.0 * s.accepted / s.decided, 1) ELSE 0 END
                        AS acceptance_rate,
                    CASE WHEN s.decided > 0
                        THEN round(100.0 * s.rejected / s.decided, 1) ELSE 0 END
                        AS rejection_rate,
                    (s.decided >= %(min)s
                        AND s.accepted > 0.95 * s.decided) AS candidate_n1,
                    (s.decided >= %(min)s
                        AND s.rejected > 0.20 * s.decided) AS needs_improvement
                FROM (
                    SELECT
                        date_trunc('week', a.create_date)::date AS week,
                        r.company_id AS company_id,
                        a.tool_name AS tool_name,
                        count(*) AS total,
                        count(*) FILTER (WHERE a.state = 'confirmed') AS accepted,
                        count(*) FILTER (WHERE a.state = 'cancelled') AS rejected,
                        count(*) FILTER (WHERE a.state = 'expired') AS expired,
                        count(*) FILTER (WHERE a.state = 'failed') AS failed,
                        count(*) FILTER (WHERE a.state = 'pending') AS pending,
                        count(*) FILTER (
                            WHERE a.state IN ('confirmed', 'cancelled', 'expired')
                        ) AS decided
                    FROM xtd_ai_pending_action a
                    JOIN xtd_ai_run r ON r.id = a.run_id
                    GROUP BY 1, 2, 3
                ) s
            )
            """,
                table=SQL.identifier(self._table),
                min=MIN_CARDS,
            )
        )
