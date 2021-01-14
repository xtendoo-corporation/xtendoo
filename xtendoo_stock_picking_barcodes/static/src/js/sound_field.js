/* Copyright 2020 Xtendoo - Manuel Calero.
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define('stock_barcodes.field_sound_widget', function (require) {
"use strict";

    var basicFields = require('web.basic_fields');
    var core = require('web.core');
    var fieldRegistry = require('web.field_registry');

    var FieldChar = basicFields.FieldChar;

    /**
     * FieldCharSoundWidget is a widget to play a sound when value contains Error.
     */
    var FieldCharSoundWidget = FieldChar.extend({

        // properties

        _audio: null,

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _playSound() {
            if (typeof (Audio) !== "undefined") {
                if (!this._audio) {
                    this._audio = new Audio();
                    var ext = this._audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                    var session = this.getSession();
                    this._audio.src = session.url("/xtendoo_stock_picking_barcodes/static/src/sounds/error" + ext);
                }
                this._audio.play();
            }
        },

        _renderReadonly: function() {
            this._super.apply(this, arguments);
            if (this.value.toString().indexOf('Error') > -1){
                this._playSound();
            }
        },

    });

    fieldRegistry.add('field_char_sound', FieldCharSoundWidget);

    return FieldCharSoundWidget;
});
