from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    # SOLUCIÓN: Redefinir tax_ids_after_fiscal_position como campo almacenado
    # con inverse para sincronizar automáticamente con tax_ids
    # Usar tabla de relación específica para evitar conflicto con tax_ids
    tax_ids_after_fiscal_position = fields.Many2many(
        'account.tax',
        relation='pos_order_line_tax_ids_after_fp_rel',
        column1='pos_order_line_id',
        column2='tax_id',
        string='Taxes to Apply',
        compute='_compute_tax_ids_after_fiscal_position',
        inverse='_inverse_tax_ids_after_fiscal_position',
        store=True,
        readonly=False,
    )

    @api.depends('order_id', 'order_id.fiscal_position_id', 'tax_ids')
    def _compute_tax_ids_after_fiscal_position(self):
        """
        Computa los impuestos aplicables según la posición fiscal.
        Este método reemplaza al original de Odoo para hacerlo almacenable.
        """
        for line in self:
            if line.tax_ids:
                line.tax_ids_after_fiscal_position = line.order_id.fiscal_position_id.map_tax(line.tax_ids)
            else:
                line.tax_ids_after_fiscal_position = False

    def _inverse_tax_ids_after_fiscal_position(self):
        """
        Método inverso: cuando se modifica tax_ids_after_fiscal_position desde la vista,
        actualiza tax_ids para mantener la coherencia.
        """
        for line in self:
            if line.tax_ids_after_fiscal_position:
                # Sincronizar tax_ids con tax_ids_after_fiscal_position
                # Esto asegura que al guardar, tax_ids tenga los impuestos correctos
                line.tax_ids = line.tax_ids_after_fiscal_position

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para asegurar que tax_ids se establezca correctamente"""
        for vals in vals_list:
            # Si viene product_id pero no tax_ids, obtener impuestos del producto
            if 'product_id' in vals and not vals.get('tax_ids'):
                product = self.env['product.product'].browse(vals['product_id'])
                order = self.env['pos.order'].browse(vals.get('order_id'))

                if order and product:
                    taxes = product.taxes_id
                    # Aplicar posición fiscal si existe
                    if order.fiscal_position_id:
                        taxes = order.fiscal_position_id.map_tax(taxes)
                    # Establecer tax_ids (el campo almacenado)
                    vals['tax_ids'] = [(6, 0, taxes.ids)]

            # Si viene tax_ids_after_fiscal_position pero no tax_ids, sincronizar
            if vals.get('tax_ids_after_fiscal_position') and not vals.get('tax_ids'):
                # Extraer los IDs de tax_ids_after_fiscal_position
                tax_cmd = vals.get('tax_ids_after_fiscal_position')
                if isinstance(tax_cmd, list) and tax_cmd:
                    if tax_cmd[0][0] == 6:  # Comando (6, 0, [ids])
                        vals['tax_ids'] = [(6, 0, tax_cmd[0][2])]

        return super().create(vals_list)

    def write(self, vals):
        """Override write para asegurar que tax_ids se mantenga sincronizado"""
        # Si se está cambiando el producto, recalcular impuestos
        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            for line in self:
                order = line.order_id
                if order and product:
                    taxes = product.taxes_id
                    if order.fiscal_position_id:
                        taxes = order.fiscal_position_id.map_tax(taxes)
                    vals['tax_ids'] = [(6, 0, taxes.ids)]

        # Si se modifica tax_ids_after_fiscal_position, sincronizar con tax_ids
        if 'tax_ids_after_fiscal_position' in vals and 'tax_ids' not in vals:
            tax_cmd = vals.get('tax_ids_after_fiscal_position')
            if isinstance(tax_cmd, list) and tax_cmd:
                if tax_cmd[0][0] == 6:  # Comando (6, 0, [ids])
                    vals['tax_ids'] = [(6, 0, tax_cmd[0][2])]

        return super().write(vals)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Establece el precio unitario y los impuestos cuando se selecciona un producto"""
        if self.product_id and self.order_id.state == 'draft':
            # Establecer precio
            if not self.order_id.pricelist_id:
                self.price_unit = self.product_id.lst_price
            else:
                pricelist = self.order_id.pricelist_id
                price = pricelist._get_product_price(
                    self.product_id,
                    self.qty or 1.0,
                    uom=self.product_id.uom_id
                )
                self.price_unit = price

            # Establecer impuestos en tax_ids (campo almacenado)
            # tax_ids_after_fiscal_position se calculará automáticamente
            taxes = self.product_id.taxes_id.filtered(
                lambda t: t.company_id == self.order_id.company_id
            )
            self.tax_ids = taxes

