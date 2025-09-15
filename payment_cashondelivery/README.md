# Contrarreembolso

## Technical details

This module does not integrate with an API and, instead, offers a base for implementing payment
providers with cashondelivery payment flows relying on payment instructions being displayed to the cashondeliveryer.
This is done by immediately marking transactions as 'pending' to display their 'pending message'.

It defines a base Contrarreembolso payment provider that allows making payments by bank transfer.

## Supported features

- Direct payment flow

## Module history

- `16.1`
  - The default payment instructions message of Contrarreembolso can be recomputed at any time after
    installation of the module. odoo/odoo#103903
- `16.0`
  - The `cashondelivery_mode` field is added to distinguish cashondelivery payment modes from other payment
    providers and to allow duplicating the base Contrarreembolso provider in multi-company databases.
    odoo/odoo#99400
  - The module is no longer automatically installed with the `payment` module. odoo/odoo#99400
  - The module is renamed from `payment_transfer` to `payment_cashondelivery`. odoo/odoo#99400

## Testing instructions

Contrarreembolso can be tested indifferently in test or live mode as it does not make API requests.
