===============================
Xtendoo Account Payment Effects
===============================

This module adds customer collection effects management on top of OCA payment
orders/lots for Odoo 19 Community.

Features
========

* Reuses ``account.payment``, ``account.payment.order`` and ``account.payment.lot``.
* Supports checks, promissory notes and future collection instruments through
  payment method line configuration.
* Keeps invoices in ``in_payment`` until the bank statement matches the payment.
* Creates deposit/remittance lots from existing payments without recreating them.
* Adds payment lot selection to OCA bank reconciliation.
* Protects existing payments when canceling Xtendoo lots/orders.

Dependencies
============

* ``account_payment_batch_oca``
* ``account_reconcile_oca``

Configuration
=============

1. Go to ``Accounting -> Configuration -> Payment Methods``.
2. Create or edit an inbound payment method line.
3. Enable ``Selectable on Payment Orders``.
4. Enable ``Manage as Collection Effect``.
5. Configure an outstanding receipt account in ``Outstanding Receipt Account``.
6. Enable reference and due date requirements as needed.

Example: Check
==============

* Payment type: Inbound
* Manage as Collection Effect: enabled
* Effect Reference Required: enabled
* Effect Due Date Required: disabled

Example: Promissory Note
========================

* Payment type: Inbound
* Manage as Collection Effect: enabled
* Effect Reference Required: enabled
* Effect Due Date Required: enabled

Outstanding receipt accounts
============================

Do not create custom accounting logic in this module. Configure the outstanding
receipt account directly on ``account.payment.method.line.payment_account_id``.
Typical examples are portfolio checks or promissory notes accounts.

Usage
=====

Register a check from an invoice
--------------------------------

1. Open a customer invoice.
2. Click ``Register Payment``.
3. Choose an effect-enabled payment method.
4. Enter the effect reference and due date when applicable.
5. Create the payment.

The payment is posted to the configured outstanding receipt account and the
invoice remains ``in_payment`` until the bank statement is reconciled.

Consult collection effects
--------------------------

Open ``Accounting -> Customers -> Collection Effects``.
Use the provided filters to distinguish:

* In portfolio.
* Deposited/remitted.
* Collected.
* Rejected.
* Canceled.
* Overdue / due today / upcoming / without due date.

Create a deposit/remittance lot
-------------------------------

1. Open ``Collection Effects``.
2. Select existing inbound customer payments managed as effects, all sharing
   the same company, currency and bank journal (any mix of collection
   methods on that journal is fine).
3. Run ``Create Deposit/Remittance Lot`` from the action menu.
4. Confirm the wizard.

The module creates one ``account.payment.order`` with
``xtd_source_type = existing_payments`` and one related ``account.payment.lot``.
No new payments and no new journal entries are created.

Alternatively, from ``Accounting -> Customers -> Remesas de efectos`` create a
new payment/debit order, set its payment method, and use the ``Diario de
banco`` field to pick the actual destination bank journal for the deposit -
it can be any journal of type "Bank", independently of the journal tied to
the payment method. Then click ``Importar pagos existentes`` (visible only
for methods configured as collection effects, instead of OCA's ``Importar
apuntes contables`` which creates new payments from pending invoice lines).
This fills the ``Pagos existentes`` tab in place with every eligible payment
sharing that same company and destination journal - any collection method,
not just the one chosen for the order - not yet matched or assigned to a lot.
Remove any row you do not want with the list's delete icon, adjust the
deposit date, then click ``Confirmar pagos``. You can click ``Importar pagos
existentes`` again at any time while still in draft to refresh the list; it
stays available even after payments have been added.

Reconcile a lot
---------------

1. Create or import the bank statement line for the deposit.
2. Open the OCA reconciliation form.
3. Go to the ``Payment Lots`` tab.
4. Select the lot.
5. Validate the reconciliation.

The payment liquidity lines are added as counterparts. Once reconciliation is
complete, payments become matched and invoices move from ``in_payment`` to
``paid`` through standard Odoo reconciliation.

Cancel a lot safely
-------------------

If the lot has no matched payments yet, open the related payment order and
use the standard ``Cancel Payments`` button.

This operation:

* removes ``payment_lot_id`` from payments,
* removes ``payment_order_id`` from payments,
* deletes the OCA lot structure,
* keeps the original payments,
* keeps the posted journal entries,
* keeps the invoice/payment reconciliation intact.

Returned / rejected effects
===========================

* If the effect has not been matched with a bank transaction yet
  (``is_matched = False``), use the standard ``Reject`` button on the
  payment. This only sets ``state = rejected``; no journal entry is deleted.
* If the effect is already matched with a bank transaction
  (``is_matched = True``), the module blocks both ``Reject`` and ``Cancel``
  directly on the payment. ``Cancel`` is blocked too because core Odoo's
  ``button_cancel()`` silently calls ``remove_move_reconcile()`` before
  cancelling the journal entry - clicking it on an already-matched effect
  would otherwise rip out the bank reconciliation with no warning. Reverse
  the bank matching first through the standard/OCA reconciliation flow
  (import or create an offsetting bank statement line for the bounced amount
  and reconcile it against the same payment), then reject or cancel the
  payment. This never touches ``account.partial.reconcile`` directly and
  never deletes journal entries with SQL.

Difference between is_reconciled and is_matched
===============================================

* ``is_reconciled`` means the payment has been reconciled against the invoice
  receivable/payable side.
* ``is_matched`` means the payment liquidity side has been matched with the bank
  statement or equivalent bank-side reconciliation.

Therefore, an effect can already be reconciled with the invoice while still not
matched with the bank. That is why the invoice stays ``in_payment`` before the
bank matching and becomes ``paid`` only afterwards.

Note that ``account.payment.state`` (Draft/In Process/Paid) can independently
show ``paid`` before ``is_matched`` is true - core Odoo flips a payment to
``paid`` once every invoice it is reconciled against has ``payment_state =
paid``, which for grouped or multi-invoice payments does not always line up
with that specific payment's own bank matching. For that reason, the lot's
payment list shows ``xtd_effect_status`` (derived purely from ``is_matched``
and ``payment_lot_id``) as the primary status column instead of the raw
``state`` field, which stays available as an optional column.

Limitations
===========

* One Xtendoo lot always has one company, one currency and one journal; it can
  mix several collection payment methods (for example check and promissory
  note) as long as they share those three. Payments on a different journal
  need a separate order/lot.
* The module relies on OCA reconciliation UI and does not add custom JS.

