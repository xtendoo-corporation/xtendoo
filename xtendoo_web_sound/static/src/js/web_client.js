/*

https://www.oocademy.com/v13.0/tutorial/creating-javascript-classes-and-widgets-in-odoo-56
usuario : manuelcalerosolis@gmail.com
password : nidorino

https://www.cybrosys.com/blog/how-to-load-js-function-menu-item-click-odoo-13

js:
    var GreetingMessage = AbstractAction.extend({

    core.action_registry.add('hr_attendance_greeting_message', GreetingMessage);

xml:
    <record id="hr_attendance_action_greeting_message" model="ir.actions.client">
        <field name="name">Message</field>
        <field name="tag">hr_attendance_greeting_message</field>
    </record>

py:
    def attendance_action(self, next_action):
        action_message = self.env.ref('hr_attendance.hr_attendance_action_greeting_message').read()[0]
        return action_message

*/

odoo.define('tutorial.ClientAction', function (require) {
  // We use the require() to import the widgets we need for our own widget.
  const AbstractAction = require('web.AbstractAction');
  const Widget = require('web.Widget');
  const core = require('web.core');
  const field_registry = require('web.field_registry');

  // Extend the AbstractAction (base class) to define our own template
  const QuizAction = AbstractAction.extend({
    template: "tutorial.ClientAction",

    events: {
      'click .o_quiz_button_click': 'quiz_button_click'
    },

    quiz_button_click() {
      alert('QuizAction Clicked');
    },

    start() {
      const counter = new Counter(this, 47);
      counter.appendTo(this.$el);
    }
  });

  const ButtonWidget = Widget.extend({
    events: {
      'click .button_widget': 'button_widget'
    },

    button_widget: function () {
      alert('Button Clicked')
    },

  });

  const CounterWidget = Widget.extend({
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

    play_sound_error() {
      var src = "/xtendoo_web_sound/static/src/sounds/error.wav";
      $('body').append('<audio src="'+src+'" autoplay="true"></audio>');
    },

  });

  // Adds it to the registry so that the action is loaded by Odoo
  field_registry.add('counter_widget', CounterWidget);
  core.action_registry.add('quiz_action', QuizAction);

  return {
    CounterWidget: CounterWidget,
    QuizAction: QuizAction,
  }

});

/*
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
*/
