# Debug script for journal dashboard data
import json

journals = env["account.journal"].search([("type", "in", ["bank", "cash", "credit"])])
print("-" * 100)
print(
    f"{'ID':<5} | {'NAME':<30} | {'TYPE':<10} | {'HAS ACCOUNT':<12} | {'HAS DATA':<10}"
)
print("-" * 100)

for journal in journals:
    dashboard_data = {journal.id: {}}
    journal._fill_bank_cash_dashboard_data(dashboard_data)
    data = dashboard_data.get(journal.id, {})

    has_account = "YES" if journal.default_account_id else "NO"
    has_custom_data = "YES" if "account_id_balance" in data else "NO"

    print(
        f"{journal.id:<5} | {journal.name[:30]:<30} | {journal.type:<10} | {has_account:<12} | {has_custom_data:<10}"
    )
    if has_custom_data == "YES":
        print(f"      -> Balance: {data['account_id_balance']}")

print("-" * 100)
