/* Copyright 2018-2019 Sergio Teruel <sergio.teruel@tecnativa.com>.
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define("stock_barcodes.FormController", function(require) {
    "use strict";

    var FormController = require("web.FormController");
    var core = require("web.core");
    var _t = core._t;

    FormController.include({
        events: {
            "click .o_button_cancel_scanner": "_onCancelScanner",
            "click .o_button_validate_scanner": "_onValidateScanner",
            "click .o_button_test_scanner": "_onValidateScanner",
        },

        _barcodeScanned: function(barcode, target) {
            var self = this;

            /*
            Set control focus to package_qty or product_qty directly after
            scan a barcode for manual entry mode entries.
            */

            this._super(barcode, target).then(function() {
                var manual_entry_mode = self.$("div[name='manual_entry'] input").val();
                if (manual_entry_mode) {
                    self.$("input[name='product_qty']").focus();
                }
            });
        },
        renderButtons: function($node) {

            /* Hide save and discard buttons from wizard, for this form do
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
        _onValidateScanner: function() {
            var self = this;
            var prom = Promise.resolve();
            var recordID = this.renderer.getEditableRecordID();
            if (recordID) {
                // If user's editing a record, we wait to save it before to try to
                // validate the inventory.
                prom = this.saveRecord(recordID);
            }

            prom.then(function() {
                self._rpc({
                    model: "wiz.stock.barcodes.read.picking",
                    method: "action_validate_picking",
                }).then(function(res) {
                    var exitCallback = function(infos) {
                        // In case we discarded a wizard, we do nothing to stay on
                        // the same view...
                        if (infos && infos.special) {
                            return;
                        }
                        // ... but in any other cases, we go back on the inventory form.
                        self.do_notify(
                            _t("Success"),
                            _t("The picking has been validated")
                        );
                        self.trigger_up("history_back");
                    };

                    if (_.isObject(res)) {
                        self.do_action(res, {on_close: exitCallback});
                    } else {
                        return exitCallback();
                    }
                });
            });
        },
        _onCancelScanner: function() {
            this.trigger_up("history_back");
        },
        _onValidateScanner: function() {
            this.trigger_up("history_back");
        },
        _onTestScanner: function() {
            alert("Test Scanner.");
        },
    });
});
