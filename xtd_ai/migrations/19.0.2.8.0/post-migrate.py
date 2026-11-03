def migrate(cr, version):
    """Balanced profile by default: the old default (always confirm) is reset.

    Users who want a card for every write can switch it on again in their
    preferences; the policy keeps cards for prices, taxes, VAT and email.
    """
    cr.execute("UPDATE res_users SET xtd_ai_confirm_writes = false")
