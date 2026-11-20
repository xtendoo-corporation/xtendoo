import { t } from "@odoo/owl";
import { dialogProps } from "@web/core/dialog/dialog";
import { TitlePlugin } from "@web/core/browser/title_plugin";
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

const XTD_NAME = "Xtd";

// Odoo 20: los props por defecto viven en el esquema compartido ``dialogProps``.
dialogProps.title = t.string().optional(XTD_NAME);
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

// Odoo 20 sustituye el servicio de título por TitlePlugin: solo cambiamos el
// título por defecto (el que se muestra cuando ninguna vista aporta uno).
patch(TitlePlugin.prototype, {
    setup() {
        super.setup(...arguments);
        this.defaultTitle = XTD_NAME;
    },
});
