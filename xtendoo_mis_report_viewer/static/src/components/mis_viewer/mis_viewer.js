/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart, useState } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class MisEnhancedViewer extends Component {
    static template = "xtendoo_mis_report_viewer.MisEnhancedViewer";
    static components = { Layout, Dropdown, DropdownItem };

    setup() {
        this.actionService = useService("action");
        this.notificationService = useService("notification");

        this.state = useState({
            instanceId: this.props.action?.params?.report_instance_id || this.props.action?.context?.active_id,
            metadata: {},
            reportData: { lines: [], header: [] },
            options: null,
            loading: true,
        });

        this.searchTimeout = null;

        onWillStart(async () => {
            if (this.state.instanceId) {
                await this.loadMetadata();
                await this.loadReportData();
            } else {
                this.state.loading = false;
            }
        });
    }

    onDateChange() {
        this.loadReportData();
    }

    onFilterDate(filter) {
        this.state.options.date.filter = filter;
        this.loadReportData();
    }

    toggleUnfoldAll() {
        this.state.options.unfold_all = !this.state.options.unfold_all;
        this.loadReportData();
    }

    get filteredLines() {
        if (!this.state.options) {
            return [];
        }
        const search = (this.state.options.search || "").toLowerCase();
        if (!search) {
            return this.state.reportData.lines;
        }
        return (this.state.reportData.lines || []).filter(l =>
            (l.name || "").toLowerCase().includes(search)
        );
    }

    toggleOption(option) {
        this.state.options[option] = !this.state.options[option];
        this.loadReportData();
    }

    onSearchInput(ev) {
        this.state.options.search = ev.target.value;
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        this.searchTimeout = setTimeout(() => {
            this.loadReportData();
        }, 500);
    }

    onFilterComparison(filter) {
        this.state.options.comparison.filter = filter;
        this.loadReportData();
    }

    toggleJournal(journal) {
        journal.selected = !journal.selected;
        this.loadReportData();
    }

    getSelectedJournalsCount() {
        if (!this.state.options) {
            return 0;
        }
        return (this.state.options.journals || []).filter(j => j.selected).length;
    }

    async loadMetadata() {
        try {
            const metadata = await rpc("/xtendoo_mis_report_viewer/get_metadata", {
                instance_id: this.state.instanceId,
            });
            this.state.metadata = metadata;
        } catch (error) {
            this.notificationService.add(_t("Error loading metadata"), { type: "danger" });
        }
    }

    async loadReportData(options = null) {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await rpc("/xtendoo_mis_report_viewer/get_report_data", {
                instance_id: this.state.instanceId,
                options: options || this.state.options,
            });
            if (data.error) {
                this.state.error = data.error;
                this.notificationService.add(data.error, { type: "danger" });
            } else {
                this.state.reportData = data;
                this.state.options = data.options;
            }
        } catch (error) {
            console.error("Error loading report:", error);
            const errorMessage = _t("Error loading report data. Please try again.");
            this.state.error = errorMessage;
            this.notificationService.add(errorMessage, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async onDrilldown(drilldownArg) {
        try {
            const action = await rpc("/xtendoo_mis_report_viewer/drilldown", {
                instance_id: this.state.instanceId,
                drilldown_arg: drilldownArg,
            });
            if (action) {
                this.actionService.doAction(action);
            }
        } catch (error) {
            this.notificationService.add(_t("Error during drilldown"), { type: "danger" });
        }
    }

    async onExport(format) {
        try {
            const action = await rpc("/xtendoo_mis_report_viewer/export_report", {
                instance_id: this.state.instanceId,
                format: format,
                options: this.state.options,
            });
            if (action) {
                this.actionService.doAction(action);
            }
        } catch (error) {
            this.notificationService.add(_t("Error exporting report"), { type: "danger" });
        }
    }

    toggleLine(lineId) {
        const unfolded = this.state.options.unfolded_lines || [];
        if (unfolded.includes(lineId)) {
            this.state.options.unfolded_lines = unfolded.filter(id => id !== lineId);
        } else {
            this.state.options.unfolded_lines = [...unfolded, lineId];
        }
        this.loadReportData();
    }
}

registry.category("actions").add("xtendoo_mis_report_viewer", MisEnhancedViewer);
