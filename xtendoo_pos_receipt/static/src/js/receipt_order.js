// odoo/custom/src/custom-todopinturas/todopintura_pos_custom/static/src/js/receipt_order_patch.js
import { patch } from "@web/core/utils/patch";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { _t } from "@web/core/l10n/translation";
import { onMounted } from "@odoo/owl";

// Explicación: Añadir fallback para resolver la compañía en varios lugares (env.pos, props.order, env.company),
// más logs detallados para depurar en Odoo 19, y mantener/llamar al setup original para no romper la inicialización.

// Guardamos el setup original para mantener la inicialización base de Odoo 19
const originalSetup = ReceiptHeader.prototype.setup;

// Helper para serializar de forma segura y evitar errores por referencias circulares
function safeDump(obj) {
    try {
        return JSON.stringify(obj, (key, value) => {
            if (typeof value === 'function') return `[Function: ${value.name || 'anonymous'}]`;
            return value;
        }, 2);
    } catch (e) {
        try {
            return String(obj);
        } catch (e2) {
            return '<unserializable>';
        }
    }
}

// Resolver la compañía buscando en varios lugares (compatibilidad Odoo 19)
function resolveCompany(component) {
    try {
        // 1) this.env.pos.company (clásico)
        if (component?.env?.pos?.company) {
            return component.env.pos.company;
        }
        // 1b) this.env may store debug context under a Symbol (Odoo 19). Try keys via Reflect (strings + symbols).
        if (component?.env) {
            try {
                const envKeys = Reflect.ownKeys(component.env);
                if (envKeys && envKeys.length) {
                    console.log('[POS DEBUG] resolveCompany - env keys:', envKeys.map(k => k.toString()));
                }
                for (const k of envKeys) {
                    try {
                        const ctx = component.env[k];
                        // Log basic type info to avoid heavy serialization
                        console.log('[POS DEBUG] resolveCompany - env key:', k.toString(), 'type:', typeof ctx);
                        if (ctx && ctx.pos) {
                            try {
                                const posKeys = Reflect.ownKeys(ctx.pos || {}).map(x => x.toString()).slice(0, 20);
                                console.log('[POS DEBUG] resolveCompany - ctx.pos keys (sample):', posKeys);
                            } catch (e) {
                                console.log('[POS DEBUG] resolveCompany - ctx.pos (raw):', ctx.pos);
                            }
                            if (ctx.pos.company) {
                                console.log('[POS DEBUG] resolveCompany - found company in env key:', k.toString());
                                try {
                                    console.log('[POS DEBUG] resolveCompany - company dump:', safeDump({ id: ctx.pos.company.id, name: ctx.pos.company.name, vat: ctx.pos.company.vat }));
                                } catch (e) {
                                    console.log('[POS DEBUG] resolveCompany - company (raw):', ctx.pos.company);
                                }
                                return ctx.pos.company;
                            }
                            if (ctx.pos.config && ctx.pos.config.company) {
                                console.log('[POS DEBUG] resolveCompany - found company in env key (pos.config):', k.toString());
                                return ctx.pos.config.company;
                            }
                            console.log('[POS DEBUG] resolveCompany - returning ctx.pos from env key:', k.toString());
                            return ctx.pos;
                        }
                    } catch (e) {
                        // ignore per-key errors
                    }
                }
            } catch (e) {
                // ignore symbol inspection errors
            }
        }
        // 2) this.props.order.company
        const order = component?.props?.order;
        if (order) {
            // Try plain property first
            if (order.company) {
                console.log('[POS DEBUG] resolveCompany - found company as order.company');
                return order.company;
            }
            // Try common string keys
            if (order.raw && order.raw.company) {
                console.log('[POS DEBUG] resolveCompany - found company as order.raw.company');
                return order.raw.company;
            }
            if (order.company_id && typeof order.company_id === 'object') {
                console.log('[POS DEBUG] resolveCompany - found company as order.company_id');
                return order.company_id;
            }

            // Now inspect symbol/string properties on the order (use Reflect to get both)
            try {
                const orderKeys = Reflect.ownKeys(order);
                if (orderKeys && orderKeys.length) {
                    console.log('[POS DEBUG] resolveCompany - order keys:', orderKeys.map(k => k.toString()).slice(0,50));
                }
                for (const k of orderKeys) {
                    const desc = k.toString();
                    try {
                        const val = order[k];
                        console.log('[POS DEBUG] resolveCompany - order key:', desc, 'typeof:', typeof val);
                        // If it's a function (lazy getter), call it
                        if (typeof val === 'function') {
                            try {
                                const res = val.call(order);
                                console.log('[POS DEBUG] resolveCompany - called function for key:', desc, '-> typeof res:', typeof res);
                                if (res) {
                                    if (desc.includes('__lazy_company') || (res && (res.vat || res.name))) {
                                        console.log('[POS DEBUG] resolveCompany - got company from order key (func):', desc, res && res.id ? {id: res.id, name: res.name, vat: res.vat} : res);
                                        return res;
                                    }
                                    if (desc.includes('__lazy_raw')) {
                                        if (res && res.company) {
                                            console.log('[POS DEBUG] resolveCompany - got company from order key (func raw):', desc);
                                            return res.company;
                                        }
                                    }
                                }
                            } catch (e) {
                                console.warn('[POS DEBUG] resolveCompany - error calling function for key', desc, e);
                                // ignore call errors
                            }
                        }
                        // If it's an object, inspect it
                        if (val && typeof val === 'object') {
                            try {
                                const valKeys = Reflect.ownKeys(val).map(x => x.toString()).slice(0,20);
                                console.log('[POS DEBUG] resolveCompany - order key object keys (sample):', desc, valKeys);
                            } catch (e) {
                                // ignore
                            }
                            if (desc.includes('__lazy_raw') && val.company) {
                                console.log('[POS DEBUG] resolveCompany - got company from order key (object raw):', desc);
                                return val.company;
                            }
                            if (desc.includes('__lazy_company') && val) {
                                console.log('[POS DEBUG] resolveCompany - got company from order key (object company):', desc);
                                return val;
                            }
                        }
                    } catch (e) {
                        // ignore per-key errors
                    }
                }
            } catch (e) {
                // ignore symbol inspection errors
            }
        }
        // 3) this.env.company
        if (component?.env?.company) {
            console.log('[POS DEBUG] resolveCompany - found company in env.company');
            return component.env.company;
        }
    } catch (e) {
        console.warn('[POS DEBUG] resolveCompany error:', e);
    }
    return null;
}

