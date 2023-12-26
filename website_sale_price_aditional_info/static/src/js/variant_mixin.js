odoo.define('website_sale_price_aditional_info.VariantMixin', function (require) {
'use strict';

const {Markup} = require('web.utils');
var VariantMixin = require('sale.VariantMixin');
var publicWidget = require('web.public.widget');
var core = require('web.core');
var QWeb = core.qweb;

require('website_sale.website_sale');

VariantMixin._onChangeCombinationAdditionalPrice = function (ev, $parent, combination) {
    var $aditional_price = $parent.find('.aditional_price');
    var $aditional_price_container = $parent.find('.aditional_price_container');
    if (!combination.website_price_additional_info) {
        $aditional_price_container.addClass('d-none');
    }else{
        $aditional_price_container.removeClass('d-none');
    }
    $aditional_price.text(combination.website_price_additional_info);
};

publicWidget.registry.WebsiteSale.include({
    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination: function () {
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationAdditionalPrice.apply(this, arguments);
    },
    /**
     * Recomputes the combination after adding a product to the cart
     * @override
     */
    _onClickAdd(ev) {
        return this._super.apply(this, arguments).then(() => {
            if ($('div.availability_messages').length) {
                this._getCombinationInfo(ev);
            }
        });
    }
});

return VariantMixin;

});

