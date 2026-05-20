# -*- coding: utf-8 -*-

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    xt_barcode_allow_extra_product = fields.Boolean(
        string="Permitir productos extra",
        default=True,
        help="Permite escanear productos no previstos originalmente en la operación.",
    )
    xt_barcode_restrict_scan_source_location = fields.Selection(
        selection=[
            ("no", "Sin escaneo obligatorio"),
            ("mandatory", "Escaneo obligatorio"),
        ],
        string="Escaneo de origen",
        default="no",
        required=True,
        help="Obliga a confirmar por barcode la ubicación origen antes de escanear productos.",
    )
    xt_barcode_restrict_scan_dest_location = fields.Selection(
        selection=[
            ("no", "Sin escaneo obligatorio"),
            ("optional", "Opcional"),
            ("mandatory", "Obligatorio tras cada producto"),
        ],
        string="Escaneo de destino",
        default="no",
        required=True,
        help="Permite acercar el flujo clásico al comportamiento del barcode Enterprise para destinos.",
    )
    xt_barcode_restrict_scan_tracking_number = fields.Selection(
        selection=[
            ("optional", "Opcional"),
            ("mandatory", "Obligatorio"),
        ],
        string="Escaneo de lote/serie",
        default="optional",
        required=True,
        help="Cuando es obligatorio, la validación clásica exige que cada línea trazada confirme su lote o serie por barcode.",
    )
    xt_barcode_restrict_put_in_pack = fields.Selection(
        selection=[
            ("no", "No"),
            ("optional", "Opcional"),
            ("mandatory", "Obligatorio tras cada producto"),
        ],
        string="Puesta en paquete",
        default="no",
        required=True,
        help="Permite usar un flujo clásico de empaquetado por barcode sin depender de Owl.",
    )
    xt_barcode_validation_full = fields.Boolean(
        string="Permitir validación completa sin escaneo",
        default=True,
        help="Si se desactiva, la validación clásica exige al menos una línea trabajada por barcode.",
    )
    xt_barcode_validation_after_dest_location = fields.Boolean(
        string="Exigir destino antes de validar",
        help="Con destino en modo opcional, fuerza que todas las líneas trabajadas hayan confirmado destino por barcode antes de validar.",
    )
    xt_barcode_validation_all_product_packed = fields.Boolean(
        string="Exigir todo empaquetado antes de validar",
        help="Con empaquetado en modo opcional, fuerza que todas las líneas trabajadas estén puestas en paquete antes de validar.",
    )

