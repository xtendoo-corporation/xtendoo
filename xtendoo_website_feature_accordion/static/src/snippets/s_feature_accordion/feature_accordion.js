/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * FeatureAccordion — Interaction for the s_feature_accordion snippet.
 *
 * Handles:
 *  - Clicking an accordion item activates it and collapses siblings.
 *  - Swaps the hero image on the left with a smooth fade transition.
 *  - Works in both published view and Website Builder edit mode.
 */
export class FeatureAccordion extends Interaction {
    static selector = ".s_feature_accordion";

    setup() {
        this.imgEl = this.el.querySelector(".s_feature_accordion_img");
        this.items = [...this.el.querySelectorAll(".s_feature_accordion_item")];

        // Bind click handlers
        for (const item of this.items) {
            this.addListener(item, "click", (ev) => this._onItemClick(ev, item));
        }

        // Ensure the initially-active item's image is displayed
        const activeItem = this.el.querySelector(".s_feature_accordion_item.active");
        if (activeItem && this.imgEl) {
            const src = activeItem.dataset.featureImg;
            if (src) {
                this.imgEl.src = src;
            }
        }
    }

    /**
     * Handle click on an accordion item:
     *  1. If already active, do nothing (always one item open).
     *  2. Remove .active from all siblings.
     *  3. Add .active to clicked item.
     *  4. Trigger image swap with fade animation.
     *
     * @param {Event} ev
     * @param {HTMLElement} item
     */
    _onItemClick(ev, item) {
        // Prevent toggling the already-active item — we always keep one open
        if (item.classList.contains("active")) {
            return;
        }

        // Deactivate all items
        for (const other of this.items) {
            other.classList.remove("active");
        }

        // Activate clicked item
        item.classList.add("active");

        // Swap image with fade
        const newSrc = item.dataset.featureImg;
        if (newSrc && this.imgEl) {
            this._swapImage(newSrc);
        }
    }

    /**
     * Perform a fade-out → swap src → fade-in transition on the hero image.
     *
     * @param {string} newSrc  URL of the new image
     */
    _swapImage(newSrc) {
        // Skip if the image is already showing this source
        if (this.imgEl.src && this.imgEl.src.endsWith(newSrc)) {
            return;
        }

        // Start fade-out
        this.imgEl.classList.add("s_feature_accordion_img_fade_out");
        this.imgEl.classList.remove("s_feature_accordion_img_fade_in");

        // After the CSS transition completes, swap src and fade-in
        const onTransitionEnd = () => {
            this.imgEl.removeEventListener("transitionend", onTransitionEnd);
            this.imgEl.src = newSrc;

            // Once the new image is loaded, fade in
            const showImage = () => {
                this.imgEl.classList.remove("s_feature_accordion_img_fade_out");
                this.imgEl.classList.add("s_feature_accordion_img_fade_in");
            };

            if (this.imgEl.complete) {
                showImage();
            } else {
                this.imgEl.addEventListener("load", showImage, { once: true });
                // Fallback: if load event never fires (e.g. cached)
                this.waitForTimeout(showImage, 600);
            }
        };

        this.imgEl.addEventListener("transitionend", onTransitionEnd, { once: true });

        // Fallback in case transitionend doesn't fire (e.g. no transition on element)
        this.waitForTimeout(() => {
            if (this.imgEl.classList.contains("s_feature_accordion_img_fade_out")) {
                onTransitionEnd();
            }
        }, 500);
    }
}

registry
    .category("public.interactions")
    .add("xtendoo_website_feature_accordion.feature_accordion", FeatureAccordion);