// Intentar resolver la compañía con reintentos (útil si getters perezosos se inicializan después)
function tryResolveCompanyWithRetries(component, maxAttempts = 6, delay = 250) {
    return new Promise((resolve) => {
        let attempts = 0;
        const attempt = () => {
            try {
                const company = resolveCompany(component);
                attempts += 1;
                if (company) {
                    console.log('[POS DEBUG] tryResolveCompanyWithRetries - resolved on attempt', attempts);
                    return resolve(company);
                }
                if (attempts >= maxAttempts) {
                    console.warn('[POS DEBUG] tryResolveCompanyWithRetries - failed after attempts', attempts);
                    return resolve(null);
                }
            } catch (e) {
                console.warn('[POS DEBUG] tryResolveCompanyWithRetries - error during attempt', e);
            }
            setTimeout(attempt, delay);
        };
        attempt();
    });
}

// Resolver VAT/CIF intentando varios campos/propiedades (company, partner, raw, símbolos)
function resolveVat(company) {
    try {
        if (!company) return "";
        // Prefer string values
        const candidates = [
            company.vat,
            company.vat_number,
            company.vat_id,
            company.tax_id,
            // partner-related
            company.partner_id && (company.partner_id.vat || (company.partner_id.raw && company.partner_id.raw.vat)),
            company.commercial_partner_id && (company.commercial_partner_id.vat || (company.commercial_partner_id.raw && company.commercial_partner_id.raw.vat)),
            // raw fallback
            company.raw && company.raw.vat,
            company.raw && company.raw.vat_number,
        ];
        for (const c of candidates) {
            if (typeof c === 'string' && c.trim()) return c.trim();
            if (typeof c === 'number') return String(c);
        }
        // Intentar inspeccionar keys simbólicas / proxy
        try {
            const keys = Reflect.ownKeys(company || {});
            for (const k of keys) {
                const kn = k.toString().toLowerCase();
                if (kn.includes('vat') || kn.includes('tax') || kn.includes('cif')) {
                    try {
                        const v = company[k];
                        if (typeof v === 'string' && v.trim()) return v.trim();
                        if (typeof v === 'number') return String(v);
                        // si es objeto y tiene raw.vat
                        if (v && typeof v === 'object') {
                            if (v.vat && typeof v.vat === 'string' && v.vat.trim()) return v.vat.trim();
                            if (v.raw && v.raw.vat && typeof v.raw.vat === 'string' && v.raw.vat.trim()) return v.raw.vat.trim();
                        }
                    } catch (e) {
                        // ignore per-key
                    }
                }
            }
        } catch (e) {
            // ignore
        }
    } catch (e) {
        console.warn('[POS DEBUG] resolveVat error:', e);
    }
    return "";
}

