odoo.define('qrcode_table.screen', function(require) {
    "use strict";
    
    const { debounce } = owl.utils;
    const { useContext } = owl.hooks;
    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const Chrome = require('point_of_sale.Chrome');
    const BusService = require('bus.BusService');

    const PosTableChrome = (Chrome) =>
        class extends Chrome {
            /**
             * @override
             */
            async start() {
                await super.start();
                this.env.services.bus_service.call('bus_service', 'updateOption', 'table.order', this.env.session.uid);
                this.env.services.bus_service.call('bus_service', 'onNotification', this, this._onNotification);
                this.env.services.bus_service.call('bus_service', 'startPolling');
            }
            _onNotification(notifications) {
                for (var notif of notifications) {
                    if (notif) {
                        var user_id = notif.payload;
                        var n = new Noty({
                            theme: 'light',
                            text: 'You have new order',
                            timeout: false,
                            layout: 'topRight',
                            type: 'success',
                            closeWith: ['button'],
                            sounds: {
                                sources: ['/qrcode_table/static/lib/noty/lib/done-for-you.mp3'],
                                volume: 1,
                                conditions: ['docVisible']
                            },
                        });
                        n.show();
                    }
                }
            }
        };
    Registries.Component.extend(Chrome, PosTableChrome);

    class TableOrderPosLines extends PosComponent {
        async LineStateChnage(line_id, state) {
            try {
                let tableorderslinestate = await this.rpc({
                    model: 'table.order.line',
                    method: 'change_table_order_state',
                    args: [line_id, state],
                });
                if(tableorderslinestate){
                    const TableOrderListScreen = Registries.Component.get('TableOrderListScreen');
                    var tableorders = await TableOrderListScreen.prototype.get_table_orders.apply(this, arguments);
                    this.trigger('close-temp-screen');
                    await this.showTempScreen('TableOrderListScreen', {
                        'tableorders': tableorders || []
                    });
                }
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to change state'),
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    TableOrderPosLines.template = 'TableOrderPosLines';
    Registries.Component.add(TableOrderPosLines);

    class TableOrderLine extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('toggleLineChange', (ev) => this.toggle_table_order(ev));
        }
        toggle_table_order(ev){
            var line_id = $(ev.currentTarget).closest('tr').data('id');
            $('.table_order_client_line').removeClass('highlight');
            $('.table_order_list_product').addClass('trhide');
            $(ev.currentTarget).closest('tr').toggleClass('highlight');
            $('tr[data-parent_id~="'+line_id+'"]').toggleClass('trhide');
       }
       async add_to_cart_table_order(){
            var self = this;
            var order = this.env.pos.get_order();
            var table = this.env.pos.tables_by_id[this.props.tos.table_id];
            this.env.pos.set_table(table);
            var isexit =  this.filter_order(this.props.tos.token);
            if(isexit){
                isexit.set_is_table_order(this.props.tos.is_table_order);
                isexit.set_token_table(this.props.tos.token);
                 _.each(this.props.tos.line, function(line) {
                    var product = self.env.pos.db.get_product_by_id(line.product_id);
                    var is_line_exit = isexit.get_line_all_ready_exit(line.id);
                    if (!is_line_exit) {
                        isexit.add_product(product, { quantity: line.qty, merge: false });
                        var od_line = isexit.get_selected_orderline();
                        od_line.set_table_order_line_id(line.id);
                        od_line.set_note(line.note);
                    }
                });
                await this.trigger('close-temp-screen');
                this.env.pos.set_order(isexit);
                this.env.pos.set_table(isexit.table, isexit);
            }else{
                order = this.env.pos.add_new_order();
                order.set_is_table_order(this.props.tos.is_table_order);
                order.set_token_table(this.props.tos.token);
                _.each(this.props.tos.line, function(line) {
                    var product = self.env.pos.db.get_product_by_id(line.product_id);
                    var is_line_exit = order.get_line_all_ready_exit(line.id);
                    if (!is_line_exit) {
                        order.add_product(product, { quantity: line.qty, merge: false });
                        var od_line = order.get_selected_orderline();
                        od_line.set_table_order_line_id(line.id);
                        od_line.set_note(line.note);
                    }
                });
                await this.trigger('close-temp-screen');
                this.env.pos.set_order(order);
                this.env.pos.set_table(order.table, order);
            }
       }
       async _onClickAcceptAllOrder(){
            try {
                let res = await this.rpc({
                        model: 'table.order',
                        method: 'change_table_accept_all_order',
                        args: [this.props.tos.id],
                    });
                if(res){
                    const TableOrderListScreen = Registries.Component.get('TableOrderListScreen');
                    var tableorders = await TableOrderListScreen.prototype.get_table_orders.apply(this, arguments);
                    this.trigger('close-temp-screen');
                    await this.showTempScreen('TableOrderListScreen', {
                        'tableorders': tableorders || []
                    });
                }
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to Accept order'),
                    });
                } else {
                    throw error;
                }
            }
       }
       async _onClickCancelAllOrder(){
            try {
                let res = await this.rpc({
                        model: 'table.order',
                        method: 'change_table_cance_all_order',
                        args: [this.props.tos.id],
                    });
                if(res){
                    const TableOrderListScreen = Registries.Component.get('TableOrderListScreen');
                    var tableorders = await TableOrderListScreen.prototype.get_table_orders.apply(this, arguments);
                    this.trigger('close-temp-screen');
                    await this.showTempScreen('TableOrderListScreen', {
                        'tableorders': tableorders || []
                    });
                }
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to Cancel Order'),
                    });
                } else {
                    throw error;
                }
            }
       }
       filter_order(token, table_id){
         var ex_order = false
         _.each(this.env.pos.get_order_list(), function(order){
                if(order.token == token && order.is_table_order){
                    ex_order = order;
                }
         });
         return ex_order;
       }
    }
    TableOrderLine.template = 'TableOrderLine';
    Registries.Component.add(TableOrderLine);

    class TableOrderListScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.top_orders = [];
        }
        back() {
            this.trigger('close-temp-screen');
            this.showScreen('FloorScreen');
        }
        get tableorders() {
            return this.props.tableorders || [];
        }
        async get_table_orders() {
            var table_id = false;
            if(this.env.pos.table && this.env.pos.table.id){
                table_id = parseInt(this.env.pos.table.id);
            }
            try {
                let tableorders = await this.rpc({
                    model: 'table.order',
                    method: 'get_table_order_lists',
                    args: [[]],
                });
                return tableorders;
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to Fetch orders'),
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    TableOrderListScreen.template = 'TableOrderListScreen';
    Registries.Component.add(TableOrderListScreen);

    class TableOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const TableOrderListScreen = Registries.Component.get('TableOrderListScreen');
            var tableorders = await TableOrderListScreen.prototype.get_table_orders.apply(this, arguments);
            await this.showTempScreen('TableOrderListScreen', {
                'tableorders': tableorders || []
            });
        }
    }
    TableOrderButton.template = 'TableOrderButton';

    ProductScreen.addControlButton({
        component: TableOrderButton,
        condition: function() {
            return true;
        },
    });

    Registries.Component.add(TableOrderButton);

    // return PrintBillButton;

});