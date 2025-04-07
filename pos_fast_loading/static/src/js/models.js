/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Loader } from "@point_of_sale/app/loader/loader";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosData } from "@point_of_sale/app/models/data_service";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";

patch(PosData.prototype, {
    async loadInitialData() {
        let context = await this.update_required_context();
        let res = await this.orm.call("pos.session", "load_data", [
            odoo.pos_session_id,
            PosData.modelToLoad,
        ], { context: context });
        return res;
    },
    update_required_context() {
        return new Promise((resolve, reject) => {
            var self = this;
            var context = {};
            var data = [];
            var request = window.indexedDB.open("cacheDate", 1);
            request.onsuccess = async function (event) {
                var db = event.target.result;
                if (db.objectStoreNames.contains("last_update")) {
                    var res = await getRecordsIndexedDB(db, "last_update");
                    context["sync_from_mongo"] = true;
                    context["is_indexed_updated"] = res;
                    // localStorage.setItem("cache_last_update", JSON.stringify(res));
                    resolve(context);
                }
            };
            request.onerror = function (event) {
                reject();
            };
            request.onupgradeneeded = function (event) {
                var db = event.target.result;
                var itemsStore = db.createObjectStore("last_update", {
                    keyPath: "id",
                });
            };
        });       
    },
    async initData() {
        const modelClasses = {};
        const relations = {};
        const fields = {};
        const data = {};
        const response = await this.loadInitialData();

        for (const [model, values] of Object.entries(response)) {
            if (!("indexedDB" in window)) {
                console.log("This browser doesn't support IndexedDB");
                relations[model] = values.relations;
                fields[model] = values.fields;
                data[model] = values.data;
            } else {
                if(['product.product', 'res.partner'].includes(model)){
                    relations[model] = values.relations;
                    fields[model] = values.fields;
                }else{
                    relations[model] = values.relations;
                    fields[model] = values.fields;
                    data[model] = values.data;
                }
            }
        }
        for (const posModel of registry.category("pos_available_models").getAll()) {
            const pythonModel = posModel.pythonModel;
            const extraFields = posModel.extraFields || {};

            modelClasses[pythonModel] = posModel;
            relations[pythonModel] = {
                ...relations[pythonModel],
                ...extraFields,
            };
        }
        const { models, records, indexedRecords } = createRelatedModels(
            relations,
            modelClasses,
            this.opts
        );

        this.records = records;
        this.indexedRecords = indexedRecords;
        this.fields = fields;
        this.relations = relations;
        this.models = models;

        const order = data["pos.order"] || [];
        const orderlines = data["pos.order.line"] || [];

        delete data["pos.order"];
        delete data["pos.order.line"];

        this.models.loadData(data, this.modelToLoad);
        this.models.loadData({ "pos.order": order, "pos.order.line": orderlines });
        const dbData = await this.loadIndexedDBData();
        this.loadedIndexedDBProducts = dbData ? dbData["product.product"] : [];
        this.network.loading = false;

        if(data['mongo.server.config'] && data['mongo.server.config'].length){
            this.mongo_config_id = data['mongo.server.config'][0]['id']
        }

        let prods =  response['product.product']
        let partners =  response['res.partner']
        await this.custom_product_load(prods.data);
        await this.custom_partner_load(partners.data);
    },
    custom_product_load(products) {
        var self = this;
        self.product_loaded = false;
    
        if (products.length) {
            self.models.loadData({ "product.product": products });
            self.loadRemProductsFast();
            console.log("Product loaded through default...");
        }

        // this.ui.block();
        // this.ui.block('Product Loading...');

        var request = window.indexedDB.open("Product", 1);
        request.onsuccess = async function (event) {
            var db = event.target.result;
            if (!products.length) {
                var res = await getRecordsIndexedDB(db, "products");
                self.models.loadData({ "product.product": res });
                self.product_loaded_using_index = true;
                console.log("Product loaded through IndexedDB...");
                // self.ui.unblock();
                // self.ui.unblock();
            } else {
                if (db.objectStoreNames.contains("products")) {
                    try {
                        var product_transaction = db.transaction("products", "readwrite");
                        var productsStore = product_transaction.objectStore("products");
    
                        products.forEach(function (product) {
                            var data_store = productsStore.get(product.id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                data = product;
                                delete data["pos"];
                                delete data["env"];
                                delete data["applicablePricelistItems"];
                                productsStore.put(data);
                            };
                        });
                    } catch (error) {
                        console.log("----exception---- products");
                    }
                }
            }
        };
    
        request.onupgradeneeded = function (event) {
            var db = event.target.result;
            var productsStore = db.createObjectStore("products", {
                keyPath: "id",
            });
        };
    },
    custom_partner_load(partners) {
        var self = this;
        if (partners.length) {
            self.partners = partners;
            self.models.loadData({ "res.partner": partners });
            console.log("partners loaded through default...........");
            self.loadRemCustomersFast();
        }
        var request = window.indexedDB.open("Partners", 1);
        request.onsuccess = function (event) {
            var db = event.target.result;
            if (!partners.length) {
                getRecordsIndexedDB(db, "partners").then(function (res) {
                    self.partners = res;
                    self.models.loadData({ "res.partner": res });
                });
                self.partner_loaded_using_index = true;
                console.log("partners loaded through indexdb...........");
            } else {
                if (db.objectStoreNames.contains("partners")) {
                    try {
                        var transaction = db.transaction("partners", "readwrite");
                        var partnersStore = transaction.objectStore("partners");
                        /*************************************/
                        partners.forEach(function (partner) {
                            var data_store = partnersStore.get(partner.id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                data = partner;
                                var requestUpdate = partnersStore.put(data);
                            };
                        });
                    } catch {
                        console.log("--- exception --- partners");
                    }
                }
            }
        };
        request.onupgradeneeded = function (event) {
            var db = event.target.result;
            var partnersStore = db.createObjectStore("partners", {
                keyPath: "id",
            });
        };

        // **********date*******
        var date_request = window.indexedDB.open("cacheDate", 1);
        date_request.onupgradeneeded = function (event) {
            var db = event.target.result;
            var lastUpdateTimeStore = db.createObjectStore("last_update", {
                keyPath: "id",
            });
        };
        date_request.onsuccess = function (event) {
            var date_db = event.target.result;
            try {
                var time_transaction = date_db.transaction(
                    "last_update",
                    "readwrite"
                );
                var lastTimeStore = time_transaction.objectStore("last_update");
                var last_date_store = lastTimeStore.get("time");
                last_date_store.onsuccess = function (event) {
                    var data = event.target.result;
                    self.mongo_config = self.records['mongo.server.config'][1];
                    data = {
                        id: "time",
                        time: self.mongo_config ? self.mongo_config.cache_last_update_time : undefined,
                    };
                    var last_updated_time = lastTimeStore.put(data);
                    // localStorage.setItem("cache_last_update", JSON.stringify(data));
                };
            } catch {
                console.log("-----exception---- last update");
            }
        };
    },
    async loadRemProductsFast() {
        let products = [];
        let page = 1;
        var self = this;
        do {
            self.company_id = self.models['pos.config'].get(odoo.pos_config_id).company_id.id
            products = await this.orm.call("mongo.server.config", "load_rem_product", [0, page, self.company_id, odoo.pos_session_id]);
            if (products.length) {
                self.models.loadData({ "product.product": products });
                self.updateProductsIDB(products);
            }
            page += 1;
        } while (products.length);
        // self.ui.unblock();
        // self.env.services.ui.unblock();
    },
    async loadRemCustomersFast() {
        let partners = [];
        let page = 1;
        var self = this;
        // this.ui.block("Loading Remaining Customers...")
        do {
            // let company_id = self.config.company_id.id
            // let company_id = Object.values(self.records['res.company'])[0].id
            partners = await this.orm.call("mongo.server.config", "load_rem_customer", [0, page, self.company_id]);
            if (partners) {
                self.models.loadData({ "res.partner": partners });
                self.updatePartnerIDB(partners);
            }
            page += 1;
        } while (partners.length);
        // this.ui.unblock(); // The page is blocked at this point, unblock it.
    },
    updateProductsIDB(products, product_deleted_record_ids) {
        var self = this;
        if ((products && products.length) || (product_deleted_record_ids && product_deleted_record_ids.length)) {
            if (!("indexedDB" in window)) console.log("This browser doesn't support IndexedDB");
            else {
                var request = window.indexedDB.open("Product", 1);
                request.onsuccess = function (event) {
                    var db = event.target.result;
                    var transaction = db.transaction("products", "readwrite");
                    var itemsStore = transaction.objectStore("products");

                    if (products && products.length){
                        $.each(products, function (seq, item) {
                            var data_store = itemsStore.get(item.id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                data = item;
                                delete data["pos"];
                                delete data["env"];
                                delete data["applicablePricelistItems"];
                                var requestUpdate = itemsStore.put(data);
                            };
                        });
                    }
                    if (product_deleted_record_ids && product_deleted_record_ids.length){
                        $.each(product_deleted_record_ids, function (seq, id) {
                            var data_store = itemsStore.get(id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                var requestUpdate = itemsStore.delete(id);
                            };
                        });
                    }
                };
            }
        }
    },
    updatePartnerIDB(partners, partner_deleted_record_ids) {
        var self = this;
        if ((partners && partners.length) || (partner_deleted_record_ids && partner_deleted_record_ids.length)) {
            if (!("indexedDB" in window)) {
                console.log("This browser doesn't support IndexedDB");
            } else {
                var request = window.indexedDB.open("Partners", 1);
                request.onsuccess = function (event) {
                    var db = event.target.result;
                    var transaction = db.transaction("partners", "readwrite");
                    var itemsStore = transaction.objectStore("partners");
                    if (partners && partners.length) {
                        partners.forEach(function (item) {
                            var data_store = itemsStore.get(item.id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                data = item;
                                const updateRequest = itemsStore.put(data);
                                updateRequest.onsuccess = (event) => { console.log(event) };
                                updateRequest.onerror = (event) => { console.log(event)};
                            };
                        });
                    }
                    if (partner_deleted_record_ids &&partner_deleted_record_ids.length) {
                        partner_deleted_record_ids.forEach(function (id) {
                            var data_store = itemsStore.get(id);
                            data_store.onsuccess = function (event) {
                                var data = event.target.result;
                                var requestUpdate = itemsStore.delete(id);
                            };
                        });
                    }
                };
            }
        }
    },
});

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.loader = Loader;
    },
    async initServerData() {
        var self = this;
        self.product_loaded_using_index = false;
        self.partner_loaded_using_index = false;
        await super.initServerData(...arguments);
    },
    async processServerData() {
        await super.processServerData(...arguments);
        this.mongo_config = this.data.models['mongo.server.config'].get(this.data.mongo_config_id)
    },
});

function getRecordsIndexedDB(db, store) {
    return new Promise((resolve, reject) => {
        if (db.objectStoreNames.contains(store)) {
            try {
                var transaction = db.transaction(store, "readwrite");
                var objectStore = transaction.objectStore(store);
                var data_request = objectStore.getAll();
                data_request.onsuccess = function (event) {
                    resolve(event.target.result);
                };
                data_request.onerror = function (event) {
                    reject();
                };
            } catch (e) {
                console.log("No Items found", e);
            }
        }
    });
}