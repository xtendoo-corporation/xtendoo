/* Copyright 2020 Manuel Calero - Xtendoo
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define('stock_picking_codebar_gs1.FormController', function (require) {
    'use strict';

    var FormController = require('web.FormController');

    FormController.include({
        _barcodeScanned: function (barcode, target) {
            var self = this;
            /*
            Set control focus to package_qty or product_qty directly after
            scan a barcode for manual entry mode entries.
            */
            this._super(barcode, target);
        },
    });
});
