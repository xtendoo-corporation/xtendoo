from odoo import api, fields, models


class PosCategory(models.Model):
    _inherit = "pos.category"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
        required=True,
        default=lambda self: self.env.company,
    )
    parent_id = fields.Many2one(
        check_company=True,
    )
    # child_id = fields.One2many(check_company=True)

    @api.model
    def _search(self, domain, *args, **kwargs):
        if "company_id" not in (item[0] for item in domain):
            domain += [("company_id", "in", self.env.user.company_ids.ids)]
        return super()._search(domain, *args, **kwargs)
