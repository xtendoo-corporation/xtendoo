/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";
import { Component, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SynchNotificationWidget extends Component {
    static template = "pos_fast_loading.SynchNotificationWidget";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.pos = useService("pos");
        onMounted(() => this.onMounted());
    }
    onMounted() {
        var self = this;
        self.interval_id = false;

        if (!self.pos.config.enable_pos_longpolling) {
            if (self.pos.mongo_config && self.pos.mongo_config.pos_live_sync == "notify") $(".session_update").show();

            if(!self.interval_id &&
                self.pos &&
                self.pos.mongo_config &&
                self.pos.mongo_config.pos_live_sync != "reload"
            ) self.start_cache_polling();
        }

        if (self.pos.mongo_config) {
            setTimeout(() => {
                $(".session_update").click();
            }, 1000);
        }
    }
    async _onClickSessionUpdate() {
        var self = this;
        let config_id = self.pos.config.id;
        let last_update_time = self.pos.mongo_config.cache_last_update_time;

        await this.orm.call("mongo.server.config", "get_data_on_sync", [], { 
            config_id: config_id, 
            mongo_cache_last_update_time: last_update_time, 
            context: user.context,
        }).then(function (res) {
            if(self.pos && self.pos.mongo_config) self.post_rechecking_process(res);
            self.render();
        }).catch(function (error, event) {
            if (event && event.preventDefault) event.preventDefault();
            $(".session_update .fa-refresh").css({
                color: "rgb(94, 185, 55)",
            });
        });
    }
    start_cache_polling() {
        var self = this;
        if (!self.interval_id)
            self.interval_id = setInterval(function () {
                if (self.pos.config.id) {
                    setTimeout(function () {
                    }, 3000);

                    let res = rpc("/cache/notify", {
                        config_id: self.pos.config.id,
                        mongo_cache_last_update_time: self.pos.mongo_config.cache_last_update_time,
                    }).then(function (result) {
                        if (result.sync_method == "reload") {
                            clearInterval(self.interval_id);
                            self.interval_id = false;
                        } else {
                            if (result.is_data_updated) {
                                $(".session_update .fa-refresh").css({
                                    color: "rgb(94, 185, 55)",
                                });
                            } else {
                                if (result.sync_method == "notify") {
                                    $(".session_update .fa-refresh").css({
                                        color: "#ff5656",
                                    });
                                    clearInterval(self.interval_id);
                                    self.interval_id = false;
                                } else if (result.sync_method == "realtime") {
                                    $(".session_update .fa-refresh").css({
                                        color: "#ff5656",
                                    });
                                    if (result.data) self.post_rechecking_process(result.data);
                                }
                            }
                        }
                    });
                    return res
                }
            }, 5000);
    }
    post_rechecking_process(res) {
        var self = this;
        if (res) {
            const {
                mongo_config,
                products = false,
                partners = false,
                partner_deleted_record_ids = false,
                product_deleted_record_ids = false,
            } = res;
            self.pos.mongo_config.cache_last_update_time = mongo_config;

            if (!self.pos.config.enable_pos_longpolling) {
                // *********************Adding and Updating the Products*******************************
                self.updatePosProducts(products, product_deleted_record_ids);

                // *********************Adding and Updating Pricelist Item to pos*********************
                // self.updatePricePos(pricelist_items, price_deleted_record_ids);

                // *********************Adding and Updating Partner to pos*********************
                self.updatePartnerPos(partners, partner_deleted_record_ids);
            }

            // ************************ Partners deleted from indexedDB***************************
            self.pos.data.updatePartnerIDB(partners, partner_deleted_record_ids);

            // **********************Updating Time In IndexedDB************************************
            self.updateCacheTimeIDB();

            // *********** Pricelist item Deleted and Updated from indexedDB**********************
            // self.updatePriceIDB(pricelist_items, price_deleted_record_ids);

            // ***********Products deleted from indexedDB*****************************************
            self.pos.data.updateProductsIDB(products, product_deleted_record_ids);

            // ***********************************************************************************
            if (!self.pos.config.enable_pos_longpolling) {
                $(".session_update .fa-refresh").css({
                    color: "rgb(94, 185, 55)",
                });
                if (!self.interval_id) self.start_cache_polling();
            }
        } else console.log("product not updated");
    }
    async updatePosProducts(products, product_deleted_record_ids) {
        var self = this;
        
        if (products && products.length) {
            $.each(products, async function (seq, product) {
                if (self.pos.data.records['product.product'].has(product.id)) {
                    let rec = self.pos.data.records['product.product'].get(product.id);
                    await self.formatData(rec, 'product.product', [product]);
                }else{
                    let d = {}
                    d['product.product'] = [product];
                    self.pos.data.models.loadData(d);
                }
            });
        }

        if (product_deleted_record_ids && product_deleted_record_ids.length) {
            $.each(product_deleted_record_ids, async function (seq, record) {
                if (record.id in self.pos.data.records['product.product']) {
                    let rec = self.pos.data.records['product.product'][record.id];
                    await self.pos.data.models['product.product'].delete(rec);
                }
            });
        }

        await this.pos.processProductAttributes();
    }
    updatePartnerPos(partners, partner_deleted_record_ids) {
        var self = this;
        $.each(partners, async function (id, partner) {
            if (partner.id in self.pos.data.records['res.partner']) {
                let rec = self.pos.data.records['res.partner'][partner.id];
                await self.pos.data.models['res.partner'].update(rec, partner);
            }
        });

        // if (partners) self.pos.db.add_partners(partners);
        if (partner_deleted_record_ids && partner_deleted_record_ids.length) {
            console.log("######## deleting partner ##############");
            $.each(partner_deleted_record_ids, async function (seq, partner_id) {
                let rec = self.pos.data.records['res.partner'][partner_id];
                await self.pos.data.models['res.partner'].delete(rec);
                // self.delete_partner(partner_id);
            });
        }
    }
    updateCacheTimeIDB() {
        var self = this;
        if (!("indexedDB" in window)) {
            console.log("This browser doesn't support IndexedDB");
        } else {
            var request = window.indexedDB.open("cacheDate", 1);
            request.onsuccess = function (event) {
                var db = event.target.result;
                if (db.objectStoreNames.contains("last_update")) {
                    var transaction = db.transaction("last_update", "readwrite");
                    var itemsStore = transaction.objectStore("last_update");
                    var dateDataStore = itemsStore.get("time");
                    dateDataStore.onsuccess = function (event) {
                        var req = event.target.result;
                        req = {
                            id: "time",
                            time: self.pos.mongo_config.cache_last_update_time,
                        };
                        var requestUpdate = itemsStore.put(req);
                    };
                }
            };
        }
    }
    updatePriceIDB(pricelist_items, price_deleted_record_ids) {
        var self = this;
        if ("indexedDB" in window) {
            if (
                (pricelist_items && pricelist_items.length) ||
                (price_deleted_record_ids && price_deleted_record_ids.length)
            ) {
                var request = window.indexedDB.open("Items", 1);
                request.onsuccess = function (event) {
                    var db = event.target.result;
                    var transaction = db.transaction("items", "readwrite");
                    var itemsStore = transaction.objectStore("items");
                    if (price_deleted_record_ids && price_deleted_record_ids.length)
                        price_deleted_record_ids.forEach(function (id) {
                            var data_store = itemsStore.get(id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                var requestUpdate = itemsStore.delete(id);
                            };
                        });
                    if (pricelist_items && pricelist_items.length)
                        pricelist_items.forEach(function (item) {
                            var data_store = itemsStore.get(item.id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                data = item;
                                var requestUpdate = itemsStore.put(data);
                            };
                        });

                    //---------------------------------------------
                    if (self.pos && self.pos.get_order()) {
                        var order = self.pos.get_order();
                        var pricelist = order.pricelist;
                        order.set_pricelist(pricelist);
                        if (
                            order.get_screen_data() &&
                            order.get_screen_data().name == "ProductScreen"
                        ) {
                            self.pos.showScreen("PartnerListScreen");
                            self.pos.showScreen("ProductScreen");
                        }
                    }
                    //---------------------------------------------
                };
            }
        }
    }
    updatePricePos(pricelist_items, price_deleted_record_ids) {
        var self = this;
        var delete_price_data = [];
        if (
            (pricelist_items && pricelist_items.length) ||
            (price_deleted_record_ids && price_deleted_record_ids.length)
        ) {
            var pricelist_items_by_pricelist_id = {};
            $.each(pricelist_items, function (seq, item) {
                if (item.pricelist_id[0] in pricelist_items_by_pricelist_id)
                    pricelist_items_by_pricelist_id[item.pricelist_id[0]].push(item);
                else pricelist_items_by_pricelist_id[item.pricelist_id[0]] = [item];
            });
            $.each(price_deleted_record_ids, function (seq, item) {
                delete_price_data.push(pricelist_items_by_pricelist_id);
            });
            $.each(self.pos.pricelists, function (seq, pricelist) {
                var new_pricelist_items = [];
                $.each(pricelist.items, function (seq, item) {
                    if (price_deleted_record_ids.indexOf(item.id) == -1)
                        new_pricelist_items.push(item);
                });
                if (pricelist_items_by_pricelist_id[pricelist.id]) {
                    var pricelist_new_items = new_pricelist_items.concat(
                        pricelist_items_by_pricelist_id[pricelist.id]
                    );
                    pricelist.items = pricelist_new_items;
                } else pricelist.items = new_pricelist_items;
            });
        }
    }
    async sync_data(res, model){
        let self= this;
        if(res.operation === 'CREATE'){
            let d = {}
            d[model] = res.record
            self.data.models.loadData(d);
        }else{
            let rec = self.data.records[model][res.record_id];
            if(rec){
                if(res.operation === 'UPDATE') await self.formatData(rec, model, res.record);
                else if(res.operation === 'DELETE') rec.delete();
            }
            if(!rec && res.operation === 'UPDATE'){
                let d = {}
                d[model] = res.record
                self.data.models.loadData(d);
            }
        }
    }
    async formatData(rec, model, result) {
        let self = this;
        const X2MANY_TYPES = new Set(["many2many", "one2many"]);
        
        for (const record of result) {
            if (rec) {
                const formattedForUpdate = {};
                for (const [field, value] of Object.entries(record)) {
                    const fieldsParams = self.pos.data.relations[model][field];
        
                    if (!fieldsParams) continue;
                    if (X2MANY_TYPES.has(fieldsParams.type)) {
                        const currentValues = rec[field].map(item => item.id);
                        const newValues = value.map(id => id);
        
                        const toAdd = newValues.filter(id => !currentValues.includes(id));
                        const toRemove = currentValues.filter(id => !newValues.includes(id));
        
                        formattedForUpdate[field] = [
                            ...toAdd
                                .map(id => {
                                    const item = self.pos.data.models[fieldsParams.relation].get(id);
                                    if(item) return item ? ["link", item] : null; // Add null check
                                })
                                .filter(item => item !== null),  // Filter out null values
                            ...toRemove
                                .map(id => {
                                    const item = self.pos.data.models[fieldsParams.relation].get(id);
                                    if(item) return item ? ["unlink", item] : null; // Add null check
                                })
                                .filter(item => item !== null)  // Filter out null values
                        ];
        
                    } else if (fieldsParams.type === "many2one") {
                        if (self.pos.data.models[fieldsParams.relation]) {
                            const item = self.pos.data.models[fieldsParams.relation].get(value);
                            if (item) {
                                formattedForUpdate[field] = ["link", item];
                            }
                        }
                    } else {
                        formattedForUpdate[field] = value;
                    }
                }
                rec.update(formattedForUpdate);
            }
        }
    }
}