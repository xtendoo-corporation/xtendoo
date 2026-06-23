import { Component, onWillStart, onMounted, onWillDestroy, onPatched, useState, useRef } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const Chart = window.Chart;

export class XtdDashboard extends Component {
    static template = "xtendoo_xtd_theme.XtdDashboard";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.session = session;

        this.salesChartRef = useRef("salesChart");
        this.orderStatusChartRef = useRef("orderStatusChart");
        this._chartInstances = {};

        this.state = useState({
            statistics: {},
            activities: [],
            topProducts: [],
            orderStatus: [],
            chartData: null,
            loading: true,
            layout: { mode: "global", can_customize: false, blocks: [] },
            editingLayout: false,
            draftBlocks: [],
            genericBlockData: {},
            previewBlock: null,
            builderOptions: { apps: [], models: [], fields: [] },
            showBlockBuilder: false,
            newBlock: {
                name: "",
                block_type: "generic_list",
                app: "",
                model: "",
                selectedFields: [],
                date_field: "",
                limit: 5,
                size: "medium",
            },
            isSidebarHidden: document.body.classList.contains("xtd-sidebar-hidden"),
            chartPeriod: "year",
            kpiPeriod: "month",
            topPeriod: "month",
            recentItems: { sales: [], orders: [], purchase_orders: [], invoiced: [] },
        });

        useBus(this.env.bus, "XTD_SIDEBAR:TOGGLE", () => {
            this.state.isSidebarHidden = document.body.classList.contains("xtd-sidebar-hidden");
        });

        onWillStart(async () => {
            await this._fetchData();
        });

        onMounted(() => {
            this._renderCharts();
        });

        onPatched(() => {
            this._renderCharts();
        });

