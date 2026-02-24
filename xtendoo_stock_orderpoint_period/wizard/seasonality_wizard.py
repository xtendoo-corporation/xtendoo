# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import calendar
from collections import defaultdict
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


# ────────────────────────────────────────────────────────────────────────
#  Línea de preview (O2M del wizard)
# ────────────────────────────────────────────────────────────────────────
class SeasonalityWizardLine(models.TransientModel):
    _name = "stock.orderpoint.seasonality.wizard.line"
    _description = "Línea de preview para el wizard de estacionalidad"

    wizard_id = fields.Many2one(
        "stock.orderpoint.seasonality.wizard",
        string="Wizard",
        ondelete="cascade",
    )
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    month = fields.Integer(string="Mes", readonly=True)
    month_name = fields.Char(string="Mes (nombre)", compute="_compute_month_name")
    demand_qty = fields.Float(
        string="Demanda histórica", digits="Product Unit", readonly=True
    )
    factor_pct = fields.Float(string="Factor (%)", readonly=True)
    suggested_min_qty = fields.Float(
        string="Min qty sugerida",
        digits="Product Unit",
        readonly=True,
    )
    date_start = fields.Date(string="Fecha inicio", readonly=True)
    date_end = fields.Date(string="Fecha fin", readonly=True)
    action_flag = fields.Selection(
        [("create", "Crear"), ("update", "Actualizar")],
        string="Acción",
        readonly=True,
    )
    existing_orderpoint_id = fields.Many2one(
        "stock.warehouse.orderpoint",
        string="Orderpoint existente",
        readonly=True,
    )

    @api.depends("month")
    def _compute_month_name(self):
        month_names = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre",
        }
        for rec in self:
            rec.month_name = month_names.get(rec.month, "")


# ────────────────────────────────────────────────────────────────────────
#  Wizard principal
# ────────────────────────────────────────────────────────────────────────
MONTH_SELECTION = [
    ("1", "Enero"),
    ("2", "Febrero"),
    ("3", "Marzo"),
    ("4", "Abril"),
    ("5", "Mayo"),
    ("6", "Junio"),
    ("7", "Julio"),
    ("8", "Agosto"),
    ("9", "Septiembre"),
    ("10", "Octubre"),
    ("11", "Noviembre"),
    ("12", "Diciembre"),
]


