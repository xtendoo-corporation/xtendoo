odoo.define('qrcode_table.pos', function(require) {
    "use strict";
    var models = require('point_of_sale.models');
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attr, options) {
            _super_order.initialize.apply(this, arguments);
            this.is_table_order = false;
            this.token = false;
        },
        set_is_table_order: function(is_table_order) {
            this.is_table_order = is_table_order;
            this.trigger('change', this);
        },
        get_is_table_order: function() {
            return this.is_table_order;
        },
        set_token_table: function(token) {
            this.token = token;
            this.trigger('change', this);
        },
        get_token_table: function() {
            return this.token;
        },
        get_line_all_ready_exit: function(line_id) {
            var self = this;
            var orderlines = self.orderlines.models;
            var flag = false;
            _.each(orderlines, function(line) {
                if (line_id == line.table_order_line_id) {
                    flag = true;
                }
            });
            return flag;
        },
        printChanges: async function(){
            let isPrintSuccessful = await _super_order.printChanges.apply(this, arguments);
            if(isPrintSuccessful){
                if (this.orderlines) {
                    if (this.orderlines.models) {
                        var lines = $.map(this.orderlines.models, function(n) {
                            return n.table_order_line_id;
                        });
                        if (lines) {
                            var orderd_st = await this.table_ordered_items(lines);
                        }
                    }
                }
            }
            return isPrintSuccessful;
        },
        table_ordered_items: async function(lines){
            var orderd_st = await this.pos.rpc({
                    model: 'table.order.line',
                    method: 'get_table_order_line_state_ordered',
                    args: [lines],
                });
            return orderd_st;
        },
        export_as_JSON: function() {
            var json = _super_order.export_as_JSON.apply(this, arguments);
            json.is_table_order = this.get_is_table_order();
            json.token = this.get_token_table();
            return json;
        },
    });
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.apply(this, arguments);
            this.table_order_line_id = false;
        },
        set_table_order_line_id: function(table_order_line_id) {
            this.table_order_line_id = table_order_line_id;
            this.trigger('change', this);
        },
        get_table_order_line_id: function() {
            return this.table_order_line_id;
        },
    });
});