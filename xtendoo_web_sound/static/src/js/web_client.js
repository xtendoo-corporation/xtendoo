odoo.define('tutorial.ClientAction', function (require) {
    "use strict";

    // Load these requirements so that we can use these components for our own action.
    const AbstractAction = require('web.AbstractAction');
    const Widget = require('web.Widget');
    const core = require('web.core');

    // Extend the AbstractAction (base class) to define our own template
    const QuizAction = AbstractAction.extend({
        template: "tutorial.ClientAction",

        start() {
            const counter = new Counter(this, 47);
            counter.appendTo(this.$el);
        }
    });

    // Create the Counter widget by extending the default web widget.
    const Counter = Widget.extend({
        template: "tutorial.Counter",
        events: {
          'click .increment': 'increment'
        },

        init(parent, value) {
          this._super(parent);
          this.value = value;
        },

        increment() {
          this.value++;
          this.$el.find('span.o-value').text(this.value);
        },
    });

    // Adds it to the registry so that the action is loaded by Odoo
    core.action_registry.add('tutorial.quiz', QuizAction);

//    WebClient.include({
//        play_sound_bell: function() {
//            var src = "/web_sound/static/src/sounds/bell.wav";
//            $('body').append('<audio src="'+src+'" autoplay="true"></audio>');
//        },
//        play_sound_error: function() {
//            var src = "/web_sound/static/src/sounds/error.wav";
//            $('body').append('<audio src="'+src+'" autoplay="true"></audio>');
//        },
//    });

});