class SeasonalityWizard(models.TransientModel):
    _name = "stock.orderpoint.seasonality.wizard"
    _description = "Wizard: Generar orderpoints estacionales por histórico"

    # ── Parámetros ──────────────────────────────────────────────────────
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Ubicación",
        help="Dejar vacío para usar la ubicación de stock del almacén.",
        domain="[('warehouse_id', '=', warehouse_id), ('usage', '=', 'internal')]",
    )
    year_reference = fields.Integer(
        string="Año de referencia",
        required=True,
        default=lambda self: fields.Date.context_today(self).year - 1,
        help="Año del que se toma la demanda histórica (p.ej. 2025).",
    )
    # Selección múltiple simulada con Many2many virtual no es posible en
    # TransientModel fácilmente.  Usamos un Char con selección manual o un
    # flag "all_year".
    month_ids = fields.Many2many(
        "stock.orderpoint.seasonality.wizard.month",
        relation="seasonality_wizard_month_rel",
        string="Meses",
        help="Selecciona los meses objetivo. Vacío = todos (año completo).",
    )
    all_year = fields.Boolean(
        string="Año completo",
        default=True,
        help="Si está marcado, se generarán orderpoints para los 12 meses.",
    )
    product_ids = fields.Many2many(
        "product.product",
        relation="seasonality_wizard_product_rel",
        string="Productos",
        domain="[('is_storable', '=', True)]",
        help="Deja vacío para calcular todos los almacenables con movimientos.",
    )
    categ_id = fields.Many2one(
        "product.category",
        string="Categoría de producto",
        help="Filtra productos por categoría (combinable con productos).",
    )
    simulation = fields.Boolean(
        string="Simulación",
        default=True,
        help="Si está activo solo muestra preview; no crea ni actualiza.",
    )
    factor_pct = fields.Float(
        string="Factor de demanda (%)",
        help="Se toma por defecto del ajuste de la compañía. "
        "Editable aquí para sobreescribir.",
    )
    target_year = fields.Integer(
        string="Año objetivo",
        required=True,
        default=lambda self: fields.Date.context_today(self).year,
        help="Año en el que se crearán los intervalos de orderpoints.",
    )

    # ── Líneas de preview ───────────────────────────────────────────────
    line_ids = fields.One2many(
        "stock.orderpoint.seasonality.wizard.line",
        "wizard_id",
        string="Preview",
    )

    # ── Defaults ────────────────────────────────────────────────────────
    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.factor_pct = self.company_id.demand_factor_pct

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "factor_pct" in fields_list and "factor_pct" not in res:
            res["factor_pct"] = self.env.company.demand_factor_pct
        return res

    # ── Helpers ─────────────────────────────────────────────────────────
    def _get_months(self):
        """Devuelve lista de enteros [1..12] según selección."""
        if self.all_year or not self.month_ids:
            return list(range(1, 13))
        return [int(m.month) for m in self.month_ids]

    def _get_products(self):
        """Devuelve recordset de productos a analizar."""
        domain = [("is_storable", "=", True)]
        if self.product_ids:
            domain.append(("id", "in", self.product_ids.ids))
        if self.categ_id:
            domain.append(("categ_id", "child_of", self.categ_id.id))
        return self.env["product.product"].search(domain)

    def _get_location(self):
        return self.location_id or self.warehouse_id.lot_stock_id

    def _month_date_range(self, year, month):
        """Devuelve (date_start, date_end) para un mes dado."""
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    # ── Cálculo de demanda histórica ────────────────────────────────────
    def _compute_demand(self, products, months):
        """Calcula demanda histórica agrupada por producto y mes.

        Estrategia:
        - stock.move en estado 'done'
        - Salidas desde la ubicación del almacén (location_id hijo del
          almacén), es decir, movimientos que SALEN del stock.
        - Se restan devoluciones (movimientos de entrada al mismo stock
          con origin que contenga 'Return' o usando picking_type_code == 'incoming'
          y origin referenciando el picking original).

        Para simplificar y optimizar, usamos read_group.

        Retorna: dict  {(product_id, month): qty_in_product_uom}

        VERIFY IN SOURCE – Usamos location_id (origen) dentro del almacén
        para detectar salidas.  Si tu flujo usa location_dest_id de clientes
        como filtro alternativo, ajusta el dominio.
        """
        result = defaultdict(float)
        if not products or not months:
            return result

        location = self._get_location()
        # Ubicaciones hijas de la ubicación de stock
        child_locations = self.env["stock.location"].search(
            [("id", "child_of", location.id)]
        )

        for month in months:
            start, end = self._month_date_range(self.year_reference, month)

            # ── Salidas (consumo / ventas) ──────────────────────────────
            out_domain = [
                ("state", "=", "done"),
                ("company_id", "=", self.company_id.id),
                ("date", ">=", fields.Datetime.to_datetime(start)),
                (
                    "date",
                    "<=",
                    fields.Datetime.to_datetime(end).replace(
                        hour=23, minute=59, second=59
                    ),
                ),
                ("product_id", "in", products.ids),
                ("location_id", "in", child_locations.ids),
                # Excluir movimientos internos (destino también interno)
                ("location_dest_id", "not in", child_locations.ids),
            ]
            out_groups = self.env["stock.move"]._read_group(
                out_domain,
                ["product_id", "product_uom"],
                ["product_qty:sum"],
            )
            for product, uom, qty_sum in out_groups:
                # Convertir a UoM del producto si difiere
                if uom != product.uom_id:
                    qty_sum = uom._compute_quantity(
                        qty_sum, product.uom_id, rounding_method="HALF-UP"
                    )
                result[(product.id, month)] += qty_sum

            # ── Devoluciones (entradas de retorno) ──────────────────────
            # Las devoluciones son movimientos entrantes al stock desde
            # ubicaciones de cliente/proveedor con picking_type_code == 'incoming'.
            # Restamos lo devuelto.
            in_domain = [
                ("state", "=", "done"),
                ("company_id", "=", self.company_id.id),
                ("date", ">=", fields.Datetime.to_datetime(start)),
                (
                    "date",
                    "<=",
                    fields.Datetime.to_datetime(end).replace(
                        hour=23, minute=59, second=59
                    ),
                ),
                ("product_id", "in", products.ids),
                ("location_dest_id", "in", child_locations.ids),
                ("location_id", "not in", child_locations.ids),
                # Solo devoluciones: origin_returned_move_id presente
                ("origin_returned_move_id", "!=", False),
            ]
            in_groups = self.env["stock.move"]._read_group(
                in_domain,
                ["product_id", "product_uom"],
                ["product_qty:sum"],
            )
            for product, uom, qty_sum in in_groups:
                if uom != product.uom_id:
                    qty_sum = uom._compute_quantity(
                        qty_sum, product.uom_id, rounding_method="HALF-UP"
                    )
                result[(product.id, month)] -= qty_sum

        # Asegurar que no queden demandas negativas
        return {k: max(v, 0.0) for k, v in result.items()}

    # ── Buscar orderpoint existente (dedupe) ────────────────────────────
    def _find_existing_orderpoint(self, product, ds, de):
        """Busca un orderpoint existente por clave de deduplicación:
        company_id + location_id + product_id + date_start + date_end
        """
        location = self._get_location()
        return self.env["stock.warehouse.orderpoint"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("location_id", "=", location.id),
                ("product_id", "=", product.id),
                ("date_start", "=", ds),
                ("date_end", "=", de),
            ],
            limit=1,
        )

    # ── Acción: Calcular preview ────────────────────────────────────────
    def action_compute_preview(self):
        """Calcula la demanda histórica y genera las líneas de preview."""
        self.ensure_one()
        months = self._get_months()
        products = self._get_products()

        if not products:
            raise UserError(
                _("No se encontraron productos almacenables con los filtros indicados.")
            )

        demand = self._compute_demand(products, months)
        factor = self.factor_pct

        line_vals = []
        for product in products:
            for month in months:
                qty = demand.get((product.id, month), 0.0)
                suggested = qty * (1.0 + factor / 100.0)

                ds, de = self._month_date_range(self.target_year, month)
                existing = self._find_existing_orderpoint(product, ds, de)

                line_vals.append(
                    {
                        "wizard_id": self.id,
                        "product_id": product.id,
                        "month": month,
                        "demand_qty": qty,
                        "factor_pct": factor,
                        "suggested_min_qty": suggested,
                        "date_start": ds,
                        "date_end": de,
                        "action_flag": "update" if existing else "create",
                        "existing_orderpoint_id": existing.id if existing else False,
                    }
                )

        # Limpiar líneas anteriores y crear las nuevas
        self.line_ids.unlink()
        self.env["stock.orderpoint.seasonality.wizard.line"].create(line_vals)

        # Devolver acción para re-abrir el wizard con las líneas
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    # ── Acción: Aplicar (crear/actualizar orderpoints) ──────────────────
    def action_apply(self):
        """Crea o actualiza orderpoints basándose en las líneas de preview.

        Si simulation == True, no hace nada (se queda en preview).
        """
        self.ensure_one()
        if self.simulation:
            raise UserError(
                _(
                    "El modo simulación está activo. Desactívalo para aplicar los cambios."
                )
            )

        if not self.line_ids:
            raise UserError(
                _("No hay líneas de preview. Ejecuta 'Calcular preview' primero.")
            )

        location = self._get_location()
        created = 0
        updated = 0

        for line in self.line_ids:
            vals = {
                "product_min_qty": line.suggested_min_qty,
                "product_max_qty": line.suggested_min_qty,  # max = min por defecto
            }

            if line.action_flag == "update" and line.existing_orderpoint_id:
                line.existing_orderpoint_id.write(vals)
                updated += 1
            else:
                # Crear nuevo orderpoint
                # VERIFY IN SOURCE – El campo 'name' se genera automáticamente
                # por la secuencia 'stock.orderpoint' en create().
                create_vals = {
                    "product_id": line.product_id.id,
                    "warehouse_id": self.warehouse_id.id,
                    "location_id": location.id,
                    "company_id": self.company_id.id,
                    "date_start": line.date_start,
                    "date_end": line.date_end,
                    "trigger": "auto",
                    **vals,
                }
                self.env["stock.warehouse.orderpoint"].create(create_vals)
                created += 1

        # Mensaje informativo
        message = _(
            "Proceso completado: %(created)d reglas creadas, %(updated)d actualizadas.",
            created=created,
            updated=updated,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Orderpoints estacionales"),
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


# ────────────────────────────────────────────────────────────────────────
#  Modelo auxiliar para selección de meses (Many2many del wizard)
# ────────────────────────────────────────────────────────────────────────
class SeasonalityWizardMonth(models.TransientModel):
    _name = "stock.orderpoint.seasonality.wizard.month"
    _description = "Mes seleccionable para el wizard de estacionalidad"
    _rec_name = "name"

    month = fields.Char(string="Mes (número)", required=True)
    name = fields.Char(string="Nombre", required=True)
