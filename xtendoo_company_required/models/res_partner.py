from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains('company_id', 'property_stock_customer', 'property_stock_supplier')
    def _check_stock_location_company_consistency(self):
        """
        Verifica que las ubicaciones de stock sean consistentes con la empresa del partner.
        Si el partner tiene una empresa asignada, las ubicaciones de stock deben pertenecer
        a la misma empresa o no tener empresa asignada.
        """
        for partner in self:
            if partner.company_id:
                # Verificar ubicación de cliente
                if partner.property_stock_customer and \
                   partner.property_stock_customer.company_id and \
                   partner.property_stock_customer.company_id != partner.company_id:
                    raise ValidationError(
                        f"El partner '{partner.name}' pertenece a la empresa '{partner.company_id.name}' "
                        f"pero la 'Ubicación de cliente' pertenece a '{partner.property_stock_customer.company_id.name}'. "
                        f"Para evitar inconsistencias, ambas deben pertenecer a la misma empresa."
                    )

                # Verificar ubicación de proveedor
                if partner.property_stock_supplier and \
                   partner.property_stock_supplier.company_id and \
                   partner.property_stock_supplier.company_id != partner.company_id:
                    raise ValidationError(
                        f"El partner '{partner.name}' pertenece a la empresa '{partner.company_id.name}' "
                        f"pero la 'Ubicación de proveedor' pertenece a '{partner.property_stock_supplier.company_id.name}'. "
                        f"Para evitar inconsistencias, ambas deben pertenecer a la misma empresa."
                    )

    @api.model
    def create(self, vals):
        """
        Al crear un partner con empresa, asigna automáticamente las ubicaciones
        de stock correctas para esa empresa.
        """
        partner = super(ResPartner, self).create(vals)
        if partner.company_id:
            partner._set_default_stock_locations()
        return partner

    def write(self, vals):
        """
        Al cambiar la empresa de un partner, actualiza las ubicaciones de stock
        para que sean consistentes.
        """
        result = super(ResPartner, self).write(vals)
        if 'company_id' in vals:
            for partner in self:
                if partner.company_id:
                    partner._set_default_stock_locations()
        return result

    def _set_default_stock_locations(self):
        """
        Establece las ubicaciones de stock por defecto según la empresa del partner.
        """
        self.ensure_one()
        if not self.company_id:
            return

        # Buscar o crear ubicación de cliente para esta empresa
        customer_location = self.env['stock.location'].search([
            ('usage', '=', 'customer'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not customer_location:
            # Si no existe, usar la ubicación de cliente por defecto sin empresa
            customer_location = self.env['stock.location'].search([
                ('usage', '=', 'customer'),
                ('company_id', '=', False)
            ], limit=1)

        # Buscar o crear ubicación de proveedor para esta empresa
        supplier_location = self.env['stock.location'].search([
            ('usage', '=', 'supplier'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not supplier_location:
            # Si no existe, usar la ubicación de proveedor por defecto sin empresa
            supplier_location = self.env['stock.location'].search([
                ('usage', '=', 'supplier'),
                ('company_id', '=', False)
            ], limit=1)

        # Actualizar las propiedades del partner
        if customer_location:
            self.property_stock_customer = customer_location
        if supplier_location:
            self.property_stock_supplier = supplier_location

    def action_fix_stock_locations(self):
        """
        Acción manual para corregir las ubicaciones de stock de partners seleccionados.
        """
        for partner in self:
            if partner.company_id:
                partner._set_default_stock_locations()

