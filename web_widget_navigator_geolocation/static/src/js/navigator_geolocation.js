odoo.define('web.WidgetNavigatorGeolocationButton', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;


var WidgetNavigatorGeolocationButton = AbstractField.extend({
    template: 'NavigatorGeolocation.Buttons',
    events: {
        'click': '_onClick',
    },

    // inherited
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.latitude = 0;
        this.longitude = 0;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    /**
     * This widget is supposed to be used inside a stat button and, as such, is
     * rendered the same way in edit and readonly mode.
     *
     * @override
     * @private
     */
//    _render: function () {
//        this.$el.empty();
//        var text = "lat: " + this.latitude + " - lon: " + this.latitude;
//        var $val = $('<span>').text(text);
//    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Redirects to the website page of the record.
     *
     * @private
     */
    _onClick: function () {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(position => {
            this.latitude = position.coords.latitude;
            this.longitude = position.coords.longitude;
            this.$('.latitude').text(this.latitude);
            this.$('.longitude').text(this.longitude);
            this._rpc({
                model: 'res.users',
                method: 'change_geolocation',
                args: [this.latitude, this.longitude],
            });
        })
      } else {
        alert("Geolocation is not supported by this browser.");
      }
    },

});

field_registry
    .add('navigator_geolocation_button', WidgetNavigatorGeolocationButton);
});
