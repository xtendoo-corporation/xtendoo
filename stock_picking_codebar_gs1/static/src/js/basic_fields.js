/* Copyright 2020.
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */


odoo.define('stock_picking_codebar_gs1.RenderFieldOne2Many', function (require) {
    'use strict';

    var basic_fields = require('web.basic_fields');
    var relational_fields = require('web.relational_fields');
    var field_registry = require('web.field_registry');

    var RenderFieldOne2Many = relational_fields.FieldOne2Many.extend({
        /**
         * We want to use our custom renderer for the list.
         *
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.isDirty = true;
        },
        render: function () {
            alert("render!!");
        },
        reset: function (record, event) {
            this._reset(record, event);
            alert("reset!!");
            if (!event || event === this.lastChangeEvent) {
                this.isDirty = false;
            }
            if (this.isDirty) {
                return $.when();
            } else {
                return this._render();
            }
        },
        _getRenderer: function () {
            this.isDirty = true;
            return this._super.apply(this, arguments);
        },
    });

    field_registry.add('render_field_one2many', RenderFieldOne2Many);

    return {
        RenderFieldOne2Many: RenderFieldOne2Many,
    }
});
