from odoo import api, fields, models


class CashboxCalculatorMixin(models.AbstractModel):
    """
    Mixin para añadir calculadora de efectivo a cualquier wizard.
    Proporciona campos para contar billetes y monedas, y calcula el total automáticamente.
    """
    _name = 'cashbox.calculator.mixin'
    _description = 'Calculadora de efectivo (billetes y monedas)'

    # Toggle para usar calculadora
    use_cashbox = fields.Boolean(
        string='Usar calculadora de efectivo',
        default=False,
        help='Activar para contar billetes y monedas manualmente'
    )

    # Campos para billetes
    qty_500 = fields.Integer(string='500 €', default=0)
    qty_200 = fields.Integer(string='200 €', default=0)
    qty_100 = fields.Integer(string='100 €', default=0)
    qty_50 = fields.Integer(string='50 €', default=0)
    qty_20 = fields.Integer(string='20 €', default=0)
    qty_10 = fields.Integer(string='10 €', default=0)
    qty_5 = fields.Integer(string='5 €', default=0)

    # Campos para monedas
    qty_2 = fields.Integer(string='2 €', default=0)
    qty_1 = fields.Integer(string='1 €', default=0)
    qty_050 = fields.Integer(string='0,50 €', default=0)
    qty_020 = fields.Integer(string='0,20 €', default=0)
    qty_010 = fields.Integer(string='0,10 €', default=0)
    qty_005 = fields.Integer(string='0,05 €', default=0)
    qty_002 = fields.Integer(string='0,02 €', default=0)
    qty_001 = fields.Integer(string='0,01 €', default=0)

    def _calculate_cashbox_total(self):
        """
        Calcula el total de efectivo basado en las cantidades de billetes y monedas.

        Returns:
            float: Total calculado en euros
        """
        self.ensure_one()
        return (
            self.qty_500 * 500 +
            self.qty_200 * 200 +
            self.qty_100 * 100 +
            self.qty_50 * 50 +
            self.qty_20 * 20 +
            self.qty_10 * 10 +
            self.qty_5 * 5 +
            self.qty_2 * 2 +
            self.qty_1 * 1 +
            self.qty_050 * 0.50 +
            self.qty_020 * 0.20 +
            self.qty_010 * 0.10 +
            self.qty_005 * 0.05 +
            self.qty_002 * 0.02 +
            self.qty_001 * 0.01
        )

