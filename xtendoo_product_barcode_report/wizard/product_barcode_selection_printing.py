# Copyright 2020 Carlos Roca <carlos.roca@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductPrintingQty(models.TransientModel):
    _name = "product.line.print"
    _rec_name = "product_id"
    _description = "Print Product Line"

    product_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
    )
    label_qty = fields.Integer("Quantity of Labels")
    #wizard_id = fields.Many2one("product.print", string="Wizard")


""" class WizProductSelectionPrinting(models.TransientModel):
    _name = "product.print"
    _description = "Wizard to select how many barcodes have to be printed"

    @api.model
    def default_get(self, fields):
        ctx = self.env.context.copy()
        res = super().default_get(fields)
        if ctx.get("active_ids") and ctx.get("active_model") == "product.template":
            product_ids = self.env["product.template"].browse(
                ctx.get("active_ids"))
            res.update({"product_ids": product_ids.ids})
        return res

    product_ids = fields.Many2many("product.template")
    product_print = fields.One2many(
        "product.line.print", "wizard_id", "Products"
    )

    @api.onchange("product_ids")
    def _onchange_product_ids(self):
        product_print_data = []
        line_fields = [
            f for f in self.env["product.line.print"]._fields.keys()]
        product_print_data_tmpl = self.env[
            "product.line.print"
        ].default_get(line_fields)
        for product_id in self.product_ids:
            product = self.env["product.template"].browse(product_id)
            product_print_data = dict(product_print_data_tmpl)
            product_print_data.update(
                    self._prepare_data_from_product(product)
                )
            if product_print_data:
                product_print_data.append((0, 0, product_print_data))
        if self.product_ids:
            self.product_print = product_print_data

    @api.model
    def _prepare_data_from_product(self, product_id):
        if product_id.barcode:
            return {
                "product_id": product_id.id,
                "label_qty": 1,
            }
        else:
            return {}

    def print_labels(self):
        #print_product = self.product_print.filtered(
         #   lambda p: p.label_qty > 0)
        #if print_product:
        return self.env.ref(
                "xtendoo_product_barcode_report.action_label_barcode_report"
            ).report_action(self.product_print_moves) """