        onWillDestroy(() => {
            this._destroyCharts();
        });
    }

    get statistics() { return this.state.statistics; }
    get activities() { return this.state.activities; }
    get topProducts() { return this.state.topProducts; }
    get orderStatus() { return this.state.orderStatus; }
    get dashboardBlocks() {
        return this.state.editingLayout ? this.state.draftBlocks : (this.state.layout.blocks || []);
    }
    get canEditLayout() { return !!this.state.layout.can_edit; }
    get editingLayout() { return this.state.editingLayout; }
    get availableDashboardBlocks() {
        const visibleKeys = new Set(this.state.draftBlocks.map((block) => block.key));
        const availableByKey = new Map();
        for (const block of [
            ...(this.state.layout.available_blocks || []),
            ...(this.state.layout.blocks || []),
        ]) {
            if (block?.key && !visibleKeys.has(block.key)) {
                availableByKey.set(block.key, block);
            }
        }
        return [...availableByKey.values()].sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
    }
    get isSidebarHidden() { return this.state.isSidebarHidden; }
    get filteredBuilderModels() {
        if (!this.state.newBlock.app) {
            return this.state.builderOptions.models || [];
        }
        return (this.state.builderOptions.models || []).filter((model) => (
            model.apps?.includes(this.state.newBlock.app)
        ));
    }

    async _fetchData() {
        this.state.loading = true;

        try {
            try {
                const layout = await this.orm.call("xtd.dashboard.service", "get_dashboard_layout", []);
                this.state.layout = layout?.blocks?.length ? layout : this._defaultLayout();
            } catch {
                this.state.layout = this._defaultLayout();
            }

            await Promise.all([
                this._fetchKpis(),
                this._fetchChartData(),
                this._fetchActivities(),
                this._fetchTopProducts(),
                this._fetchOrderStatus(),
                this._fetchRecentItems(),
            ]);

            await this._fetchGenericBlocks();
        } catch (e) {
            console.error("Error al cargar datos del dashboard:", e);
            this._resetData();
        } finally {
            this.state.loading = false;
        }
    }

    _resetData() {
        this.state.layout = this._defaultLayout();
        this.state.chartData = { labels: [], quotations: [], orders_count: [] };
        this.state.chartPeriod = "year";
        this.state.kpiPeriod = "month";
        this.state.topPeriod = "month";
        this.state.recentItems = { sales: [], orders: [], purchase_orders: [], invoiced: [] };
        this.state.statistics = this._formatKpis({});
        this.state.activities = [];
        this.state.topProducts = [];
        this.state.orderStatus = [];
    }

    _calcTrend(current, previous) {
        if (!previous) return current ? 100.0 : 0.0;
        return Math.round(((current - previous) / previous) * 100 * 10) / 10;
    }

    _getPeriodRange(period) {
        const now = new Date();
        let start, end;
        if (period === "week") {
            const day = now.getDay();
            const diff = day === 0 ? 6 : day - 1;
            start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - diff);
            end = new Date(start);
            end.setDate(start.getDate() + 6);
        } else if (period === "month") {
            start = new Date(now.getFullYear(), now.getMonth(), 1);
            end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        } else {
            start = new Date(now.getFullYear(), 0, 1);
            end = new Date(now.getFullYear(), 11, 31);
        }
        return { start, end };
    }

    async onChangeChartPeriod(period) {
        this.state.chartPeriod = period;
        await this._fetchChartData();
    }

    async onChangeKpiPeriod(period) {
        this.state.kpiPeriod = period;
        await this._fetchKpis();
        await this._fetchRecentItems();
    }

    async onChangeTopPeriod(period) {
        this.state.topPeriod = period;
        await this._fetchTopProducts();
    }

    _kpiPeriodRanges(period) {
        const now = new Date();
        let curStart, curEnd, prevStart, prevEnd;
        if (period === "week") {
            const day = now.getDay();
            const diff = day === 0 ? 6 : day - 1;
            curStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - diff);
            curEnd = new Date(curStart);
            curEnd.setDate(curStart.getDate() + 6);
            prevStart = new Date(curStart);
            prevStart.setDate(prevStart.getDate() - 7);
            prevEnd = new Date(curStart);
        } else if (period === "year") {
            curStart = new Date(now.getFullYear(), 0, 1);
            curEnd = new Date(now.getFullYear(), 11, 31);
            prevStart = new Date(now.getFullYear() - 1, 0, 1);
            prevEnd = new Date(now.getFullYear() - 1, 11, 31);
        } else {
            curStart = new Date(now.getFullYear(), now.getMonth(), 1);
            curEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            prevStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            prevEnd = new Date(now.getFullYear(), now.getMonth(), 0);
        }
        const endNext = new Date(curEnd);
        endNext.setDate(endNext.getDate() + 1);
        const prevEndNext = new Date(prevEnd);
        prevEndNext.setDate(prevEndNext.getDate() + 1);
        return { curStart, curEnd, prevStart, prevEnd, endNext, prevEndNext };
    }

    async _fetchKpis() {
        const period = this.state.kpiPeriod || "month";
        const { curStart, prevStart, endNext, prevEndNext } = this._kpiPeriodRanges(period);
        const fmt = d => d.toISOString().split("T")[0];

        const readSum = (model, domain, fields) =>
            this.orm.call(model, "search_read", [domain, fields], { limit: 10000 });

        const kpis = {};

        try {
            const [cur, prev] = await Promise.all([
                readSum("sale.order", [
                    ["state", "in", ["sale", "done"]],
                    ["date_order", ">=", fmt(curStart)],
                    ["date_order", "<", fmt(endNext)],
                ], ["amount_total"]),
                readSum("sale.order", [
                    ["state", "in", ["sale", "done"]],
                    ["date_order", ">=", fmt(prevStart)],
                    ["date_order", "<", fmt(prevEndNext)],
                ], ["amount_total"]),
            ]);
            kpis.sales = {
                value: cur.length,
                previous_value: prev.length,
                total: cur.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                previous_total: prev.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                label: "Pedidos venta", icon: "fa-shopping-bag",
            };
        } catch {
            kpis.sales = { value: 0, previous_value: 0, total: 0, previous_total: 0, label: "Pedidos venta", icon: "fa-shopping-bag" };
        }

        try {
            const [cur, prev] = await Promise.all([
                readSum("sale.order", [
                    ["state", "in", ["draft", "sent"]],
                    ["date_order", ">=", fmt(curStart)],
                    ["date_order", "<", fmt(endNext)],
                ], ["amount_total"]),
                readSum("sale.order", [
                    ["state", "in", ["draft", "sent"]],
                    ["date_order", ">=", fmt(prevStart)],
                    ["date_order", "<", fmt(prevEndNext)],
                ], ["amount_total"]),
            ]);
            kpis.orders = {
                value: cur.length,
                previous_value: prev.length,
                total: cur.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                previous_total: prev.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                label: "Presupuestos", icon: "fa-file-text-o",
            };
        } catch {
            kpis.orders = { value: 0, previous_value: 0, total: 0, previous_total: 0, label: "Presupuestos", icon: "fa-file-text-o" };
        }

        try {
            const [cur, prev] = await Promise.all([
                readSum("account.move", [
                    ["move_type", "=", "out_invoice"],
                    ["state", "=", "posted"],
                    ["invoice_date", ">=", fmt(curStart)],
                    ["invoice_date", "<", fmt(endNext)],
                ], ["amount_total"]),
                readSum("account.move", [
                    ["move_type", "=", "out_invoice"],
                    ["state", "=", "posted"],
                    ["invoice_date", ">=", fmt(prevStart)],
                    ["invoice_date", "<", fmt(prevEndNext)],
                ], ["amount_total"]),
            ]);
            kpis.invoiced = {
                value: cur.length,
                previous_value: prev.length,
                total: cur.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                previous_total: prev.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                label: "Facturado", icon: "fa-file-text-o",
            };
        } catch {
            kpis.invoiced = { value: 0, previous_value: 0, total: 0, previous_total: 0, label: "Facturado", icon: "fa-file-text-o" };
        }

        try {
            const [cur, prev] = await Promise.all([
                readSum("purchase.order", [
                    ["state", "in", ["purchase", "done"]],
                    ["date_order", ">=", fmt(curStart)],
                    ["date_order", "<", fmt(endNext)],
                ], ["amount_total"]),
                readSum("purchase.order", [
                    ["state", "in", ["purchase", "done"]],
                    ["date_order", ">=", fmt(prevStart)],
                    ["date_order", "<", fmt(prevEndNext)],
                ], ["amount_total"]),
            ]);
            kpis.purchase_orders = {
                value: cur.length,
                previous_value: prev.length,
                total: cur.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                previous_total: prev.reduce((s, r) => s + Number(r.amount_total || 0), 0),
                label: "Compras", icon: "fa-truck",
            };
        } catch {
            kpis.purchase_orders = { value: 0, previous_value: 0, total: 0, previous_total: 0, label: "Compras", icon: "fa-truck" };
        }

        for (const key of Object.keys(kpis)) {
            const trendValue = key === "invoiced" ? kpis[key].total : kpis[key].value;
            const previousTrendValue = key === "invoiced" ? kpis[key].previous_total : kpis[key].previous_value;
            kpis[key].trend = this._calcTrend(trendValue, previousTrendValue);
        }

        this.state.statistics = this._formatKpis(kpis);
    }

    async _fetchRecentItems() {
        const period = this.state.kpiPeriod || "month";
        const { curStart, endNext } = this._kpiPeriodRanges(period);
        const fmt = d => d.toISOString().split("T")[0];

        try {
            this.state.recentItems.sales = await this.orm.call("sale.order", "search_read", [
                [["state", "in", ["sale", "done"]],
                 ["date_order", ">=", fmt(curStart)], ["date_order", "<", fmt(endNext)]],
                ["name", "partner_id", "amount_total", "date_order"],
            ], { limit: 3, order: "date_order desc" });
        } catch {
            this.state.recentItems.sales = [];
        }

        try {
            this.state.recentItems.orders = await this.orm.call("sale.order", "search_read", [
                [["state", "in", ["draft", "sent"]],
                 ["date_order", ">=", fmt(curStart)], ["date_order", "<", fmt(endNext)]],
                ["name", "partner_id", "amount_total", "date_order"],
            ], { limit: 3, order: "date_order desc" });
        } catch {
            this.state.recentItems.orders = [];
        }

        try {
            this.state.recentItems.invoiced = await this.orm.call("account.move", "search_read", [
                [["move_type", "=", "out_invoice"], ["state", "=", "posted"],
                 ["invoice_date", ">=", fmt(curStart)], ["invoice_date", "<", fmt(endNext)]],
                ["name", "partner_id", "amount_total", "invoice_date"],
            ], { limit: 3, order: "invoice_date desc" });
        } catch {
            this.state.recentItems.invoiced = [];
        }

        try {
            this.state.recentItems.purchase_orders = await this.orm.call("purchase.order", "search_read", [
                [["state", "in", ["purchase", "done"]],
                 ["date_order", ">=", fmt(curStart)], ["date_order", "<", fmt(endNext)]],
                ["name", "partner_id", "amount_total", "date_order"],
            ], { limit: 3, order: "date_order desc" });
        } catch {
            this.state.recentItems.purchase_orders = [];
        }
    }

    async _fetchChartData() {
        const period = this.state.chartPeriod || "year";
        const { start, end } = this._getPeriodRange(period);
        const endNext = new Date(end);
        endNext.setDate(endNext.getDate() + 1);
        const fmt = d => d.toISOString().split("T")[0];
        const dayLabels = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
        const monthLabels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

        const quotationsByBucket = {};
        const ordersByBucket = {};

        try {
            const orders = await this.orm.call("sale.order", "search_read", [
                [["date_order", ">=", fmt(start)], ["date_order", "<", fmt(endNext)]],
                ["date_order", "state"],
            ], { limit: 10000 });
            for (const order of orders) {
                if (!order.date_order) continue;
                const key = period === "year" ? String(order.date_order).slice(0, 7) : String(order.date_order).slice(0, 10);
                if (["sale", "done"].includes(order.state)) {
                    ordersByBucket[key] = (ordersByBucket[key] || 0) + 1;
                } else if (["draft", "sent"].includes(order.state)) {
                    quotationsByBucket[key] = (quotationsByBucket[key] || 0) + 1;
                }
            }
        } catch { /* no sale module */ }

        const labels = [];
        const quotations = [];
        const orders_count = [];

        if (period === "week") {
            for (let i = 0; i < 7; i++) {
                const d = new Date(start);
                d.setDate(start.getDate() + i);
                const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
                labels.push(`${dayLabels[d.getDay()]} ${d.getDate()}`);
                quotations.push(quotationsByBucket[key] || 0);
                orders_count.push(ordersByBucket[key] || 0);
            }
        } else if (period === "month") {
            const daysInMonth = new Date(end.getFullYear(), end.getMonth() + 1, 0).getDate();
            for (let day = 1; day <= daysInMonth; day++) {
                const key = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                labels.push(String(day));
                quotations.push(quotationsByBucket[key] || 0);
                orders_count.push(ordersByBucket[key] || 0);
            }
        } else {
            const cur = new Date(start);
            while (cur <= end) {
                const key = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, "0")}`;
                labels.push(`${monthLabels[cur.getMonth()]} ${cur.getFullYear()}`);
                quotations.push(quotationsByBucket[key] || 0);
                orders_count.push(ordersByBucket[key] || 0);
                cur.setMonth(cur.getMonth() + 1);
            }
        }

        this.state.chartData = { labels, quotations, orders_count, period };
    }

    async _fetchActivities() {
        try {
            this.state.activities = await this.orm.searchRead(
                "mail.activity",
                [["user_id", "=", this.session.uid], ["date_deadline", ">=", new Date().toISOString().split("T")[0]]],
                ["res_name", "summary", "date_deadline"],
                { limit: 5 }
            );
        } catch {
            this.state.activities = [];
        }
    }

    async _fetchGenericBlocks() {
        const genericBlocks = (this.state.layout.blocks || []).filter((block) => (
            ["generic_list", "generic_calendar", "generic_kanban"].includes(block.component)
        ));
        for (const block of genericBlocks) {
            await this._fetchGenericBlock(block);
        }
    }

    async _fetchGenericBlock(block) {
        const config = block.config || {};
        const fields = config.fields?.length ? config.fields : ["display_name"];
        try {
            const records = await this.orm.searchRead(
                block.model,
                this._resolveGenericDomain(config.domain || []),
                fields,
                { limit: config.limit || 5, order: config.date_field ? `${config.date_field} desc` : "id desc" }
            );
            this.state.genericBlockData[block.key] = {
                fields,
                fieldLabels: config.field_labels || {},
                fieldTypes: config.field_types || {},
                records,
                date_field: config.date_field,
            };
        } catch (error) {
            console.warn(`No se pudo cargar el bloque ${block.key}:`, error);
            this.state.genericBlockData[block.key] = {
                fields,
                fieldLabels: config.field_labels || {},
                fieldTypes: config.field_types || {},
                records: [],
                date_field: config.date_field,
            };
        }
    }

    _resolveGenericDomain(domain) {
        const today = new Date().toISOString().split("T")[0];
        return (domain || []).map((term) => (
            Array.isArray(term)
                ? term.map((value) => value === "__today__" ? today : value)
                : term
        ));
    }

    _defaultLayout() {
        return {
            mode: "global",
            can_customize: false,
            can_edit: false,
            can_edit_global: false,
            blocks: [
                { key: "kpi_sales", component: "single_kpi", size: "small", sequence: 10, config: { kpi_key: "sales" } },
                { key: "kpi_orders", component: "single_kpi", size: "small", sequence: 11, config: { kpi_key: "orders" } },
                { key: "kpi_purchase_orders", component: "single_kpi", size: "small", sequence: 12, config: { kpi_key: "purchase_orders" } },
                { key: "kpi_invoiced", component: "single_kpi", size: "small", sequence: 13, config: { kpi_key: "invoiced" } },
                { key: "sales_chart", component: "sales_chart", size: "large", sequence: 20 },
                { key: "order_status", component: "order_status", size: "medium", sequence: 25 },
                { key: "pending_activities", component: "pending_activities", size: "medium", sequence: 30 },
                { key: "top_products", component: "top_products", size: "large", sequence: 40 },
            ],
            available_blocks: [],
        };
    }

    getBlockClass(block) {
        const classesBySize = {
            small: "col-12 col-md-6 col-xl-3",
            medium: "col-12 col-lg-4",
            large: "col-12 col-lg-8",
            full: "col-12",
        };
        return classesBySize[block.size] || classesBySize.medium;
    }

    startLayoutEdition() {
        if (!this.canEditLayout) {
            return;
        }
        this.state.draftBlocks = this._cloneBlocks(this.state.layout.blocks || []);
        this.state.editingLayout = true;
    }

    cancelLayoutEdition() {
        this.state.draftBlocks = [];
        this.state.previewBlock = null;
        this.state.editingLayout = false;
    }

    async saveLayoutEdition() {
        if (!this.canEditLayout) {
            return;
        }
        if (!this.state.draftBlocks.length) {
            return;
        }
        this.state.layout = await this.orm.call(
            "xtd.dashboard.service",
            "save_dashboard_layout",
            [this.state.draftBlocks]
        );
        this.state.draftBlocks = [];
        this.state.previewBlock = null;
        this.state.editingLayout = false;
    }

    moveDashboardBlock(block, direction) {
        const currentIndex = this.state.draftBlocks.findIndex((candidate) => candidate.key === block.key);
        const nextIndex = currentIndex + direction;
        if (currentIndex < 0 || nextIndex < 0 || nextIndex >= this.state.draftBlocks.length) {
            return;
        }
        const blocks = [...this.state.draftBlocks];
        const [movedBlock] = blocks.splice(currentIndex, 1);
        blocks.splice(nextIndex, 0, movedBlock);
        this.state.draftBlocks = blocks;
    }

    resizeDashboardBlock(block, direction) {
        const sizes = ["small", "medium", "large", "full"];
        const currentIndex = sizes.indexOf(block.size || "medium");
        const nextIndex = currentIndex + direction;
        if (nextIndex < 0 || nextIndex >= sizes.length) {
            return;
        }
        this.state.draftBlocks = this.state.draftBlocks.map((candidate) => (
            candidate.key === block.key
                ? { ...candidate, size: sizes[nextIndex] }
                : candidate
        ));
    }

    removeDashboardBlock(block) {
        this.state.draftBlocks = this.state.draftBlocks.filter((candidate) => candidate.key !== block.key);
    }

    addDashboardBlock(block) {
        this.state.draftBlocks = [
            ...this.state.draftBlocks,
            this._cloneBlocks([block])[0],
        ];
        this.state.previewBlock = null;
    }

    getGenericBlockData(block) {
        return this.state.genericBlockData[block.key] || { fields: [], fieldLabels: {}, fieldTypes: {}, records: [] };
    }

    getGenericFieldLabel(block, fieldName) {
        return this.getGenericBlockData(block).fieldLabels[fieldName] || fieldName;
    }

    openGenericRecord(block, record) {
        if (!block.model || !record?.id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: block.model,
            res_id: record.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    formatGenericValue(value, block = null, fieldName = null) {
        if (Array.isArray(value)) {
            return value[1] || "";
        }
        if (value === false || value === null || value === undefined) {
            return "";
        }
        if (this.isMonetaryField(block, fieldName, value)) {
            return this._formatCurrency(value);
        }
        return value;
    }

    isMonetaryField(block, fieldName, value) {
        if (!block || !fieldName || typeof value !== "number") {
            return false;
        }
        const fieldTypes = this.getGenericBlockData(block).fieldTypes || {};
        if (fieldTypes[fieldName] === "monetary") {
            return true;
        }
        return /(^|_)(amount|price|total|subtotal|balance|debit|credit|cost|revenue|margin)(_|$)/.test(fieldName);
    }

    getGenericKanbanTitle(block, record) {
        const fields = this.getGenericBlockData(block).fields || [];
        const titleField = fields[0] || "display_name";
        return this.formatGenericValue(record[titleField], block, titleField) || record.display_name || `#${record.id}`;
    }

    getGenericKanbanDetailFields(block) {
        return (this.getGenericBlockData(block).fields || []).slice(1);
    }

    getFieldType(block, fieldName) {
        if (!block || !fieldName) return "";
        const types = this.getGenericBlockData(block).fieldTypes || {};
        return types[fieldName] || "";
    }

    getFieldClass(block, fieldName) {
        const type = this.getFieldType(block, fieldName);
        if (type === "selection") return "xtd-field-badge";
        if (type === "monetary") return "xtd-field-monetary";
        if (type === "many2one") return "xtd-field-partner";
        if (["float", "integer"].includes(type)) return "xtd-field-numeric";
        if (["date", "datetime"].includes(type)) return "xtd-field-date";
        return "";
    }

    getStateClass(value) {
        if (!value) return "";
        const raw = Array.isArray(value) ? String(value[0] || "") : String(value);
        const v = raw.toLowerCase();
        if (["draft", "new", "open"].includes(v)) return "xtd-state-draft";
        if (["sent", "waiting", "pending"].includes(v)) return "xtd-state-pending";
        if (["sale", "done", "paid", "posted", "confirmed", "purchase"].includes(v)) return "xtd-state-done";
        if (["cancel", "cancelled", "rejected"].includes(v)) return "xtd-state-cancel";
        if (["close", "closed"].includes(v)) return "xtd-state-closed";
        return "";
    }

    isFirstField(block, fieldName) {
        const fields = this.getGenericBlockData(block).fields || [];
        return fields[0] === fieldName;
    }

    getListAccentColor(index) {
        const colors = ["sales", "orders", "invoiced", "purchase_orders", "info", "success", "warning", "danger"];
        return colors[(index || 0) % colors.length];
    }

    async openBlockBuilder() {
        this.state.showBlockBuilder = true;
        this.state.newBlock = this._defaultNewBlock();
        this.state.builderOptions = await this.orm.call(
            "xtd.dashboard.service",
            "get_block_builder_options",
            [false]
        );
    }

    async previewDashboardBlock(block) {
        this.state.previewBlock = this._cloneBlocks([block])[0];
        if (["generic_list", "generic_calendar", "generic_kanban"].includes(block.component)) {
            await this._fetchGenericBlock(block);
        }
    }

    isBlockPreviewed(block) {
        return this.state.previewBlock?.key === block.key;
    }

    getBlockComponentLabel(block) {
        const labels = {
            generic_list: "Lista",
            generic_kanban: "Kanban",
            generic_calendar: "Calendario",
            main_kpis: "KPIs",
            single_kpi: "KPI",
            sales_chart: "Gráfico",
            pending_activities: "Lista",
            top_products: "Ranking",
            order_status: "Estado",
        };
        return labels[block.component] || block.type || "Bloque";
    }

    closeBlockBuilder() {
        this.state.showBlockBuilder = false;
    }

    onNewBlockAppChange(event) {
        this.state.newBlock.app = event.target.value;
        this.state.newBlock.model = "";
        this.state.newBlock.selectedFields = [];
        this.state.newBlock.date_field = "";
        this.state.builderOptions.fields = [];
    }

    async onNewBlockModelChange(event) {
        this.state.newBlock.model = event.target.value;
        this.state.newBlock.selectedFields = [];
        this.state.newBlock.date_field = "";
        if (!this.state.newBlock.model) {
            this.state.builderOptions.fields = [];
            return;
        }
        this.state.builderOptions = await this.orm.call(
            "xtd.dashboard.service",
            "get_block_builder_options",
            [this.state.newBlock.model]
        );
        this.state.newBlock.selectedFields = this.state.builderOptions.fields
            .slice(0, 4)
            .map((field) => field.name);
    }

    toggleNewBlockField(fieldName) {
        const selectedFields = this.state.newBlock.selectedFields || [];
        this.state.newBlock.selectedFields = selectedFields.includes(fieldName)
            ? selectedFields.filter((selectedField) => selectedField !== fieldName)
            : [...selectedFields, fieldName];
    }

    isNewBlockFieldSelected(fieldName) {
        return (this.state.newBlock.selectedFields || []).includes(fieldName);
    }

    async createCustomBlock() {
        if (!this.state.newBlock.name || !this.state.newBlock.model) {
            return;
        }
        this.state.layout = await this.orm.call(
            "xtd.dashboard.service",
            "create_custom_block",
            [{
                ...this.state.newBlock,
                fields: this.state.newBlock.selectedFields,
            }]
        );
        await this._fetchGenericBlocks();
        this.state.draftBlocks = this._cloneBlocks(this.state.layout.blocks || []);
        this.state.showBlockBuilder = false;
        this.state.newBlock = this._defaultNewBlock();
    }

    async deleteCustomBlock(block) {
        if (!block.can_delete) {
            return;
        }
        const confirmed = window.confirm(`¿Eliminar definitivamente el bloque "${block.name}"?`);
        if (!confirmed) {
            return;
        }
        this.state.layout = await this.orm.call(
            "xtd.dashboard.service",
            "delete_custom_block",
            [block.block_id]
        );
        await this._fetchGenericBlocks();
        this.state.draftBlocks = this._cloneBlocks(this.state.layout.blocks || []);
    }

    _cloneBlocks(blocks) {
        return blocks.map((block) => ({
            ...block,
            config: { ...(block.config || {}) },
        }));
    }

    _defaultNewBlock() {
        return {
            name: "",
            block_type: "generic_list",
            app: "",
            model: "",
            selectedFields: [],
            date_field: "",
            limit: 5,
            size: "medium",
        };
    }

    async _fetchTopProducts() {
        const period = this.state.topPeriod || "month";
        const { curStart, endNext } = this._kpiPeriodRanges(period);
        const fmt = d => d.toISOString().split("T")[0];
        const toNum = (v) => { const n = Number(v); return isNaN(n) ? 0 : n; };

        try {
            const data = await this.orm.call(
                "sale.order.line",
                "read_group",
                [
                    [
                        ["state", "in", ["sale", "done"]],
                        ["product_id", "!=", false],
                        ["order_id.date_order", ">=", fmt(curStart)],
                        ["order_id.date_order", "<", fmt(endNext)],
                    ],
                    ["product_id", "product_uom_qty:sum", "price_subtotal:sum"],
                    ["product_id"]
                ],
                { limit: 5, orderby: "product_uom_qty desc" }
            );

            const products = data.map(item => ({
                id: item.product_id[0],
                name: item.product_id[1],
                qty: Math.round(toNum(item.product_uom_qty)),
                amount: toNum(item.price_subtotal),
            }));

            const maxQty = products.reduce((max, p) => Math.max(max, p.qty), 0);
            this.state.topProducts = products.map(p => ({
                ...p,
                amountFmt: this._formatCurrency(p.amount),
                barWidth: maxQty > 0 ? (p.qty / maxQty) * 100 : 0,
            }));
        } catch (e) {
            console.warn("No se pudo cargar top productos:", e);
            this.state.topProducts = [];
        }
    }

    async _fetchOrderStatus() {
        try {
            const states = ["draft", "sent", "sale", "done", "cancel"];
            const results = await Promise.all(states.map(s =>
                this.orm.call("sale.order", "search_count", [[["state", "=", s]]])
            ));
            this.state.orderStatus = states
                .map((state, i) => ({ state, count: results[i] }))
                .filter(item => item.count > 0)
                .map(item => ({
                    state: item.state,
                    count: item.count,
                    label: this._getOrderStateLabel(item.state)
                }));
        } catch (e) {
            console.warn("No se pudo cargar estado de pedidos:", e);
        }
    }

    get donutTotal() {
        return this.state.orderStatus.reduce((sum, s) => sum + (s.count || 0), 0);
    }

    get kpiPeriodLabel() {
        const labels = { week: "vs semana anterior", month: "vs mes anterior", year: "vs año anterior" };
        return labels[this.state.kpiPeriod] || "vs periodo anterior";
    }

    _formatKpis(kpis) {
        const toNum = (v) => { const n = Number(v); return isNaN(n) ? 0 : n; };
        const formatCurrency = (val) => val ? this._formatCurrency(val) : "0 €";
        const salesVal = toNum(kpis.sales?.value);
        const invoicedTotal = toNum(kpis.invoiced?.total);
        const ticketMedio = salesVal > 0 ? this._formatCurrency(invoicedTotal / salesVal) : "—";
        return {
            sales: {
                value: salesVal.toString(),
                total: formatCurrency(toNum(kpis.sales?.total)),
                trend: toNum(kpis.sales?.trend),
                trend_str: this._formatTrend(kpis.sales?.trend),
                label: kpis.sales?.label || "Pedidos venta",
                icon: "fa-shopping-bag",
                ticket_medio: ticketMedio,
            },
            orders: {
                value: toNum(kpis.orders?.value).toString(),
                total: formatCurrency(toNum(kpis.orders?.total)),
                trend: toNum(kpis.orders?.trend),
                trend_str: this._formatTrend(kpis.orders?.trend),
                label: kpis.orders?.label || "Presupuestos",
                icon: "fa-file-text-o",
            },
            purchase_orders: {
                value: toNum(kpis.purchase_orders?.value).toString(),
                total: formatCurrency(toNum(kpis.purchase_orders?.total)),
                trend: toNum(kpis.purchase_orders?.trend),
                trend_str: this._formatTrend(kpis.purchase_orders?.trend),
                label: kpis.purchase_orders?.label || "Pedidos de compra",
                icon: "fa-truck",
            },
            invoiced: {
                value: toNum(kpis.invoiced?.value).toString(),
                total: formatCurrency(toNum(kpis.invoiced?.total)),
                trend: toNum(kpis.invoiced?.trend),
                trend_str: this._formatTrend(kpis.invoiced?.trend),
                label: kpis.invoiced?.label || "Facturado (mes)",
                icon: "fa-file-text-o",
            },
        };
    }

    _formatTrend(trend) {
        if (trend === undefined || trend === null) return "0%";
        const sign = trend >= 0 ? "+" : "";
        return `${sign}${trend}%`;
    }

    _renderCharts() {
        if (!Chart) return;
        this._renderSalesChart();
        this._renderOrderStatusChart();
    }

    _renderSalesChart() {
        const canvas = this.salesChartRef?.el;
        const data = this.state.chartData;

        if (this._chartInstances.sales) {
            if (!canvas) {
                this._chartInstances.sales.destroy();
                delete this._chartInstances.sales;
                return;
            }
            if (data?.labels?.length) {
                this._chartInstances.sales.data.labels = data.labels;
                this._chartInstances.sales.data.datasets[0].data = data.quotations;
                this._chartInstances.sales.data.datasets[1].data = data.orders_count;
                this._chartInstances.sales.update();
            }
            return;
        }

        if (!canvas || !data?.labels?.length) return;
        const ctx = canvas.getContext("2d");

        const gradient = ctx.createLinearGradient(0, 0, 200, 0);
        gradient.addColorStop(0, "rgba(255, 122, 0, 0.25)");
        gradient.addColorStop(1, "rgba(255, 122, 0, 0)");

        const rawData = this.state.chartData;

        this._chartInstances.sales = new Chart(ctx, {
            type: "line",
            data: {
                labels: rawData.labels,
                datasets: [
                    {
                        label: "Presupuestos",
                        data: rawData.quotations,
                        borderColor: "#FFC107",
                        backgroundColor: "rgba(255, 193, 7, 0.08)",
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: "#FFC107",
                        pointBorderColor: "#fff",
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        borderDash: [5, 3],
                    },
                    {
                        label: "Pedidos de venta",
                        data: rawData.orders_count,
                        borderColor: "#6464FF",
                        backgroundColor: "rgba(100, 100, 255, 0.08)",
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: "#6464FF",
                        pointBorderColor: "#fff",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "top",
                        align: "end",
                        labels: { usePointStyle: true, boxWidth: 8, padding: 16, font: { size: 11 } },
                    },
                    tooltip: {
                        backgroundColor: "#151515",
                        titleFont: { size: 12 },
                        bodyFont: { size: 11 },
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 10 }, color: "#8b8790" },
                    },
                    y: {
                        position: "left",
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: {
                            font: { size: 10 },
                            color: "#8b8790",
                            precision: 0,
                        },
                    },
                },
            },
        });
    }

    _renderOrderStatusChart() {
        const canvas = this.orderStatusChartRef?.el;
        const statuses = this.state.orderStatus;

        if (this._chartInstances.orderStatus) {
            if (!canvas) {
                this._chartInstances.orderStatus.destroy();
                delete this._chartInstances.orderStatus;
                return;
            }
            if (statuses?.length) {
                const statusColors = { sale: "#FF7A00", sent: "#6464FF", draft: "#FFC107", cancel: "#DC3545", done: "#28A745" };
                this._chartInstances.orderStatus.data.labels = statuses.map((s) => s.label);
                this._chartInstances.orderStatus.data.datasets[0].data = statuses.map((s) => s.count);
                this._chartInstances.orderStatus.data.datasets[0].backgroundColor = statuses.map((s) => statusColors[s.state] || "#6c757d");
                this._chartInstances.orderStatus.update();
            }
            return;
        }

        if (!canvas || !statuses?.length) return;
        const ctx = canvas.getContext("2d");

        const statusColors = { sale: "#FF7A00", sent: "#6464FF", draft: "#FFC107", cancel: "#DC3545", done: "#28A745" };

        this._chartInstances.orderStatus = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: statuses.map((s) => s.label),
                datasets: [{
                    data: statuses.map((s) => s.count),
                    backgroundColor: statuses.map((s) => statusColors[s.state] || "#6c757d"),
                    borderColor: "#fff",
                    borderWidth: 3,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#151515",
                        titleFont: { size: 12 },
                        bodyFont: { size: 12, weight: "bold" },
                        padding: 10,
                        cornerRadius: 8,
                        z: 9999,
                        callbacks: {
                            label: (ctx) => ` ${ctx.parsed} pedidos`,
                        },
                    },
                },
            },
        });
    }

    _destroyCharts() {
        Object.values(this._chartInstances).forEach((chart) => {
            if (chart) chart.destroy();
        });
        this._chartInstances = {};
    }

    _getOrderStateLabel(state) {
        const labels = {
            'draft': 'Presupuesto',
            'sent': 'Enviado',
            'sale': 'Pedido de venta',
            'done': 'Bloqueado',
            'cancel': 'Cancelado'
        };
        return labels[state] || state;
    }

    _formatCurrency(amount) {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(amount);
    }

    openAction(xmlid) {
        this.action.doAction(xmlid);
    }

    getKpiCreateTitle(key) {
        const labels = {
            sales: "Crear pedido de venta",
            orders: "Crear presupuesto",
            purchase_orders: "Crear compra",
            invoiced: "Crear factura",
        };
        return labels[key] || "Crear";
    }

    createKpiRecord(key) {
        const actions = {
            sales: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "form"]],
                target: "current",
                context: {},
                name: "Ventas",
            },
            orders: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "form"]],
                target: "current",
                context: {},
                name: "Ventas",
            },
            purchase_orders: {
                type: "ir.actions.act_window",
                res_model: "purchase.order",
                views: [[false, "form"]],
                target: "current",
                context: {},
                name: "Compras",
            },
            invoiced: {
                type: "ir.actions.act_window",
                res_model: "account.move",
                views: [[false, "form"]],
                target: "current",
                context: { default_move_type: "out_invoice" },
                name: "Facturación",
            },
        }[key];
        if (actions) {
            this.action.doAction(actions, { clearBreadcrumbs: true });
        }
    }

    onKpiClick(key) {
        const actions = {
            sales: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "list"], [false, "form"]],
                domain: [["state", "in", ["sale", "done"]]],
                name: "Pedidos venta",
            },
            orders: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "list"], [false, "form"]],
                domain: [["state", "in", ["draft", "sent"]]],
                name: "Presupuestos",
            },
            purchase_orders: {
                type: "ir.actions.act_window",
                res_model: "purchase.order",
                views: [[false, "list"], [false, "form"]],
                domain: [["state", "in", ["purchase", "done"]]],
                name: "Compras",
            },
            invoiced: {
                type: "ir.actions.act_window",
                res_model: "account.move",
                views: [[false, "list"], [false, "form"]],
                domain: [["move_type", "=", "out_invoice"], ["state", "=", "posted"]],
                name: "Facturado",
            },
        }[key];
        if (actions) {
            this.action.doAction(actions, { clearBreadcrumbs: true });
        }
    }
}

registry.category("actions").add("xtendoo_xtd_theme.dashboard", XtdDashboard);
