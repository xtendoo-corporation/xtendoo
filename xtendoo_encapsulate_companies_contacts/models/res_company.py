import logging

from odoo import api, models


_logger = logging.getLogger(__name__)

SKIP_COMPANY_ENCAPSULATION_CTX_KEY = 'skip_company_encapsulation'


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        self.sudo()._xt_ensure_company_partners_shared()

        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        prepared_vals_list = [vals.copy() for vals in vals_list]
        no_partner_vals_list = [
            vals
            for vals in prepared_vals_list
            if vals.get('name') and not vals.get('partner_id')
        ]
        if no_partner_vals_list:
            partners = self.env['res.partner'].with_context(
                default_parent_id=False,
                **{SKIP_COMPANY_ENCAPSULATION_CTX_KEY: True},
            ).create([
                {
                    'name': vals['name'],
                    'is_company': True,
                    'image_1920': vals.get('logo'),
                    'email': vals.get('email'),
                    'phone': vals.get('phone'),
                    'website': vals.get('website'),
                    'vat': vals.get('vat'),
                    'country_id': vals.get('country_id'),
                }
                for vals in no_partner_vals_list
            ])
            partners.flush_model()
            for vals, partner in zip(no_partner_vals_list, partners):
                vals['partner_id'] = partner.id

        return super().create(prepared_vals_list)

    @api.model
    def _xt_ensure_company_partners_shared(self):
        companies = self.sudo().with_context(active_test=False).search([])
        company_partners = companies.mapped('partner_id').filtered('company_id')
        if company_partners:
            _logger.warning(
                "[xtendoo_encapsulate_companies_contacts] Corrigiendo %s partners de compañía con company_id indebido.",
                len(company_partners),
            )
            company_partners.with_context(
                **{SKIP_COMPANY_ENCAPSULATION_CTX_KEY: True}
            ).write({'company_id': False})

        if 'internal_transit_location_id' not in self._fields:
            return

        partner_model = self.env['res.partner']
        if 'property_stock_customer' not in partner_model._fields or 'property_stock_supplier' not in partner_model._fields:
            return

        self._xt_reset_shared_stock_routes()
        shared_locations = self._xt_reset_shared_stock_locations()
        inter_company_location = shared_locations.get('stock.stock_location_inter_company')
        if inter_company_location and not inter_company_location.active and len(companies) > 1:
            inter_company_location.sudo().write({'active': True})

        for company in companies.filtered('partner_id'):
            if not company.internal_transit_location_id and hasattr(company, '_create_transit_location'):
                company.sudo()._create_transit_location()
            if company.internal_transit_location_id:
                company.partner_id.sudo().with_company(company).write({
                    'property_stock_customer': company.internal_transit_location_id.id,
                    'property_stock_supplier': company.internal_transit_location_id.id,
                })

        if inter_company_location:
            for company in companies.filtered('partner_id'):
                if hasattr(company, '_set_per_company_inter_company_locations'):
                    company.sudo()._set_per_company_inter_company_locations(inter_company_location)

    @api.model
    def _xt_reset_shared_stock_locations(self):
        location_specs = {
            'stock.stock_location_suppliers': {
                'name': 'Vendors',
                'usage': 'supplier',
                'active': True,
            },
            'stock.stock_location_customers': {
                'name': 'Customers',
                'usage': 'customer',
                'active': True,
            },
            'stock.stock_location_inter_company': {
                'name': 'Inter-company transit',
                'usage': 'transit',
                'active': False,
            },
        }
        shared_locations = {}
        ir_model_data = self.env['ir.model.data'].sudo()
        stock_location_model = self.env['stock.location'].sudo()
        for xmlid, spec in location_specs.items():
            location = self.env.ref(xmlid, raise_if_not_found=False)
            if location and location.company_id:
                _logger.warning(
                    "[xtendoo_encapsulate_companies_contacts] Corrigiendo ubicación compartida %s con company_id=%s.",
                    xmlid,
                    location.company_id.display_name,
                )
                location = stock_location_model.with_context(
                    **{SKIP_COMPANY_ENCAPSULATION_CTX_KEY: True}
                ).create({
                    'name': spec['name'],
                    'usage': spec['usage'],
                    'company_id': False,
                    'active': spec['active'],
                })
                module, name = xmlid.split('.', 1)
                ir_model_data.search([
                    ('module', '=', module),
                    ('name', '=', name),
                    ('model', '=', 'stock.location'),
                ], limit=1).write({'res_id': location.id})
            shared_locations[xmlid] = location

        supplier_location = shared_locations.get('stock.stock_location_suppliers')
        customer_location = shared_locations.get('stock.stock_location_customers')
        if supplier_location:
            self.env['ir.default'].sudo().with_context(
                **{SKIP_COMPANY_ENCAPSULATION_CTX_KEY: True}
            ).set('res.partner', 'property_stock_supplier', supplier_location.id)
        if customer_location:
            self.env['ir.default'].sudo().with_context(
                **{SKIP_COMPANY_ENCAPSULATION_CTX_KEY: True}
            ).set('res.partner', 'property_stock_customer', customer_location.id)
        return shared_locations

    @api.model
    def _xt_reset_shared_stock_routes(self):
        route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
        if route and route.company_id:
            _logger.warning(
                "[xtendoo_encapsulate_companies_contacts] Corrigiendo ruta compartida stock.route_warehouse0_mto con company_id=%s.",
                route.company_id.display_name,
            )
            route.sudo().write({'company_id': False})
        return route




