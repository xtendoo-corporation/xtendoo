odoo.define('qrcode_table.custom', function(require) {
    "use strict";
    require('web.dom_ready');
    require('bus.BusService');
    var core = require('web.core');
    var session = require('web.session');
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var _t = core._t;
    var publicWidget = require('web.public.widget');

    publicWidget.registry.PosTabelOrder = publicWidget.Widget.extend({
        selector: '.pos_table_order',
        events: {
            'click .quick-modal.in button.js_add_cart_json': '_onQuickViewAddCartJSON',
            'change .quick-modal input.js_variant_change, ul[data-attribute_value_ids]': '_onChangeQucikViewVariant',
            'click .quick .quick-view': '_onClickQuickViewPOSTable',
            'click .shopping_cart_table .remove_order_line': '_onClickRemoveOrderLine',
            'click .quick-modal.in .js_check_product': '_onClickCheckProductAddToCart',
            'click .edit_pos_table_notes': '_onClickEditPosTableNote',
            'click .btn_pos_table_note_update': '_onClickUpdatePosTableNote',
        },
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            var self = this;
            var def = this._super.apply(this, arguments);
            $(".model_resume_tb_order").modal({
                show: true,
                backdrop: 'static',
                keyboard: false
            });
            $(".quick-modal").each(function() {
                $('input.js_variant_change', this).first().trigger('change');
            });
            return def;
        },
        _onQuickViewAddCartJSON: function(ev) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            var $input = $link.closest('.input-group').find("input");
            var product_id = +$input.closest('*:has(input[name="product_id"])').find('input[name="product_id"]').val();
            var min = parseFloat($input.data("min") || 0);
            var max = parseFloat($input.data("max") || Infinity);
            var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val() || 0, 10);
            var new_qty = quantity > min ? (quantity < max ? quantity : max) : min;
            $('input[name="' + $input.attr("name") + '"]').add($input).filter(function() {
                var $prod = $(this).closest('*:has(input[name="product_id"])');
                return !$prod.length || +$prod.find('input[name="product_id"]').val() === product_id;
            }).val(new_qty).change();
            return false;
        },
        _priceToStr: function(price) {
            var l10n = _t.database.parameters;
            var precision = 2;

            if ($('.decimal_precision').length) {
                precision = parseInt($('.decimal_precision').last().data('precision'));
            }
            var formatted = _.str.sprintf('%.' + precision + 'f', price).split('.');
            formatted[0] = utils.insert_thousand_seps(formatted[0]);
            return formatted.join(l10n.decimal_point);
        },
        _onChangeQucikViewVariant: function(ev) {
            var self = this;
            var $ul = $(ev.target).closest('.js_add_cart_variants');
            var $parent = $ul.closest('.js_product');
            var $product_id = $parent.find('.product_id').first();
            var $price = $parent.find(".oe_price:first .oe_currency_value");
            var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
            var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
            var variant_ids = $ul.data("attribute_value_ids");
            if (_.isString(variant_ids)) {
                variant_ids = JSON.parse(variant_ids.replace(/'/g, '"'));
            }
            var values = [];
            var unchanged_values = $parent.find('div.oe_unchanged_value_ids').data('unchanged_value_ids') || [];

            $parent.find('input.js_variant_change:checked').each(function() {
                values.push(+$(this).val());
            });
            values = values.concat(unchanged_values);

            $parent.find("label").removeClass("text-muted css_not_available");

            var product_id = false;
            for (var k in variant_ids) {
                $price.html(self._priceToStr(variant_ids[k][2]));
                $default_price.html(self._priceToStr(variant_ids[k][3]));

                if (_.isEmpty(_.difference(variant_ids[k][1], values))) {
                    if (variant_ids[k][3] - variant_ids[k][2] > 0.01) {
                        $default_price.closest('.oe_website_sale').addClass("discount");
                        $optional_price.closest('.oe_optional').show().css('text-decoration', 'line-through');
                        $default_price.parent().removeClass('hidden');
                    } else {
                        $optional_price.closest('.oe_optional').hide();
                        $default_price.parent().addClass('hidden');
                    }
                    product_id = variant_ids[k][0];
                    break;
                }
            }

            $parent.find("input.js_variant_change:radio, select.js_variant_change").each(function() {
                var $input = $(this);
                var id = +$input.val();
                var values = [id];

                $parent.find("ul:not(:has(input.js_variant_change[value='" + id + "'])) input.js_variant_change:checked, select.js_variant_change").each(function() {
                    values.push(+$(this).val());
                });

                for (var k in variant_ids) {
                    if (!_.difference(values, variant_ids[k][1]).length) {
                        return;
                    }
                }
                $input.closest("label").addClass("css_not_available");
                $input.find("option[value='" + id + "']").addClass("css_not_available");
            });

            if (product_id) {
                $parent.removeClass("css_not_available");
                $product_id.val(product_id);
                $parent.find("#add_to_cart").removeClass("disabled");
            } else {
                $parent.addClass("css_not_available");
                $product_id.val(0);
                $parent.find("#add_to_cart").addClass("disabled");
            }
        },
        _onClickQuickViewPOSTable: function(event) {
            var $modal_quick = $(event.currentTarget).closest('.productprice').find('.quick-modal');
        },
        _onClickRemoveOrderLine: function(event) {
            var order_line = parseInt($(event.currentTarget).attr('order_line_id'));
            if (order_line) {
                ajax.jsonRpc("/table/remove/order_line_json", 'call', {
                    'line_id': order_line,
                }).then(function(data) {
                    if (data) {
                        if (data.table_cart_lines) {
                            $('.shopping_cart').html(data.table_cart_lines);
                        }
                    }
                });
            }
        },
        _onClickCheckProductAddToCart: function(event) {
            var self = this;
            var table_id = parseInt($(event.currentTarget).attr('table_id'));
            var product_id = parseInt($(event.currentTarget).closest('form').find("input[name='product_id']").val());
            var quantity = parseFloat($(event.currentTarget).closest('.quick-modal').find("input[name='add_qty']").val()) || 1.0;
            var notes = $(event.currentTarget).closest('.quick-modal').find("#notes").val()
            var $productbox = $(event.currentTarget).closest('.productbox');
            event.preventDefault();
            $(".quick-modal.in").modal('hide');

            self._rpc({
                route: "/table/cart/update_json",
                params: {
                    product_id: product_id,
                    table_id: table_id,
                    add_qty: quantity,
                    note: notes
                },
            }).then(function(data) {
                if (data) {
                    $('.shopping_cart').html(data['qrcode_table.table_cart_shop']);
                }
            });
            return false;
        },
        _onClickEditPosTableNote: function(event) {
            var self = this;
            var order_line = parseInt($(event.currentTarget).attr('order_line_id'));
            self._rpc({
                route: "/table/get/note",
                params: {
                    order_line_id: order_line,
                },
            }).then(function(data) {
                if (data) {
                    $('#pos_table_note_text').val(data.note);
                    $('.btn_pos_table_note_update').attr('order_line_id', data.order_line_id);
                    $('#EditPosTableNote').modal('show');
                }
            });
        },
        _onClickUpdatePosTableNote: function(event) {
            var self = this;
            var order_line = parseInt($(event.currentTarget).attr('order_line_id'));
            var note = $('#pos_table_note_text').val();
            self._rpc({
                route: "/table/update/note",
                params: {
                    order_line_id: order_line,
                    note: note,
                },
            }).then(function(data) {
                if (data && data.success) {
                    $('#EditPosTableNote').modal('hide');
                }
            });

        },
    });
    publicWidget.registry.PosTabelOrderConfirmPage = publicWidget.Widget.extend({
        selector: '.o_table_order_confirm',
        start: function() {
            var self = this;
            var def = this._super.apply(this, arguments);
            self._interval = window.setInterval(this._onQRCodeNotification.bind(this), 5000);
            return def;
        },
        _onQRCodeNotification: function() {
            this._rpc({
                route: "/qrcode_table/update_json",
            }).then(function(data) {
                $(".js_table_order_list").first().before(data['qrcode_table.table_cart_lines']).end().remove();
            });
        },
    });
});