patch(ReceiptHeader.prototype, {
    get vatText() {
        // Usar company ya resuelta si existe (evita problema si se resolvió asíncronamente)
        const resolved = this._resolvedCompany || resolveCompany(this);
        if (!resolved) {
            console.warn("[POS DEBUG] vatText - no se encontró company en env/props (ni resolved)", {
                env: this?.env,
                props: this?.props,
            });
            return "";
        }
        // Resolver el VAT con múltiples fallbacks
        const vatValue = resolveVat(resolved);
        console.log('[POS DEBUG] vatText - vatValue candidate:', vatValue, 'typeof:', typeof vatValue);
        if (!vatValue) {
            console.warn('[POS DEBUG] vatText - vat vacío o no encontrado en company (se usarán otros ficheros si proceden)');
            return "";
        }
        return _t("CIF: %(vatId)s", { vatId: vatValue });
    },
    setup() {
        // Llamamos al setup original si existe (importante en Odoo 19)
        if (typeof originalSetup === 'function') {
            try {
                originalSetup.apply(this, arguments);
            } catch (err) {
                console.error('[POS DEBUG] Error al ejecutar originalSetup:', err);
            }
        }

        console.log('[POS DEBUG] patched setup invoked - this:', this);
        onMounted(async () => {
            console.log('[POS DEBUG] onMounted - this.env (raw):', this.env);
            console.log('[POS DEBUG] onMounted - this.props (raw):', this.props);
            // Inspeccionar props.order si existe
            if (this?.props?.order) {
                try {
                    console.log('[POS DEBUG] onMounted - this.props.order (keys):', Object.keys(this.props.order || {}));
                    // Evitar intentar serializar objetos grandes sin control
                    try {
                        const raw = this.props.order.raw || this.props.order;
                        console.log('[POS DEBUG] onMounted - this.props.order.raw (dump):', safeDump(raw));
                    } catch (e) {
                        console.warn('[POS DEBUG] Error al dump props.order:', e);
                    }
                } catch (e) {
                    console.warn('[POS DEBUG] Error al inspeccionar props.order:', e);
                }
            }

            // Intentar resolver la compañía por varios caminos con reintentos
            const company = await tryResolveCompanyWithRetries(this, 6, 250);
            if (!company) {
                console.warn('[POS DEBUG] setup - company no encontrada tras fallback y reintentos', {
                    env: this.env,
                    props: this.props,
                });
                return;
            }

            // Guardar la compañía resuelta para que vatText la use sincrónicamente
            this._resolvedCompany = company;
            console.log('[POS DEBUG] setup - _resolvedCompany set:', safeDump({ id: company.id, name: company.name, vat: company.vat }));

            // Crear una versión plana de la company para inyectarla en plantillas (evita proxies y getters perezosos)
            let plainCompany = null;
            try {
                plainCompany = {
                    id: company.id,
                    name: company.name || '',
                    vat: resolveVat(company) || (company.vat || ''),
                    street: company.street || '',
                    street2: company.street2 || '',
                    zip: company.zip || '',
                    city: company.city || '',
                    state_id: company.state_id && company.state_id.name ? { id: company.state_id.id, name: company.state_id.name } : (company.state_id || null),
                    country_id: company.country_id && company.country_id.name ? { id: company.country_id.id, name: company.country_id.name } : (company.country_id || null),
                    phone: company.phone || '',
                    email: company.email || false,
                };
            } catch (e) {
                console.warn('[POS DEBUG] setup - error building plainCompany:', e);
                plainCompany = { id: company.id || null, name: company.name || '', vat: company.vat || '' };
            }

            // === INYECCIÓN: permitir que las plantillas accedan inmediatamente a company (usando plainCompany) ===
            try {
                // 1) props.data
                if (this.props) {
                    try {
                        if (!this.props.data) {
                            try { this.props.data = {}; } catch (e) { /* no writable */ }
                        }
                        if (this.props.data) {
                            try { this.props.data.company = plainCompany; } catch (e) { /* no writable */ }
                            try { this.props.data._debug = safeDump({company: plainCompany, order_id: this.props.order && this.props.order.raw ? this.props.order.raw.id : (this.props.order && this.props.order.id) }); } catch (e) { /* ignore */ }
                            console.log('[POS DEBUG] setup - injected plainCompany into props.data.company');
                        }
                    } catch (e) {
                        console.warn('[POS DEBUG] setup - error injecting plainCompany into props.data:', e);
                    }
                }
            } catch (e) {
                console.warn('[POS DEBUG] setup - failed injecting plainCompany into props.data:', e);
            }

            try {
                // 2) props.order.raw or props.order.company (keep original proxy there but set raw.company to plain)
                if (this.props && this.props.order) {
                    try {
                        if (this.props.order.raw) {
                            try { this.props.order.raw.company = plainCompany; } catch (e) { /* ignore */ }
                            try { this.props.order.raw._debug = safeDump({company: plainCompany, order_id: this.props.order.raw.id}); } catch (e) { /* ignore */ }
                        } else {
                            try { this.props.order.company = plainCompany; } catch (e) { /* ignore */ }
                        }
                        console.log('[POS DEBUG] setup - injected plainCompany into props.order (raw/company)');
                    } catch (e) {
                        console.warn('[POS DEBUG] setup - failed injecting plainCompany into props.order:', e);
                    }
                }
            } catch (e) {
                console.warn('[POS DEBUG] setup - error inspecting props.order for plain injection:', e);
            }

            try {
                // 3) env.pos.company: keep as original proxy to avoid side effects, but set env.pos.company_printable to plainCompany for templates
                if (this.env && this.env.pos) {
                    try { this.env.pos.company_printable = plainCompany; } catch (e) { /* ignore */ }
                    try { this.env.pos.company_printable_debug = safeDump(plainCompany); } catch (e) { /* ignore */ }
                    console.log('[POS DEBUG] setup - set env.pos.company_printable to plainCompany');
                }
            } catch (e) {
                console.warn('[POS DEBUG] setup - failed setting env.pos.company_printable:', e);
            }
            // === FIN INYECCIÓN ===

            // Logs detallados de la compañía (campos comunes en Odoo)
            console.log('[POS DEBUG] setup - company (raw):', company);
            try {
                console.log('[POS DEBUG] setup - company (dump):', safeDump({
                    id: company.id,
                    name: company.name,
                    vat: company.vat,
                    street: company.street,
                    street2: company.street2,
                    zip: company.zip,
                    city: company.city,
                    state_id: company.state_id,
                    country_id: company.country_id,
                    phone: company.phone,
                    email: company.email,
                }));
            } catch (e) {
                console.warn('[POS DEBUG] Error al serializar company:', e);
            }

            // Información adicional útil para depurar (config del POS, partner, etc.)
            const posResolved = this.env?.pos || this.props?.order?.config || null;
            if (posResolved) {
                try {
                    console.log('[POS DEBUG] setup - pos (keys):', Object.keys(posResolved || {}));
                } catch (e) {
                    console.log('[POS DEBUG] setup - pos (raw):', posResolved);
                }
            } else {
                console.log('[POS DEBUG] setup - pos no resuelto (ni env.pos ni props.order.config)');
            }

            try {
                const currentOrder = this.env?.pos?.get_order ? this.env.pos.get_order() : (this.props?.order ? this.props.order : null);
                console.log('[POS DEBUG] setup - currentOrder (dump or id):', currentOrder ? safeDump({ id: currentOrder.id, name: currentOrder.display_name || currentOrder.name }) : 'no currentOrder');
            } catch (e) {
                console.warn('[POS DEBUG] Error al obtener currentOrder:', e);
            }

            // --- Nuevo: ajustar clase del logo según su relación de aspecto ---
            try {
                const applyLogoSizing = () => {
                    try {
                        // Buscar logo dentro del render container del receipt
                        const logo = document.querySelector('.render-container .pos-receipt .pos-receipt-logo');
                        if (!logo) return;
                        // Crear función que evalúa la relación de aspecto real de la imagen
                        const evalAndApply = (img) => {
                            try {
                                const naturalW = img.naturalWidth || img.width || 0;
                                const naturalH = img.naturalHeight || img.height || 0;
                                if (!naturalW || !naturalH) return;
                                const ratio = naturalW / naturalH;
                                img.classList.remove('logo--wide', 'logo--tall');
                                if (ratio > 1.6) {
                                    img.classList.add('logo--wide');
                                } else if (ratio < 0.8) {
                                    img.classList.add('logo--tall');
                                } else {
                                    // roughly square-ish
                                }
                            } catch (e) {
                                console.warn('[POS DEBUG] evalAndApply logo error', e);
                            }
                        };
                        if (logo.complete && logo.naturalWidth) {
                            evalAndApply(logo);
                        } else {
                            logo.addEventListener('load', () => evalAndApply(logo));
                            // fallback small timeout
                            setTimeout(() => evalAndApply(logo), 500);
                        }
                    } catch (e) {
                        console.warn('[POS DEBUG] applyLogoSizing error', e);
                    }
                };
                // Ejecutar una vez y también on-demand cada vez que se abre el receipt
                applyLogoSizing();
                document.addEventListener('click', (ev) => {
                    // si se hace click en botones de impresión o en la UI que re-renderizan, re-evaluar
                    applyLogoSizing();
                });
            } catch (e) {
                console.warn('[POS DEBUG] Logo sizing initialization failed', e);
            }

        });
    },
});
