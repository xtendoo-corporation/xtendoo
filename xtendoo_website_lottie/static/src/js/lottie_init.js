/** @odoo-module **/

const SELECTOR = '.xtd-lottie';
const INITIALIZED_FLAG = 'xtdLottieInitialized';
const OBSERVER_FLAG = '__xtdLottieObserverAttached';
const GLOBAL_NAMESPACE = 'xtdWebsiteLottie';

let missingLibraryLogged = false;

function parseBoolean(value, defaultValue = false) {
    if (value === null || value === undefined || value === '') {
        return defaultValue;
    }
    return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase());
}

function logMissingLibrary() {
    if (!missingLibraryLogged) {
        console.error('xtendoo_website_lottie: window.lottie no está disponible. Añade la librería oficial en static/lib/lottie/lottie.min.js.');
        missingLibraryLogged = true;
    }
}

function initLottieElement(element) {
    if (!element || element.dataset[INITIALIZED_FLAG] === '1') {
        return null;
    }

    if (!window.lottie || typeof window.lottie.loadAnimation !== 'function') {
        logMissingLibrary();
        return null;
    }

    const path = element.dataset.lottiePath;
    if (!path) {
        console.error('xtendoo_website_lottie: falta data-lottie-path en el elemento.', element);
        return null;
    }

    const renderer = element.dataset.lottieRenderer || 'svg';
    const loop = parseBoolean(element.dataset.lottieLoop, true);
    const autoplay = parseBoolean(element.dataset.lottieAutoplay, true);

    try {
        const animation = window.lottie.loadAnimation({
            container: element,
            renderer: renderer,
            loop: loop,
            autoplay: autoplay,
            path: path,
        });

        element.dataset[INITIALIZED_FLAG] = '1';
        element.__xtdLottieAnimation = animation;

        if (animation && typeof animation.addEventListener === 'function') {
            animation.addEventListener('data_failed', () => {
                console.error(`xtendoo_website_lottie: no se pudo cargar la animación Lottie desde ${path}.`);
            });
        }

        return animation;
    } catch (error) {
        console.error(`xtendoo_website_lottie: error al inicializar la animación ${path}.`, error);
        return null;
    }
}

function collectElements(root = document) {
    if (!root) {
        return [];
    }
    if (root.matches && root.matches(SELECTOR)) {
        return [root];
    }
    if (!root.querySelectorAll) {
        return [];
    }
    return Array.from(root.querySelectorAll(SELECTOR));
}

function initLottieAnimations(root = document) {
    return collectElements(root).map(initLottieElement).filter(Boolean);
}

function attachObserver() {
    if (!document.body || document.body[OBSERVER_FLAG]) {
        return;
    }

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    initLottieAnimations(node);
                }
            }
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    document.body[OBSERVER_FLAG] = observer;
}

function boot() {
    initLottieAnimations(document);
    attachObserver();
}

window[GLOBAL_NAMESPACE] = window[GLOBAL_NAMESPACE] || {};
window[GLOBAL_NAMESPACE].init = initLottieAnimations;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
} else {
    boot();
}
