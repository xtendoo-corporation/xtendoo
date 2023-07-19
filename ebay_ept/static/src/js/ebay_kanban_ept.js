odoo.define('ebay_ept.ebay_kanban_ept', function (require) {
    "use strict";
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');

    var eBayKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: KanbanController,
        }),
    });

    viewRegistry.add('eBayKanbanEpt', eBayKanbanView);
});
