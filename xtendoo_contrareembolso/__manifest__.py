{
    'name': 'Payment Acquirer Contrareembolso',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Contrareembolso (Cash on Delivery) payment method to website',
    'description': """
        This module adds a manual payment acquirer called Contrareembolso (Cash on Delivery)
        to the website e-commerce payment methods.
    """,
    'author': 'Guillermo Bárcena López',
    'depends': ['payment', 'website_sale'],
    'data': [
        'views/payment_acquirer_cod.xml',  # Aquí defines la vista para la web
        'views/payment_acquirer_data.xml',  # Datos iniciales del método de pago
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
