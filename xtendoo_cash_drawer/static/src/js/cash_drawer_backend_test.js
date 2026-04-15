/** @odoo-module **/
/**
 * Acción cliente para probar la apertura del cajón portamonedas desde backend.
 *
 * Arquitectura: la prueba llama directamente al bridge local desde el navegador.
 * Esto obliga a que el bridge tenga CORS correcto y, si Odoo va por HTTPS,
 * que el bridge esté expuesto también por HTTPS.
 */
import { registry } from "@web/core/registry";
import { Component, useState, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import {
    buildCashDrawerUrl,
    buildCashDrawerHealthUrl,
    sendCashDrawerRequest,
    checkCashDrawerHealth,
} from "./cash_drawer_utils";

/**
 * Diálogo de prueba del cajón portamonedas.
 *
 * Muestra la configuración activa y permite:
 *  1. Comprobar el health check del bridge (GET /health).
 *  2. Enviar la señal de apertura (GET /open-drawer?printer=...).
 *
 * Toda la lógica de red ocurre en el navegador del usuario, nunca en Python.
 */
class CashDrawerTestDialog extends Component {
    static components = { Dialog };
    static props = {
        bridge_url: String,
        printer_name: { type: String, optional: true },
        api_key: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            sending: false,
            checking: false,
            error: null,
            healthResult: null,
            openResult: null,
        });
    }

    /** Config sintético para reutilizar las utilidades JS del POS */
    get _config() {
        return {
            cash_drawer_bridge_url: this.props.bridge_url,
            cash_drawer_printer_name: this.props.printer_name || "",
            cash_drawer_api_key: this.props.api_key || "",
        };
    }

    get openUrl() {
        try {
            return buildCashDrawerUrl(this._config);
        } catch {
            return "— (URL no construible con la configuración actual)";
        }
    }

    get healthUrl() {
        try {
            return buildCashDrawerHealthUrl(this._config);
        } catch {
            return "— (URL no construible)";
        }
    }

    get maskedKey() {
        const k = this.props.api_key || "";
        if (!k) return "— (sin API key)";
        if (k.length <= 4) return "*".repeat(k.length);
        return k.slice(0, 4) + "*".repeat(Math.min(k.length - 4, 12));
    }

    /** Comprueba el health check del bridge (GET /health). */
    async onCheckHealth() {
        if (this.state.checking) return;
        this.state.checking = true;
        this.state.healthResult = null;
        this.state.error = null;
        try {
            const result = await checkCashDrawerHealth(this._config);
            this.state.healthResult = result;
        } catch (err) {
            this.state.error = err.message || String(err);
        } finally {
            this.state.checking = false;
        }
    }

    /** Envía la señal de apertura al bridge (GET /open-drawer?printer=...). */
    async onSend() {
        if (this.state.sending) return;
        this.state.sending = true;
        this.state.openResult = null;
        this.state.error = null;
        try {
            const result = await sendCashDrawerRequest(this._config);
            this.state.openResult = result;
            this.notification.add("Señal de apertura enviada correctamente.", {
                type: "success",
            });
        } catch (err) {
            this.state.error = err.message || String(err);
            console.error("[CashDrawer] Error en prueba:", err);
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
                La prueba llama <strong>directamente al bridge local</strong> desde este navegador.
                Esto valida exactamente el mismo canal que usará el TPV real en esta máquina.
            </p>

            <!-- Configuración activa -->
            <h6 class="fw-bold">Configuración activa</h6>
            <table class="table table-sm table-bordered mb-3">
                <tbody>
                    <tr>
                        <th class="bg-light" style="width:35%">URL base del bridge</th>
                        <td><code class="text-break" t-esc="props.bridge_url || '— (no configurada)'"/></td>
                    </tr>
                    <tr t-if="props.printer_name">
                        <th class="bg-light">Impresora</th>
                        <td><code t-esc="props.printer_name"/></td>
                    </tr>
                    <tr>
                        <th class="bg-light">URL de apertura construida</th>
                        <td><code class="text-break text-primary" t-esc="openUrl"/></td>
                    </tr>
                    <tr>
                        <th class="bg-light">URL health check</th>
                        <td><code class="text-break" t-esc="healthUrl"/></td>
                    </tr>
                    <tr>
                        <th class="bg-light">Header <code>x-api-key</code></th>
                        <td>
                            <span t-if="props.api_key" class="font-monospace" t-esc="maskedKey"/>
                            <span t-else="" class="text-muted">— (sin API key)</span>
                        </td>
                    </tr>
                </tbody>
            </table>

            <!-- Resultado health check -->
            <div t-if="state.healthResult" class="mb-2">
                <div t-if="state.healthResult.available" class="alert alert-success py-2">
                    <i class="fa fa-check-circle me-1"/>
                    <strong>Bridge disponible:</strong>
                    <span t-esc="state.healthResult.detail"/>
                </div>
                <div t-else="" class="alert alert-warning py-2">
                    <i class="fa fa-exclamation-triangle me-1"/>
                    <strong>Bridge no disponible:</strong>
                    <span t-esc="state.healthResult.detail"/>
                </div>
            </div>

            <!-- Resultado apertura -->
            <div t-if="state.openResult" class="alert alert-success py-2 mb-2">
                <i class="fa fa-unlock me-1"/>
                Señal de apertura enviada correctamente.
            </div>

            <!-- Error -->
            <div t-if="state.error" class="alert alert-danger mt-2" role="alert">
                <i class="fa fa-exclamation-triangle me-1"/>
                <strong>Error:</strong><br/>
                <span style="white-space:pre-wrap;" t-esc="state.error"/>
                <hr class="my-2"/>
                <small class="text-muted">
                    Posibles causas:
                    <ul class="mb-0 mt-1">
                        <li>El bridge no está en ejecución.</li>
                        <li>La URL o el puerto configurados son incorrectos.</li>
                        <li>La web de Odoo va por HTTPS y el bridge sigue en HTTP.</li>
                        <li>El bridge no permite CORS para este origen.</li>
                        <li>Este navegador no puede alcanzar la IP del bridge por LAN.</li>
                        <li>El nombre de la impresora no coincide con el configurado en el bridge.</li>
                    </ul>
                </small>
            </div>
        </div>
    </t>
    <t t-set-slot="footer">
        <!-- Health check -->
        <button class="btn btn-outline-secondary"
                t-on-click="onCheckHealth"
                t-att-disabled="state.checking or state.sending">
            <i t-attf-class="fa me-1 {{ state.checking ? 'fa-spinner fa-spin' : 'fa-heartbeat' }}"/>
            <t t-if="state.checking">Comprobando…</t>
            <t t-else="">Verificar bridge</t>
        </button>
        <!-- Apertura -->
        <button class="btn btn-primary ms-2"
                t-on-click="onSend"
                t-att-disabled="state.sending or state.checking">
            <i t-attf-class="fa me-1 {{ state.sending ? 'fa-spinner fa-spin' : 'fa-unlock' }}"/>
            <t t-if="state.sending">Enviando…</t>
            <t t-else="">Abrir cajón</t>
        </button>
        <!-- Cerrar -->
        <button class="btn btn-secondary ms-2"
                t-on-click="onCancel"
                t-att-disabled="state.sending or state.checking">
            Cerrar
        </button>
    </t>
</Dialog>
`;
CashDrawerTestDialog.template = xml`${TEMPLATE}`;

/**
 * Registra la acción cliente en el registro de Odoo.
 *
 * Se activa cuando action_test_cash_drawer() devuelve:
 *   { type: "ir.actions.client", tag: "xtendoo_cash_drawer_open_test", params: {...} }
 */
registry.category("actions").add("xtendoo_cash_drawer_open_test", async (env, action) => {
    const params = action.params || {};
    const bridgeUrl = params.bridge_url || "";

    if (!bridgeUrl) {
        env.services.notification.add(
            "No hay URL del bridge configurada para el cajón portamonedas.",
            { type: "warning" }
        );
        return false;
    }

    env.services.dialog.add(CashDrawerTestDialog, {
        bridge_url: bridgeUrl,
        printer_name: params.printer_name || "",
        api_key: params.api_key || "",
    });
    return false;
});
