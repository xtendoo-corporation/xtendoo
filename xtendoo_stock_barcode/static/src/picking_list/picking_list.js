/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useState } from "@odoo/owl";

export class XtendooStockBarcodePickingList extends Component {
    static template = "xtendoo_stock_barcode.PickingList";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.barcodeService = useService("barcode");
        this.notificationService = useService("notification");
        this.orm = useService("orm");

        // Recuperar estado previo si existe (para el botón 'Atrás' del navegador)
        const prevState = this.props.action.params.state || {};

        this.state = useState({
            loading: true,
            pickings: [],
            filter: prevState.filter || 'pending', // 'all' or 'pending'
            searchQuery: prevState.searchQuery || '',
            productFilter: prevState.productFilter || null, // {id, name, barcode}
        });

        this.stateColors = {
            draft: 'bg-secondary',
            waiting: 'bg-warning text-dark',
            confirmed: 'bg-info text-dark',
            assigned: 'bg-success',
            done: 'bg-primary',
            cancel: 'bg-danger',
        };

        this.stateLabels = {
            draft: _t('Borrador'),
            waiting: _t('Esperando otra operación'),
            confirmed: _t('En espera'),
            assigned: _t('Preparado'),
            done: _t('Hecho'),
            cancel: _t('Cancelado'),
        };

        useBus(this.barcodeService.bus, "barcode_scanned", (ev) =>
            this.onBarcodeScanned(ev.detail.barcode)
        );

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            let domain = [...(this.props.action.params.domain || [])];

            if (this.state.filter === 'pending') {
                domain.push(['state', 'not in', ['done', 'cancel']]);
            }

            if (this.state.searchQuery) {
                const search = this.state.searchQuery.trim();
                domain.push('|', ['name', 'ilike', search], ['origin', 'ilike', search]);
            }

            if (this.state.productFilter) {
                domain.push(['move_ids.product_id', '=', this.state.productFilter.id]);
            }

            this.state.pickings = await this.orm.call(
                "stock.picking",
                "action_xt_get_picking_list_data",
                [domain]
            );
        } catch (error) {
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onBarcodeScanned(barcode) {
        try {
            const products = await this.orm.call(
                "product.product",
                "search_read",
                [[['barcode', '=', barcode]], ['id', 'display_name']]
            );

            if (products.length > 0) {
                const product = products[0];
                this.state.productFilter = {
                    id: product.id,
                    name: product.display_name,
                    barcode: barcode
                };
                this.notificationService.add(
                    _t("Filtrando por producto: %s", product.display_name),
                    { type: "info" }
                );
                await this.loadData();
            } else {
                // Si no es un producto, quizás sea un picking?
                // Podríamos intentar abrirlo directamente si coincide el nombre
                const picking = await this.orm.call(
                    "stock.picking",
                    "search_read",
                    [[['name', '=', barcode]], ['id']]
                );
                if (picking.length > 0) {
                    return this.openPicking(picking[0].id);
                }

                this.notificationService.add(
                    _t("Código de barras no reconocido como producto o albarán."),
                    { type: "warning" }
                );
            }
        } catch (error) {
            console.error(error);
        }
    }

    clearProductFilter() {
        this.state.productFilter = null;
        this.loadData();
    }

    setFilter(filter) {
        this.state.filter = filter;
        this.loadData();
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        // Debounce simple
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => this.loadData(), 500);
    }

    async openPicking(pickingId) {
        return this.actionService.doAction({
            type: "ir.actions.client",
            tag: "xtendoo_stock_barcode_client_action",
            name: _t("Albarán"),
            target: "fullscreen",
            params: {
                model: "stock.picking",
                picking_id: pickingId,
                // Pasamos el estado actual para que al volver se pueda restaurar
                return_state: {
                    filter: this.state.filter,
                    searchQuery: this.state.searchQuery,
                    productFilter: this.state.productFilter,
                }
            }
        });
    }

    exitAction() {
        return this.actionService.doAction("xtendoo_stock_barcode.action_xtendoo_stock_barcode_main_menu", {
            clear_breadcrumbs: true
        });
    }
}

registry.category("actions").add("xtendoo_stock_barcode_picking_list", XtendooStockBarcodePickingList);
