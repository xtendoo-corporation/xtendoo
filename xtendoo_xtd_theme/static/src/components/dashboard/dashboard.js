import { Component, onWillStart, onMounted, onWillDestroy, onPatched, useState, useRef } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { loadBundle } from "@web/core/assets";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

// Las fechas del dashboard se calculan en hora local del usuario. Nunca usar
// toISOString(): convierte a UTC y, en zonas con offset positivo (España),
// medianoche local cae en el día anterior.
const pad2 = (n) => String(n).padStart(2, "0");
const toLocalDate = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
// Campos datetime (UTC en servidor): medianoche local -> datetime UTC.
const toUtcDateTime = (d) => serializeDateTime(DateTime.fromJSDate(d).startOf("day"));

export class XtdDashboard extends Component {
    static template = "xtendoo_xtd_theme.XtdDashboard";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.session = session;
        this.userFirstName = (user.name || "").split(" ")[0];

        this.currencyCode = session.currency_code || "EUR";
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
            draggingKey: null,
            dropTargetKey: null,
            dropPosition: "before",
            dropVertical: false,
            genericBlockData: {},
            isSidebarHidden: document.body.classList.contains("xtd-sidebar-hidden"),
            chartPeriod: "year",
            kpiPeriod: "month",
            topPeriod: "month",
            recentItems: { sales: [], orders: [], purchase_orders: [], invoiced: [] },
        });

        // Aviso nativo del navegador si se cierra o recarga con cambios sin guardar.
        useExternalListener(window, "beforeunload", (ev) => {
            if (this.isLayoutDirty) {
                ev.preventDefault();
                ev.returnValue = "";
            }
        });

        useBus(this.env.bus, "XTD_SIDEBAR:TOGGLE", () => {
            this.state.isSidebarHidden = document.body.classList.contains("xtd-sidebar-hidden");
        });

        onWillStart(async () => {
            // Chart.js (~200 KB) solo se descarga al abrir el dashboard.
            await Promise.all([
                loadBundle("xtendoo_xtd_theme.chartjs").catch((error) => {
                    console.warn("No se pudo cargar Chart.js:", error);
                }),
                this._fetchData(),
            ]);
        });

        onMounted(() => {
            this._renderCharts();
        });

        onPatched(() => {
            this._playFlip();
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
        if (this.state.editingLayout) {
            return this.state.draftBlocks;
        }
        return (this.state.layout.blocks || []).filter((block) => !block.config?.hidden);
    }
    get canEditLayout() { return !!this.state.layout.can_edit; }
    get editingLayout() { return this.state.editingLayout; }
    get isSidebarHidden() { return this.state.isSidebarHidden; }
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
                this._fetchSummary(),
                this._fetchChartData(),
                this._fetchActivities(),
                this._fetchTopProducts(),
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

    // null = no hay comparación significativa (periodo en curso sin datos): se
    // muestra "sin datos" en lugar de un -100% que alarma sin aportar nada.
    _calcTrend(current, previous) {
        if (!current) return null;
        if (!previous) return 100.0;
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
        await this._fetchSummary();
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

    async _fetchSummary() {
        try {
            const summary = await this.orm.call(
                "xtd.dashboard.service",
                "get_dashboard_summary",
                [this.state.kpiPeriod || "month"]
            );
            this.currencyCode = summary.currency || this.currencyCode;
            const labels = {
                sales: _t("Pedidos venta"),
                orders: _t("Presupuestos"),
                purchase_orders: _t("Compras"),
                invoiced: _t("Facturado"),
            };
            const icons = {
                sales: "fa-shopping-bag",
                orders: "fa-file-text-o",
                purchase_orders: "fa-truck",
                invoiced: "fa-file-text-o",
            };
            const kpis = {};
            for (const [key, kpi] of Object.entries(summary.kpis)) {
                kpis[key] = { ...kpi, label: labels[key], icon: icons[key] };
                const trendValue = key === "invoiced" ? kpi.total : kpi.value;
                const previousValue = key === "invoiced" ? kpi.previous_total : kpi.previous_value;
                kpis[key].trend = this._calcTrend(trendValue, previousValue);
            }
            this.state.statistics = this._formatKpis(kpis);
            this.state.recentItems = summary.recent;
            this.state.orderStatus = summary.order_status;
        } catch (error) {
            console.warn("No se pudo cargar el resumen del dashboard:", error);
            this.state.statistics = this._formatKpis({});
            this.state.recentItems = { sales: [], orders: [], purchase_orders: [], invoiced: [] };
            this.state.orderStatus = [];
        }
    }

    async _fetchChartData() {
        const period = this.state.chartPeriod || "year";
        const { start, end } = this._getPeriodRange(period);
        const endNext = new Date(end);
        endNext.setDate(endNext.getDate() + 1);
        const fmt = toUtcDateTime;

        const quotationsByBucket = {};
        const ordersByBucket = {};

        try {
            const orders = await this.orm.call("sale.order", "search_read", [
                [["date_order", ">=", fmt(start)], ["date_order", "<", fmt(endNext)]],
                ["date_order", "state"],
            ], { limit: 10000 });
            for (const order of orders) {
                if (!order.date_order) continue;
                // date_order viene en UTC: se pasa a hora local antes de agrupar.
                const localOrderDate = deserializeDateTime(order.date_order);
                const key = localOrderDate.toFormat(period === "year" ? "yyyy-MM" : "yyyy-MM-dd");
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
                labels.push(DateTime.fromJSDate(d).toFormat("ccc d"));
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
                labels.push(DateTime.fromJSDate(cur).toFormat("LLL yyyy"));
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
                [["user_id", "=", this.session.uid], ["date_deadline", ">=", toLocalDate(new Date())]],
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
        const today = toLocalDate(new Date());
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
        };
    }

    getBlockClass(block) {
        const classesBySize = {
            small: "col-12 col-md-6 col-xl-3",
            medium: "col-12 col-lg-4",
            large: "col-12 col-lg-8",
            full: "col-12",
        };
        let classes = classesBySize[block.size] || classesBySize.medium;
        if (block.config?.hidden) {
            classes += " xtd-dashboard-block-hidden";
        }
        if (this.state.draggingKey === block.key) {
            classes += " xtd-dashboard-block-dragging";
        }
        if (this.state.dropTargetKey === block.key && this.state.draggingKey !== block.key) {
            classes += ` xtd-dashboard-block-drop-${this.state.dropPosition}`;
            if (this.state.dropVertical) {
                classes += " xtd-dashboard-block-drop-vertical";
            }
        }
        return classes;
    }

    startLayoutEdition() {
        if (!this.canEditLayout) {
            return;
        }
        this.state.draftBlocks = this._cloneBlocks(this.state.layout.blocks || []);
        this.state.editingLayout = true;
    }

    // Orden, tamaño y visibilidad: lo único que el usuario puede cambiar.
    _layoutSignature(blocks) {
        return JSON.stringify((blocks || []).map((block) => [
            block.key,
            block.size || "medium",
            !!block.config?.hidden,
        ]));
    }

    get isLayoutDirty() {
        return this.state.editingLayout
            && this._layoutSignature(this.state.draftBlocks) !== this._layoutSignature(this.state.layout.blocks);
    }

    _closeLayoutEdition() {
        this.state.draftBlocks = [];
        this.state.draggingKey = null;
        this.state.dropTargetKey = null;
        this.state.editingLayout = false;
    }

    cancelLayoutEdition() {
        if (!this.isLayoutDirty) {
            this._closeLayoutEdition();
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Cambios sin guardar"),
            body: _t("Si cancelas se perderán los cambios hechos en el dashboard."),
            confirmLabel: _t("Descartar cambios"),
            confirm: () => this._closeLayoutEdition(),
            cancelLabel: _t("Seguir editando"),
            cancel: () => {},
        });
    }

    onBlockDragStart(ev, block) {
        this.state.draggingKey = block.key;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", block.key);
        const blockEl = ev.target.closest("[data-block-key]");
        if (blockEl) {
            ev.dataTransfer.setDragImage(blockEl, 20, 20);
        }
    }

    /**
     * Calcula dónde caería el bloque arrastrado: el bloque más cercano al
     * cursor (también en los huecos entre bloques) y si va delante o detrás.
     * Con bloques que ocupan casi toda la fila se decide por la mitad
     * vertical; con bloques más estrechos, por la mitad horizontal.
     */
    _computeDrop(ev) {
        const container = ev.currentTarget;
        const containerWidth = container.getBoundingClientRect().width || 1;
        let best = null;
        for (const el of container.querySelectorAll("[data-block-key]")) {
            const key = el.dataset.blockKey;
            if (key === this.state.draggingKey) {
                continue;
            }
            const rect = el.getBoundingClientRect();
            const dx = Math.max(rect.left - ev.clientX, 0, ev.clientX - rect.right);
            const dy = Math.max(rect.top - ev.clientY, 0, ev.clientY - rect.bottom);
            const distance = Math.hypot(dx, dy);
            if (!best || distance < best.distance) {
                best = { key, rect, distance };
            }
        }
        if (!best) {
            return null;
        }
        const vertical = best.rect.width >= containerWidth * 0.7;
        const after = vertical
            ? ev.clientY > best.rect.top + best.rect.height / 2
            : ev.clientX > best.rect.left + best.rect.width / 2;
        return { key: best.key, position: after ? "after" : "before", vertical };
    }

    _autoScroll(ev) {
        const scroller = ev.currentTarget.closest(".overflow-auto");
        if (!scroller) {
            return;
        }
        const rect = scroller.getBoundingClientRect();
        if (ev.clientY < rect.top + 80) {
            scroller.scrollTop -= 20;
        } else if (ev.clientY > rect.bottom - 80) {
            scroller.scrollTop += 20;
        }
    }

    onBlocksDragOver(ev) {
        if (!this.state.draggingKey) {
            return;
        }
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        this._autoScroll(ev);
        const drop = this._computeDrop(ev);
        this.state.dropTargetKey = drop?.key || null;
        this.state.dropPosition = drop?.position || "before";
        this.state.dropVertical = !!drop?.vertical;
    }

    onBlocksDrop(ev) {
        const draggingKey = this.state.draggingKey;
        const drop = draggingKey && this._computeDrop(ev);
        if (drop) {
            ev.preventDefault();
            const blocks = this.state.draftBlocks.filter((block) => block.key !== draggingKey);
            const moved = this.state.draftBlocks.find((block) => block.key === draggingKey);
            const targetIndex = blocks.findIndex((block) => block.key === drop.key);
            if (moved && targetIndex >= 0) {
                blocks.splice(drop.position === "after" ? targetIndex + 1 : targetIndex, 0, moved);
                const changed = blocks.some((block, i) => block.key !== this.state.draftBlocks[i].key);
                if (changed) {
                    this._flipRects = this._captureBlockRects(ev.currentTarget);
                    this.state.draftBlocks = blocks;
                }
            }
        }
        this.onBlockDragEnd();
    }

    _captureBlockRects(container) {
        const rects = new Map();
        for (const el of container.querySelectorAll("[data-block-key]")) {
            rects.set(el.dataset.blockKey, el.getBoundingClientRect());
        }
        return rects;
    }

    /** Animación FLIP: los bloques se deslizan de su sitio anterior al nuevo. */
    _playFlip() {
        const before = this._flipRects;
        this._flipRects = null;
        if (!before) {
            return;
        }
        for (const el of document.querySelectorAll(".o_xtd_dashboard [data-block-key]")) {
            const old = before.get(el.dataset.blockKey);
            if (!old) {
                continue;
            }
            const now = el.getBoundingClientRect();
            const dx = old.left - now.left;
            const dy = old.top - now.top;
            if (dx || dy) {
                el.animate(
                    [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }],
                    { duration: 250, easing: "ease-out" }
                );
            }
        }
    }

    onBlockDragEnd() {
        this.state.draggingKey = null;
        this.state.dropTargetKey = null;
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
        this._closeLayoutEdition();
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

    toggleBlockHidden(block) {
        this.state.draftBlocks = this.state.draftBlocks.map((candidate) => (
            candidate.key === block.key
                ? { ...candidate, config: { ...(candidate.config || {}), hidden: !candidate.config?.hidden } }
                : candidate
        ));
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

    deleteCustomBlock(block) {
        if (!block.can_delete) {
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Eliminar bloque"),
            body: _t('¿Eliminar definitivamente el bloque "%s"?', block.name),
            confirmLabel: _t("Eliminar"),
            confirm: async () => {
                this.state.layout = await this.orm.call(
                    "xtd.dashboard.service",
                    "delete_custom_block",
                    [block.block_id]
                );
                await this._fetchGenericBlocks();
                this.state.draftBlocks = this._cloneBlocks(this.state.layout.blocks || []);
            },
            cancel: () => {},
        });
    }

    _cloneBlocks(blocks) {
        return blocks.map((block) => ({
            ...block,
            config: { ...(block.config || {}) },
        }));
    }

    async _fetchTopProducts() {
        const period = this.state.topPeriod || "month";
        const { curStart, endNext } = this._kpiPeriodRanges(period);
        const fmt = toUtcDateTime;
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

    // Métricas del mismo periodo que el gráfico (no las del mes de las tarjetas).
    get chartSummary() {
        const data = this.state.chartData;
        const quotations = (data?.quotations || []).reduce((a, b) => a + b, 0);
        const orders = (data?.orders_count || []).reduce((a, b) => a + b, 0);
        const total = quotations + orders;
        return {
            quotations,
            orders,
            conversion: total ? `${Math.round((orders / total) * 100)}%` : "—",
        };
    }

    get donutTotal() {
        return this.state.orderStatus.reduce((sum, s) => sum + (s.count || 0), 0);
    }

    get kpiPeriodLabel() {
        const labels = { week: _t("vs semana anterior"), month: _t("vs mes anterior"), year: _t("vs año anterior") };
        return labels[this.state.kpiPeriod] || _t("vs periodo anterior");
    }

    _formatKpis(kpis) {
        const toNum = (v) => { const n = Number(v); return isNaN(n) ? 0 : n; };
        const formatCurrency = (val) => this._formatCurrency(val || 0);
        const salesVal = toNum(kpis.sales?.value);
        const invoicedTotal = toNum(kpis.invoiced?.total);
        const ticketMedio = salesVal > 0 ? this._formatCurrency(invoicedTotal / salesVal) : "—";
        return {
            sales: {
                value: salesVal.toString(),
                total: formatCurrency(toNum(kpis.sales?.total)),
                trend: toNum(kpis.sales?.trend),
                hasTrend: kpis.sales?.trend !== null && kpis.sales?.trend !== undefined,
                trend_str: this._formatTrend(kpis.sales?.trend),
                label: kpis.sales?.label || "Pedidos venta",
                icon: "fa-shopping-bag",
                ticket_medio: ticketMedio,
            },
            orders: {
                value: toNum(kpis.orders?.value).toString(),
                total: formatCurrency(toNum(kpis.orders?.total)),
                trend: toNum(kpis.orders?.trend),
                hasTrend: kpis.orders?.trend !== null && kpis.orders?.trend !== undefined,
                trend_str: this._formatTrend(kpis.orders?.trend),
                label: kpis.orders?.label || "Presupuestos",
                icon: "fa-file-text-o",
            },
            purchase_orders: {
                value: toNum(kpis.purchase_orders?.value).toString(),
                total: formatCurrency(toNum(kpis.purchase_orders?.total)),
                trend: toNum(kpis.purchase_orders?.trend),
                hasTrend: kpis.purchase_orders?.trend !== null && kpis.purchase_orders?.trend !== undefined,
                trend_str: this._formatTrend(kpis.purchase_orders?.trend),
                label: kpis.purchase_orders?.label || "Pedidos de compra",
                icon: "fa-truck",
            },
            invoiced: {
                value: toNum(kpis.invoiced?.value).toString(),
                total: formatCurrency(toNum(kpis.invoiced?.total)),
                trend: toNum(kpis.invoiced?.trend),
                hasTrend: kpis.invoiced?.trend !== null && kpis.invoiced?.trend !== undefined,
                trend_str: this._formatTrend(kpis.invoiced?.trend),
                label: kpis.invoiced?.label || "Facturado (mes)",
                icon: "fa-file-text-o",
            },
        };
    }

    _formatTrend(trend) {
        if (trend === undefined || trend === null) return "—";
        const sign = trend >= 0 ? "+" : "";
        return `${sign}${trend}%`;
    }

    _cssVar(name, fallback) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    }

    _renderCharts() {
        if (!window.Chart) return;
        this._renderSalesChart();
        this._renderOrderStatusChart();
    }

    _renderSalesChart() {
        const Chart = window.Chart;
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
        const rawData = this.state.chartData;
        const orange = this._cssVar("--xtd-orange", "#f45700");
        const muted = this._cssVar("--xtd-muted", "#8b8790");
        const line = this._cssVar("--xtd-line", "#dedbd6");

        // Barras agrupadas: con pocos datos una curva suavizada inventa picos y valles.
        this._chartInstances.sales = new Chart(ctx, {
            type: "bar",
            data: {
                labels: rawData.labels,
                datasets: [
                    {
                        label: _t("Presupuestos"),
                        data: rawData.quotations,
                        backgroundColor: "rgba(244, 87, 0, 0.28)",
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                    {
                        label: _t("Pedidos de venta"),
                        data: rawData.orders_count,
                        backgroundColor: orange,
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                categoryPercentage: 0.75,
                barPercentage: 0.9,
                maxBarThickness: 22,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "top",
                        align: "end",
                        labels: { usePointStyle: true, pointStyle: "rectRounded", boxWidth: 8, padding: 16, font: { size: 11 }, color: muted },
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
                        border: { display: false },
                        ticks: { font: { size: 10 }, color: muted },
                    },
                    y: {
                        position: "left",
                        beginAtZero: true,
                        border: { display: false },
                        grid: { color: line },
                        ticks: { font: { size: 10 }, color: muted, precision: 0 },
                    },
                },
            },
        });
    }

    _renderOrderStatusChart() {
        const Chart = window.Chart;
        const canvas = this.orderStatusChartRef?.el;
        const statuses = this.state.orderStatus;

        if (this._chartInstances.orderStatus) {
            if (!canvas) {
                this._chartInstances.orderStatus.destroy();
                delete this._chartInstances.orderStatus;
                return;
            }
            if (statuses?.length) {
                const statusColors = { sale: "#f45700", sent: "#8b6f9c", draft: "#f4b183", cancel: "#c0392b", done: "#2f9e6e" };
                this._chartInstances.orderStatus.data.labels = statuses.map((s) => s.label);
                this._chartInstances.orderStatus.data.datasets[0].data = statuses.map((s) => s.count);
                this._chartInstances.orderStatus.data.datasets[0].backgroundColor = statuses.map((s) => statusColors[s.state] || "#6c757d");
                this._chartInstances.orderStatus.update();
            }
            return;
        }

        if (!canvas || !statuses?.length) return;
        const ctx = canvas.getContext("2d");

        const statusColors = { sale: "#f45700", sent: "#8b6f9c", draft: "#f4b183", cancel: "#c0392b", done: "#2f9e6e" };

        this._chartInstances.orderStatus = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: statuses.map((s) => s.label),
                datasets: [{
                    data: statuses.map((s) => s.count),
                    backgroundColor: statuses.map((s) => statusColors[s.state] || "#6c757d"),
                    borderColor: getComputedStyle(canvas.closest(".card") || canvas).backgroundColor,
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
                            label: (ctx) => ` ${ctx.parsed} ${_t("pedidos")}`,
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

    _formatCurrency(amount) {
        const locale = (user.lang || "es_ES").replace("_", "-");
        return new Intl.NumberFormat(locale, { style: "currency", currency: this.currencyCode }).format(amount);
    }

    openAction(xmlid) {
        this.action.doAction(xmlid);
    }

    getKpiCreateTitle(key) {
        const labels = {
            sales: _t("Crear pedido de venta"),
            orders: _t("Crear presupuesto"),
            purchase_orders: _t("Crear compra"),
            invoiced: _t("Crear factura"),
        };
        return labels[key] || _t("Crear");
    }

    createKpiRecord(key) {
        const actions = {
            sales: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "form"]],
                target: "current",
                context: {},
                name: _t("Ventas"),
            },
            orders: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "form"]],
                target: "current",
                context: {},
                name: _t("Ventas"),
            },
            purchase_orders: {
                type: "ir.actions.act_window",
                res_model: "purchase.order",
                views: [[false, "form"]],
                target: "current",
                context: {},
                name: _t("Compras"),
            },
            invoiced: {
                type: "ir.actions.act_window",
                res_model: "account.move",
                views: [[false, "form"]],
                target: "current",
                context: { default_move_type: "out_invoice" },
                name: _t("Facturación"),
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
                name: _t("Pedidos venta"),
            },
            orders: {
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "list"], [false, "form"]],
                domain: [["state", "in", ["draft", "sent"]]],
                name: _t("Presupuestos"),
            },
            purchase_orders: {
                type: "ir.actions.act_window",
                res_model: "purchase.order",
                views: [[false, "list"], [false, "form"]],
                domain: [["state", "in", ["purchase", "done"]]],
                name: _t("Compras"),
            },
            invoiced: {
                type: "ir.actions.act_window",
                res_model: "account.move",
                views: [[false, "list"], [false, "form"]],
                domain: [["move_type", "=", "out_invoice"], ["state", "=", "posted"]],
                name: _t("Facturado"),
            },
        }[key];
        if (actions) {
            this.action.doAction(actions, { clearBreadcrumbs: true });
        }
    }
}

registry.category("actions").add("xtendoo_xtd_theme.dashboard", XtdDashboard);
