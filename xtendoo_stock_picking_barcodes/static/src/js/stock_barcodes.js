/* Copyright 2021 Xtendoo - Manuel Calero.
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define("stock_barcodes.FormController", function(require) {
    "use strict";

    const Dialog = require("web.Dialog");

    var FormController = require("web.FormController");
    var core = require("web.core");
    var _t = core._t;

    FormController.include({
        events: {
            "click .o_button_cancel_scanner": "_onCancelScanner",
            "click .o_button_validate_scanner": "_onValidateScanner",
        },
        _barcodeScanned: function(barcode, target) {
            /*
            Set control focus to package_qty or product_qty directly after
            scan a barcode for manual entry mode entries.
            */

            if (barcode.includes("o.btn-cancel")){
                this._onCancelScanner();
                return null;
            }

            if (barcode.includes("o.btn-validate")){
                this._onValidateScanner();
            }

            this._super(barcode, target).then(function() {
                var manual_entry_mode = self.$("div[name='manual_entry'] input").val();
                if (manual_entry_mode) {
                    self.$("input[name='product_qty']").focus();
                }
            });
        },
        renderButtons: function($node) {
            /*
            Hide save and discard buttons from wizard, for this form do
            anything and confuse the user if he wants do a manual entry. All
            extended models from  wiz.stock.barcodes.read do not have this
            buttons.
            */

            this._super($node);
            if (this.modelName.includes("wiz.stock.barcodes.read.")) {
                this.$buttons.find(".o_form_buttons_edit").css({display: "none"});
            }
        },
        canBeDiscarded: function(recordID) {
            /*
            Silent the warning that says that the record has been modified.
            */

            if (!this.modelName.includes("wiz.stock.barcodes.read.")) {
                return this._super(recordID);
            }
            return Promise.resolve(false);
        },
        _onCancelScanner: function() {
            this.trigger_up("history_back");
        },
        _onValidateScanner: function() {
            this.trigger_up("history_back");
        },
    });
});
