import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import {
    ClientErrorDialog,
    ErrorDialog,
    NetworkErrorDialog,
    odooExceptionTitleMap,
    RPCErrorDialog,
    RedirectWarningDialog,
    WarningDialog,
} from "@web/core/errors/error_dialogs";
import "@web/core/browser/title_service";

const XTD_NAME = "Xtd";

Dialog.defaultProps.title = XTD_NAME;
ErrorDialog.title = _t("Xtd Error");
ClientErrorDialog.title = _t("Xtd Client Error");
NetworkErrorDialog.title = _t("Xtd Network Error");

patch(RPCErrorDialog.prototype, {
    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
            return;
        }
        if (!this.props.type) {
            return;
        }
        const titles = {
            server: _t("Xtd Server Error"),
            script: _t("Xtd Client Error"),
            network: _t("Xtd Network Error"),
        };
        this.title = titles[this.props.type] || _t("Xtd Error");
    },
});

patch(WarningDialog.prototype, {
    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            return odooExceptionTitleMap.get(this.props.exceptionName).toString();
        }
        return this.props.title || _t("Xtd Warning");
    },
});

patch(RedirectWarningDialog.prototype, {
    setup() {
        super.setup();
        if (!this.title) {
            this.title = _t("Xtd Warning");
        }
    },
});

registry.category("services").add(
    "title",
    {
        start() {
            const titleCounters = {};
            const titleParts = {};

            function getParts() {
                return Object.assign({}, titleParts);
            }

            function setCounters(counters) {
                for (const key in counters) {
                    const value = counters[key];
                    if (!value) {
                        delete titleCounters[key];
                    } else {
                        titleCounters[key] = value;
                    }
                }
                updateTitle();
            }

            function setParts(parts) {
                for (const key in parts) {
                    const value = parts[key];
                    if (!value) {
                        delete titleParts[key];
                    } else {
                        titleParts[key] = value;
                    }
                }
                updateTitle();
            }

            function updateTitle() {
                const counter = Object.values(titleCounters).reduce(
                    (total, count) => total + count,
                    0
                );
                const name = Object.values(titleParts).join(" - ") || XTD_NAME;
                document.title = counter ? `(${counter}) ${name}` : name;
            }

            return {
                get current() {
                    return document.title;
                },
                getParts,
                setCounters,
                setParts,
            };
        },
    },
    { force: true }
);
