{
    "name": "POS Open Cash Drawer",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Adds an option to open the cash drawer from the POS burger menu",
    "description": """
        This module adds a new option in the POS hamburger menu to open the cash drawer.

        Features:
        - New menu item "Open Cash Drawer" in the POS burger menu
        - Uses the existing open_cashbox function from the hardware proxy
        - Only visible when cash drawer is configured and printer is connected
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_open_cashbox/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
