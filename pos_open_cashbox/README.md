# POS Open Cash Drawer

## Description

This module adds a new option "Open Cash Drawer" in the Point of Sale hamburger menu,
allowing users to manually open the cash drawer without making a sale or payment.

## Features

- **New Menu Option**: Adds "Open Cash Drawer" button in the POS burger menu
- **Smart Visibility**: The option only appears when:
  - Cash drawer is configured in POS settings (`iface_cashdrawer` is enabled)
  - A receipt printer is connected and available
  - The user has appropriate permissions (not a minimal role user)
- **User Feedback**: Shows success/error notifications after attempting to open the
  drawer
- **Action Logging**: The manual drawer opening is logged with the "MANUAL_OPEN" action
  type

## Requirements

- Odoo 19.0 Community or Enterprise
- Point of Sale module installed
- Hardware proxy configured with a receipt printer that has cash drawer support

## Configuration

1. Go to Point of Sale > Configuration > Point of Sale
2. Enable "Cash Drawer" option in the Hardware Proxy / PosBox section
3. Configure the IoT Box or hardware proxy connection

## Usage

1. Open a POS session
2. Click on the hamburger menu (☰) in the top-right corner
3. Click on "Open Cash Drawer" option
4. The cash drawer will open

## Technical Details

This module patches the `Navbar` component from the Point of Sale module to:

- Add the `openCashDrawer()` method that calls `hardwareProxy.openCashbox()`
- Add a computed property `showOpenCashDrawerButton` to control visibility
- Extend the navbar XML template to include the new menu item

## Author

**Xtendoo**

- Website: https://xtendoo.es

## License

LGPL-3
