odoo.define("web_notify.Notification", function(require) {
    "use strict";

    const Notification = require("web.Notification");

    Notification.include({
        // Properties
        _audio: null,

        icon_mapping: {
            success: "fa-thumbs-up",
            danger: "fa-exclamation-triangle",
            warning: "fa-exclamation",
            info: "fa-info",
            default: "fa-lightbulb-o",
        },

        init() {
            this._super.apply(this, arguments);
            // Delete default classes
            this.className = this.className.replace(" o_error", "");
            // Add custom icon and custom class
            this.icon =
                this.type in this.icon_mapping
                    ? this.icon_mapping[this.type]
                    : this.icon_mapping.default;
            this.className += " o_" + this.type;
            this._beep();
        },

        _beep() {
            console.log("_beep");
            if (typeof Audio !== "undefined") {
                if (!this._audio) {
                    this._audio = new Audio();
                    var ext = this._audio.canPlayType("audio/ogg; codecs=vorbis")
                        ? ".ogg"
                        : ".mp3";
                    var session = this.getSession();
                    this._audio.src = session.url(
                        "/xtendoo_web_notify/static/src/sounds/error" + ext
                    );
                }
                this._audio.play();
            }
        },
    });
});
