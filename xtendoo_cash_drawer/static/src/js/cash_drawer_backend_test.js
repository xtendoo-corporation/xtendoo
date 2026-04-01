/** @odoo-module **/
/**
 * Acción cliente para probar la apertura del cajón portamonedas.
 * Muestra un diálogo con los datos de la petición y la envía a través
 * del proxy de Odoo (mismo origen, sin restricciones CORS).
 */
import { registry } from "@web/core/registry";
import { Component, useState, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
class CashDrawerTestDialog extends Component {
    static components = { Dialog };
    static props = {
        url: String,
        api_key: { type: String, optional: true },
        close: Function,
    };
    setup() {
        this.notification = useService("notification");
        this.state = useState({ sending: false, error: null, resolvedUrl: null });
    }
    get maskedKey() {
        const k = this.props.api_key || "";
        if (!k) return "— (sin API key)";
        if (k.length <= 4) return "*".repeat(k.length);
        return k.slice(0, 4) + "*".repeat(Math.min(k.length - 4, 12));
    }
    get curlCommandMasked() {
        const { url, api_key } = this.props;
        const header = api_key ? `-H "x-api-key: ${this.maskedKey}" ` : "";
        return `curl ${header}"${url}"`;
    }
    async onSend() {
        if (this.state.sending) return;
        this.state.sending = true;
        this.state.error = null;
        this.state.resolvedUrl = null;
        const { url, api_key } = this.props;
        try {
            const response = await fetch("/xtendoo_cash_drawer/open", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: { url, api_key: api_key || "" },
                }),
            });
            const json = await response.json();
            if (json.error) {
                throw new Error(json.error.data?.message || json.error.message || "Error en proxy Odoo");
            }
            const result = json.result || {};
            if (result.success) {
                this.state.resolvedUrl = result.resolved_url || url;
                this.notification.add("Señal de apertura del cajón enviada correctamente.", { type: "success" });
                this.props.close();
            } else {
                this.state.error = result.error || "El servicio respondió con un error desconocido.";
            }
        } catch (err) {
            this.state.error = err.message || String(err);
            console.error("[CashDrawer] Error:", err);
        } finally {
            this.state.sending = false;
        }
    }
    onCancel() {
        this.props.close();
    }
}
const TEMPLATE = /* xml */ `
<Dialog title="'Probar apertura del cajón portamonedas'">
    <t t-set-slot="default">
        <div class="mb-3">
            <p class="text-muted mb-3">
                La petición se enviará a través del <strong>proxy de Odoo</strong>
                con la cabecera <code>x-api-key</code> completa.
            </p>
            <table class="table table-sm table-bordered">
                <tbody>
                    <tr>
                        <th class="bg-light" style="width:30%">URL configurada</th>
                        <td><code class="text-break" t-esc="props.url"/></td>
                    </tr>
                    <tr>
                        <th class="bg-light">Header <code>x-api-key</code></th>
                        <td>
                            <span t-if="props.api_key" class="font-monospace" t-esc="maskedKey"/>
                            <span t-else="" class="text-muted">— (sin API key)</span>
                        </td>
                    </tr>
                    <tr>
                        <th class="bg-light">Método</th>
                        <td><code>GET</code></td>
                    </tr>
                </tbody>
            </table>
            <div class="mt-3">
                <label class="form-label fw-bold">Equivalente curl (desde el servidor):</label>
                <pre class="bg-dark text-light p-2 rounded small text-break"
                     style="white-space:pre-wrap;" t-esc="curlCommandMasked"/>
            </div>
            <div t-if="state.error" class="alert alert-danger mt-3" role="alert">
                <i class="fa fa-exclamation-triangle me-1"/>
                <strong>Error:</strong><br/>
                <span t-esc="state.error"/>
            </div>
        </div>
    </t>
    <t t-set-slot="footer">
        <button class="btn btn-primary"
                t-on-click="onSend"
                t-att-disabled="state.sending">
            <i t-attf-class="fa me-1 {{ state.sending ? 'fa-spinner fa-spin' : 'fa-unlock' }}"/>
            <t t-if="state.sending">Enviando…</t>
            <t t-else="">Enviar petición</t>
        </button>
        <button class="btn btn-secondary ms-2"
                t-on-click="onCancel"
                t-att-disabled="state.sending">
            Cancelar
        </button>
    </t>
</Dialog>
`;
CashDrawerTestDialog.template = xml`${TEMPLATE}`;
registry.category("actions").add("xtendoo_cash_drawer_open_test", async (env, action) => {
    const { url, api_key } = action.params || {};
    if (!url) {
        env.services.notification.add(
            "No hay URL configurada para el cajón portamonedas.",
            { type: "warning" }
        );
        return false;
    }
    env.services.dialog.add(CashDrawerTestDialog, { url, api_key: api_key || "" });
    return false;
});
