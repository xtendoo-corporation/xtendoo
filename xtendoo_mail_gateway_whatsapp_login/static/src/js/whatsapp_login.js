/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const META_SDK_URL = "https://connect.facebook.net/en_US/sdk.js";
let sdkPromise;

function normalizeGraphVersion(version) {
    const cleanVersion = (version || "21.0").toString().trim();
    return cleanVersion.startsWith("v") ? cleanVersion : `v${cleanVersion}`;
}

function loadMetaSDK() {
    if (window.FB) {
        return Promise.resolve(window.FB);
    }
    if (sdkPromise) {
        return sdkPromise;
    }
    sdkPromise = new Promise((resolve, reject) => {
        const existingScript = document.querySelector(`script[src="${META_SDK_URL}"]`);
        if (existingScript) {
            existingScript.addEventListener("load", () => resolve(window.FB), {
                once: true,
            });
            existingScript.addEventListener(
                "error",
                () => reject(new Error(_t("No se pudo cargar el SDK de Meta."))),
                { once: true }
            );
            return;
        }
        const script = document.createElement("script");
        script.src = META_SDK_URL;
        script.async = true;
        script.defer = true;
        script.onload = () => resolve(window.FB);
        script.onerror = () => reject(new Error(_t("No se pudo cargar el SDK de Meta.")));
        document.head.appendChild(script);
    });
    return sdkPromise;
}

async function xtendooWhatsappEmbeddedSignup(env, action) {
    const params = action.params || {};
    const appId = params.app_id;
    const configId = params.config_id;
    if (!appId || !configId) {
        env.services.notification.add(
            _t("Completa Meta App ID y Meta Config ID antes de continuar."),
            { type: "warning" }
        );
        return;
    }

    try {
        await loadMetaSDK();
        if (!window.FB) {
            throw new Error(_t("El SDK de Meta no está disponible en el navegador."));
        }

        window.FB.init({
            appId,
            cookie: true,
            xfbml: false,
            version: normalizeGraphVersion(params.graph_version),
        });

        const response = await new Promise((resolve) => {
            window.FB.login(resolve, {
                config_id: configId,
                response_type: "code",
                override_default_response_type: true,
                scope: "whatsapp_business_management,whatsapp_business_messaging",
                extras: {
                    feature: "whatsapp_embedded_signup",
                    sessionInfoVersion: 3,
                },
            });
        });

        const authorizationCode = response?.authResponse?.code || response?.code;
        if (!authorizationCode) {
            env.services.notification.add(
                _t("Meta no devolvió un código de autorización. Revisa el popup y vuelve a intentarlo."),
                { type: "warning" }
            );
            return;
        }

        const result = await env.services.orm.call(
            params.call_model,
            params.call_method,
            [params.object_id, authorizationCode]
        );

        env.services.notification.add(
            _t("Se guardaron las credenciales devueltas por Meta en el gateway."),
            { type: "success" }
        );
        return result || { type: "ir.actions.client", tag: "soft_reload" };
    } catch (error) {
        env.services.notification.add(error.message || _t("No fue posible completar el login de Meta."), {
            title: _t("WhatsApp Embedded Signup"),
            type: "danger",
            sticky: true,
        });
    }
}

registry
    .category("actions")
    .add("xtendoo_whatsapp_embedded_signup", xtendooWhatsappEmbeddedSignup);

