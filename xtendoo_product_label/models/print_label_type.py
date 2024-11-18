from odoo import fields, models


class PrintLabelTypePy(models.Model):
    _name = "print.label.type"
    _description = 'Label Types'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)

    _sql_constraints = [('print_label_type_code_uniq', 'UNIQUE (code)', 'Code of a print label type must be unique.')]
