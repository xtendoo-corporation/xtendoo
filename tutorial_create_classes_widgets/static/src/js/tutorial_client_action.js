odoo.define('tutorial.ClientAction', function (require) {

  // Load these requirements so that we can use these components for our own action.
  const AbstractAction = require('web.AbstractAction');
  const Widget = require('web.Widget');
  const core = require('web.core');

  // Let us create some example questions with answer options and correct answers as a demo.
  const DINOSAUR_QUIZ = [
    {
      question: "Which is the best dinosaur?",
      choices: {
        a: "tyrannosaurus",
        b: "diplodocus",
        c: "ankylosaurus",
        d: "iguanodon"
      },
      answer: "d"
    },
    {
      question: "Which of these animals is not a dinosaur?",
      choices: {
        a: "a triceratops",
        b: "a cow"
      },
      answer: "b"
    },
  ];

  const COLOR_QUIZ = [
    {
      question: "What is your favorite color?",
      choices: {
        a: "red",
        b: "blue",
        c: "green",
      },
      answer: "c"
    },
    {
      question: "How many colors are there?",
      choices: {
        a: "a lot",
        b: "100",
        c: "over 9000",
      },
      answer: "c"
    }
  ];

  const QUIZZES = {
    dinosaurs: DINOSAUR_QUIZ,
    colors: COLOR_QUIZ,
  };

  // Create a QuizAction which we add to the registry of Odoo later on
  const QuizAction = AbstractAction.extend({
    template: "tutorial.ClientAction",
    // Catch events done by the user to update our views
    custom_events: {
      quiz_selected: "selectQuiz",
      quiz_completed: "quizCompleted",
      back_to_selection: "backToSelection",
    },

    start() {
      alert("Start>>>")
      const quizSelection = new QuizSelection(this);
      quizSelection.appendTo(this.$el);
    },

    selectQuiz(ev) {
      const quizWidget = new Quiz(this, ev.data.quiz);
      // add Quiz widget to the DOM
      quizWidget.appendTo(this.$el);
      // remove previous QuizSelection widget
      ev.target.destroy();
    },

    quizCompleted(ev) {
      const summary = new QuizSummary(this, ev.data);
      summary.appendTo(this.$el);
      ev.target.destroy();
    },

    // Link back to the selection view
    backToSelection(ev) {
      const quizSelection = new QuizSelection(this);
      quizSelection.appendTo(this.$el);
      ev.target.destroy();
    },
  });


  const QuizSelection = Widget.extend({
    template: "tutorial.QuizSelection",
    // This event will go off if the user clicks on our button
    events: {
      "click button": "selectQuiz",
    },
    quizzes: Object.keys(QUIZZES),

    selectQuiz(ev) {
      const quiz = ev.target.dataset.quiz;
      this.trigger_up("quiz_selected", {quiz})
    },
  });


  const Quiz = Widget.extend({
    template: "tutorial.Quiz",

    events: {
      'click button': "selectChoice",
    },

    init(parent, quizName) {
      this._super(parent);
      // here we have the widget "static" state:
      this.quizName = quizName;
      this.questions = QUIZZES[quizName];

      // and here the widget "running" state:
      this.current = 0; // index of current question
      this.answers = []; // list of user answers
    },

    // Check which choice was taken
    selectChoice(ev) {
      const choice = ev.target.dataset.choice;
      this.answers.push(choice);
      if (this.current < this.questions.length - 1) {
        this.current++;
        this.renderElement();
      } else {
        // The quiz is completed
        this.trigger_up("quiz_completed", {
          name: this.quizName,
          answers: this.answers,
        });
      }
    },
  });

  const QuizSummary = Widget.extend({
    template: "tutorial.QuizSummary",
    events: {
      "click button": "backToSelection",
    },

    init(parent, result) {
      this._super(parent);
      this.result = result;
      this.questions = QUIZZES[result.name];
    },

    backToSelection() {
      this.trigger_up("back_to_selection");
    },
  });

  // Adds it to the registry so that the action is loaded by Odoo
  core.action_registry.add('tutorial.quiz', QuizAction);
});
