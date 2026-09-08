/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const META_SDK_URL = "https://connect.facebook.net/en_US/sdk.js";
const SIGNUP_ASSETS_TIMEOUT_MS = 3 * 60 * 1000;

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
                () => reject(new Error(_t("Could not load the Meta SDK."))),
                { once: true }
            );
            return;
        }
        const script = document.createElement("script");
        script.src = META_SDK_URL;
        script.async = true;
        script.defer = true;
        script.onload = () => resolve(window.FB);
        script.onerror = () => reject(new Error(_t("Could not load the Meta SDK.")));
        document.head.appendChild(script);
    });
    return sdkPromise;
}

/**
 * Listens for the WA_EMBEDDED_SIGNUP postMessage Meta sends to the opener
 * window once the client finishes (or cancels) the Embedded Signup flow.
 * This is the only reliable, documented source for waba_id/phone_number_id.
 */
function waitForSignupAssets(timeoutMs = SIGNUP_ASSETS_TIMEOUT_MS) {
    return new Promise((resolve) => {
        let settled = false;
        let timer;
        const onMessage = (event) => {
            if (typeof event.origin !== "string" || !event.origin.endsWith("facebook.com")) {
                return;
            }
            let data;
            try {
                data = JSON.parse(event.data);
            } catch {
                return;
            }
            if (!data || data.type !== "WA_EMBEDDED_SIGNUP") {
                return;
            }
            settle(data);
        };
        const settle = (data) => {
            if (settled) {
                return;
            }
            settled = true;
            window.removeEventListener("message", onMessage);
            clearTimeout(timer);
            resolve(data || null);
        };
        window.addEventListener("message", onMessage);
        timer = setTimeout(() => settle(null), timeoutMs);
    });
}

async function xtendooWhatsappOnboardingEmbeddedSignup(env, action) {
    const params = action.params || {};
    const gatewayId = params.gateway_id;
    const session = params.session;
    const appId = params.app_id;
    const configId = params.config_id;

    if (!appId || !configId || !gatewayId || !session) {
        env.services.notification.add(
            _t("Missing WhatsApp Embedded Signup configuration. Contact your administrator."),
            { type: "danger" }
        );
        return;
    }

    const signupAssetsPromise = waitForSignupAssets();

    try {
        await loadMetaSDK();
        if (!window.FB) {
            throw new Error(_t("The Meta SDK is not available in this browser."));
        }

        window.FB.init({
            appId,
            cookie: false,
            xfbml: false,
            version: normalizeGraphVersion(params.graph_version),
        });

        const loginResponsePromise = new Promise((resolve) => {
            window.FB.login(resolve, {
                config_id: configId,
                response_type: "code",
                override_default_response_type: true,
                extras: {
                    setup: {},
                    featureType: "whatsapp_embedded_signup",
                    sessionInfoVersion: "3",
                },
            });
        });

        const [loginResponse, signupAssets] = await Promise.all([
            loginResponsePromise,
            signupAssetsPromise,
        ]);

        if (signupAssets && signupAssets.event === "CANCEL") {
            await env.services.orm.call("mail.gateway", "action_reset_signup_attempt", [
                [gatewayId],
                session,
            ]);
            env.services.notification.add(_t("WhatsApp connection cancelled."), {
                type: "warning",
            });
            return { type: "ir.actions.client", tag: "soft_reload" };
        }

        const authorizationCode = loginResponse?.authResponse?.code || loginResponse?.code;
        if (!authorizationCode) {
            await env.services.orm.call("mail.gateway", "action_reset_signup_attempt", [
                [gatewayId],
                session,
            ]);
            env.services.notification.add(
                _t("Meta did not return an authorization code. Please try again."),
                { type: "warning" }
            );
            return { type: "ir.actions.client", tag: "soft_reload" };
        }

        const signupData = (signupAssets && signupAssets.data) || {};
        const result = await env.services.orm.call(
            "mail.gateway",
            "action_save_meta_credentials",
            [
                [gatewayId],
                session,
                authorizationCode,
                signupData.waba_id || false,
                signupData.phone_number_id || false,
                signupData.business_id || false,
            ]
        );

        return result || { type: "ir.actions.client", tag: "soft_reload" };
    } catch (error) {
        env.services.notification.add(
            error.message || _t("Could not complete the WhatsApp connection with Meta."),
            { title: _t("WhatsApp Onboarding"), type: "danger", sticky: true }
        );
        return { type: "ir.actions.client", tag: "soft_reload" };
    }
}

registry
    .category("actions")
    .add("xtendoo_whatsapp_onboarding_embedded_signup", xtendooWhatsappOnboardingEmbeddedSignup);
