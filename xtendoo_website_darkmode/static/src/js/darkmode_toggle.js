/** @odoo-module **/

const root = document.documentElement;

function getStorageKey() {
    return `xtendoo_website_darkmode:${root.dataset.xtendooDarkmodeWebsiteId || "0"}`;
}

function getDefaultMode() {
    const defaultMode = root.dataset.xtendooDarkmodeDefault || "system";
    return ["light", "dark", "system"].includes(defaultMode) ? defaultMode : "system";
}

function getStoredMode() {
    try {
        const storedMode = window.localStorage ? window.localStorage.getItem(getStorageKey()) : null;
        return ["light", "dark", "system"].includes(storedMode) ? storedMode : null;
    } catch (_error) {
        return null;
    }
}

function setStoredMode(mode) {
    try {
        if (window.localStorage) {
            window.localStorage.setItem(getStorageKey(), mode);
        }
    } catch (_error) {
        // Ignore storage errors (private windows, restricted browsers, etc.).
    }
}

function getMediaQuery() {
    return window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
}

function resolveMode(mode) {
    if (mode === "system") {
        return getMediaQuery()?.matches ? "dark" : "light";
    }
    return mode === "dark" ? "dark" : "light";
}

function getPreferredMode() {
    return getStoredMode() || getDefaultMode();
}

function applyMode(mode) {
    const resolvedMode = resolveMode(mode);
    root.dataset.xtendooColorScheme = resolvedMode;
    root.dataset.bsTheme = resolvedMode;
    root.style.colorScheme = resolvedMode;
    updateButtons(resolvedMode);
}

function updateButtons(resolvedMode) {
    const nextLabelAttr = resolvedMode === "dark" ? "labelLight" : "labelDark";
    document.querySelectorAll("[data-xtendoo-darkmode-toggle]").forEach((button) => {
        const nextLabel = button.dataset[nextLabelAttr] || (resolvedMode === "dark" ? "Modo claro" : "Modo oscuro");
        button.dataset.mode = resolvedMode;
        button.setAttribute("aria-pressed", String(resolvedMode === "dark"));
        button.setAttribute("aria-label", nextLabel);
        button.setAttribute("title", nextLabel);
        const labelElement = button.querySelector(".xtd-darkmode-toggle__label");
        if (labelElement) {
            labelElement.textContent = nextLabel;
        }
    });
}

function bindButtons() {
    document.querySelectorAll("[data-xtendoo-darkmode-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const currentMode = root.dataset.xtendooColorScheme === "dark" ? "dark" : "light";
            const nextMode = currentMode === "dark" ? "light" : "dark";
            setStoredMode(nextMode);
            applyMode(nextMode);
        });
    });
}

function init() {
    if (root.dataset.xtendooDarkmodeEnabled !== "1") {
        return;
    }
    applyMode(getPreferredMode());
    bindButtons();

    const mediaQuery = getMediaQuery();
    if (!mediaQuery) {
        return;
    }

    const handleMediaChange = () => {
        const storedMode = getStoredMode();
        if (!storedMode || storedMode === "system") {
            applyMode(getPreferredMode());
        }
    };

    if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener("change", handleMediaChange);
    } else if (mediaQuery.addListener) {
        mediaQuery.addListener(handleMediaChange);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
    init();
}

