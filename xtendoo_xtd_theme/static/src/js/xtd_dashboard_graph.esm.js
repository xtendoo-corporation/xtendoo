import { patch } from "@web/core/utils/patch";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

function themeColor(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

function withAlpha(color, alpha) {
    const probe = document.createElement("canvas").getContext("2d");
    probe.fillStyle = color;
    const hex = probe.fillStyle; // "#rrggbb"
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Colores del tema sobre la configuración que ya calculó Odoo. Se aplica en
 * getChartConfig (y no en getBarChartConfig) para cubrir también a los gráficos
 * que heredan del de diarios (inventario, fabricación...) sin depender de sus
 * módulos.
 */
function recolor(field, config) {
    const orange = themeColor("--xtd-orange", "#f45700");
    const ink = themeColor("--xtd-ink", "#151515");
    const dataset = config?.data?.datasets?.[0];
    if (!dataset) {
        return config;
    }
    if (config.type === "bar") {
        const values = field.data?.[0]?.values || [];
        if (values.length === dataset.data.length) {
            const original = Array.isArray(dataset.backgroundColor) ? dataset.backgroundColor : [];
            dataset.backgroundColor = values.map((point, index) => {
                if (point.type === "past") {
                    return orange;
                }
                if (point.type === "present") {
                    return ink;
                }
                if (point.type === "future") {
                    return withAlpha(orange, 0.35);
                }
                return original[index];
            });
        }
        dataset.maxBarThickness = 28;
        dataset.borderRadius = 4;
    } else if (config.type === "line") {
        dataset.borderColor = orange;
        dataset.backgroundColor = withAlpha(orange, 0.15);
    }
    return config;
}

// Odoo 20: el gráfico se configura en getChartConfig() (consumido por useChart);
// en 19 había que envolver getBarChartConfig/getLineChartConfig en renderChart.
patch(JournalDashboardGraphField.prototype, {
    getChartConfig() {
        const config = super.getChartConfig(...arguments);
        return config ? recolor(this, config) : config;
    },
});
