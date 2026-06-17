# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Xtendoo HR Expense AI",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Expenses",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "AGPL-3",
    "summary": "Create HR expenses from documents using AI auto-detection",
    "depends": [
        "hr_expense",
        "xtendoo_ai_connector",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_expense_views.xml",
        "wizards/hr_expense_ai_wizard_views.xml",
    ],
    "external_dependencies": {
        "python": ["pdf2image"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

