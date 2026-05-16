import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

function systemColorScheme() {
    return browser.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const colorSchemeService = {
    start() {
        const preference = user.settings?.color_scheme || "system";
        const targetColorScheme = preference === "system" ? systemColorScheme() : preference;
        const currentColorScheme = cookie.get("color_scheme");

        if (["light", "dark"].includes(targetColorScheme) && currentColorScheme !== targetColorScheme) {
            cookie.set("color_scheme", targetColorScheme);
            if (currentColorScheme || targetColorScheme === "dark") {
                browser.location.reload();
            }
        }

        return {
            get currentColorScheme() {
                return cookie.get("color_scheme") || targetColorScheme;
            },
            get systemColorScheme() {
                return systemColorScheme();
            },
            get userColorScheme() {
                return preference;
            },
        };
    },
};

registry.category("services").add("color_scheme", colorSchemeService, {
    force: true,
});

