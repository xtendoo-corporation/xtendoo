# Contrato técnico: agente IA para Odoo 19 (v1)

> Fuente de verdad para todos los componentes. Si un subagente necesita cambiar algo de
> aquí, **no lo cambia por su cuenta**: lo propone en su informe final. Plan de
> referencia: `docs/ai_agent/PLAN_FASE1.md`.

## 0. Reglas generales

- Odoo 19 Community (OCB), Python 3.12. Sin Enterprise. No se toca OCB, OCA ni repos de
  clientes. Todo el código nuevo vive en:
  - Addons: `odoo/custom/src/private/xtd_ai_*` (prefijo técnico `xtd_ai`).
  - Servicio: `~/Odoo_19/ai_service/`.
  - Scripts: `~/Odoo_19/scripts/ai_agent/`. Documentación: `~/Odoo_19/docs/ai_agent/`.
- Licencia de los addons: `LGPL-3`, autor `Xtendoo`, versión `19.0.1.0.0`.
- Código, identificadores y comentarios en inglés; textos visibles al usuario, prompts y
  documentación en español (cadenas traducibles con `_()` / `env._()` en Odoo).
- Nunca secretos en ficheros versionados ni en logs. El token de usuario **nunca** se
  registra (como mucho, su `jti`).
- Base de pruebas: `ai_agent_test`. Usuarios de prueba: `ai_comercial`,
  `ai_jefe_ventas`, `ai_administracion`, `ai_almacen` (seed en `scripts/ai_agent/`).
  Registros de prueba con xmlid `xtd_ai_seed.*`.

## 1. Módulos

| Módulo                        | depends                                    | Contenido                                                                                                                                                                                     |
| ----------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `xtd_ai_gateway`              | `base`, `mail`, `bus`                      | Grupos, modelos núcleo (§5), token (§2), auth `xtd_ai` (§3), endpoint MCP (§4), registro de herramientas (§6), guardas «solo borrador» (§7), herramientas comunes (§8.1), auditoría, ajustes. |
| `xtd_ai_tools_sale`           | `xtd_ai_gateway`, `sale_management`, `crm` | Herramientas de ventas y CRM + skills `ventas`, `crm`. Guardas de `sale.order`, `crm.lead`.                                                                                                   |
| `xtd_ai_tools_purchase_stock` | `xtd_ai_gateway`, `purchase`, `stock`      | Herramientas de compras y stock + skills `compras`, `inventario`. Guardas de `purchase.order`, `stock.picking`.                                                                               |
| `xtd_ai_tools_account`        | `xtd_ai_gateway`, `account`                | Herramientas de contabilidad + skill `contabilidad`. Guardas de `account.move`, `account.payment`.                                                                                            |
| `xtd_ai_chat`                 | `xtd_ai_gateway`, `web`                    | Panel OWL en la barra superior, rutas de la UI (§9), preferencias de usuario.                                                                                                                 |

Grupos (en `xtd_ai_gateway`, categoría «Agente IA»):

- `xtd_ai_gateway.group_xtd_ai_user` «Usuario»: puede chatear.
- `xtd_ai_gateway.group_xtd_ai_manager` «Administrador» (implica usuario): ajustes,
  lectura de auditoría y uso de todos.

## 2. Token de ejecución

Formato: `xtdai1.<payload>.<firma>`

- `payload` = base64url sin relleno del JSON compacto (claves ordenadas) con:

| Clave         | Tipo      | Significado                                   |
| ------------- | --------- | --------------------------------------------- |
| `v`           | int       | Versión, `1`                                  |
| `db`          | str       | Nombre de la base                             |
| `uid`         | int       | Usuario                                       |
| `conv`        | int       | `xtd.ai.conversation` id                      |
| `run`         | int       | `xtd.ai.run` id                               |
| `cids`        | list[int] | Compañías permitidas; la primera es la activa |
| `lang`        | str       | Idioma del usuario, p. ej. `es_ES`            |
| `tz`          | str       | Zona horaria, p. ej. `Europe/Madrid`          |
| `iat` / `exp` | int       | Epoch en segundos; `exp = iat + 600`          |
| `jti`         | str       | 128 bits aleatorios en hex                    |

- `firma` = base64url sin relleno de `HMAC-SHA256(secret, "xtdai1." + payload)`.
- `secret`: `ir.config_parameter` `xtd_ai_gateway.token_secret`, 64 bytes aleatorios en
  hex generados al instalar si no existe. Rotarlo invalida todos los tokens vigentes.
- Comparación de firma con `hmac.compare_digest`.

**Verificación** (en este orden; cualquier fallo → 401 y auditoría `auth_failed` sin
token):

1. Prefijo, estructura y firma correctos.
2. `exp > now` (tolerancia 30 s).
3. `db` == base de la petición.
4. Usuario existe, `active`, `share = False` y pertenece a `group_xtd_ai_user`.
5. `xtd.ai.run` `run` existe, pertenece a `uid` y a `conv`, su `jti` coincide y su
   estado es `queued` o `running`.
6. Conversación `conv` en estado `open` y de `uid`.
7. `cids` ⊆ compañías actuales del usuario (si no, 403).

## 3. Autenticación `xtd_ai` (rutas servicio → Odoo)

- Método `_auth_method_xtd_ai` en `ir.http` (`xtd_ai_gateway/models/ir_http.py`).
- Cabeceras obligatorias:
  - `Authorization: Bearer <token>`
  - `X-XTD-AI-Service-Key: <XTD_AI_SERVICE_KEY>`
  - `X-Odoo-Database: <db>`
- La clave de servicio se lee de la **variable de entorno** `XTD_AI_SERVICE_KEY` del
  proceso de Odoo. Si no está definida, todas las rutas `xtd_ai` responden 503.
- Si todo es válido:
  `request.update_env(user=uid, context={allowed_company_ids: cids, lang, tz, xtd_ai_run: run_id})`,
  sesión sin guardar (`can_save = False`). Nunca `sudo` para datos del usuario.
- Estas rutas **no aceptan** cookie de sesión. Y el token **no sirve** fuera de
  `/xtd_ai/*` (no es una API key de Odoo, así que `/json/2`, `/web` y XML-RPC lo
  rechazan solos; hay un test que lo demuestra).

## 4. Endpoint MCP de herramientas

`POST /xtd_ai/mcp` · `auth='xtd_ai'` · `type='http'` · `csrf=False` ·
`methods=['POST']`. Cuerpo y respuesta: JSON-RPC 2.0 plano (no el envoltorio JSON-RPC de
Odoo). Sin notificaciones ni streaming. Una petición = un mensaje JSON-RPC.

### Métodos

| Método              | params                          | result                                                                                                      |
| ------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `initialize`        | `{protocolVersion, clientInfo}` | `{protocolVersion: "2025-06-18", serverInfo: {name: "xtd_ai_gateway", version}, capabilities: {tools: {}}}` |
| `tools/list`        | `{}`                            | `{tools: [Tool]}`, solo herramientas instaladas y cuyos `groups` tiene el usuario, ordenadas por nombre     |
| `tools/call`        | `{name, arguments}`             | `ToolResult`                                                                                                |
| `xtd_ai/history`    | `{}`                            | `History` (§4.3)                                                                                            |
| `xtd_ai/post_reply` | `Reply` (§4.4)                  | `{message_id}`                                                                                              |

`Tool` =
`{name, title, description, inputSchema, annotations: {readOnlyHint, destructiveHint: false, xtdKind: "read"|"draft"|"create", xtdSkill}}`.
`inputSchema` es JSON Schema con `type: object`, `additionalProperties: false` y
`required` explícito (compatible con `strict: true` de Anthropic).

### 4.1 ToolResult

```json
{
  "content": [{"type": "text", "text": "<JSON de structuredContent>"}],
  "structuredContent": { ... },
  "isError": false
}
```

`structuredContent` en caso de éxito:

```json
{
  "status": "ok",
  "data": { ... },
  "records": [{"model": "sale.order", "id": 7, "name": "S00007"}]
}
```

- `data`: resultado compacto y específico de la herramienta.
- Listas de `data` con tope de 50 filas por defecto y 200 como máximo, más
  `"truncated": true` y `"total": N` cuando se corta.
- Importes como `{"amount": 123.45, "currency": "EUR"}`. Fechas en ISO.
- **Texto libre** (nombres, notas, descripciones, líneas): siempre como objeto
  `{"untrusted_text": "...", "truncated": bool}`, cortado a 300 caracteres. Se exceptúan
  identificadores cortos (referencias, códigos, NIF, nombres de compañía/usuario y
  `name` de documentos tipo `S00007`).
- `records`: lo que el gateway convierte en enlaces internos en el chat. El LLM nunca
  construye URLs.

Escritura pendiente de confirmación:

```json
{
  "status": "pending_confirmation",
  "pending_action_id": 12,
  "summary": "Presupuesto para Deco Addict: 2 líneas, 1.250,00 € sin impuestos"
}
```

Error de herramienta (`isError: true`; el LLM lo ve y puede reaccionar):

```json
{
  "status": "error",
  "error": {
    "code": "access_denied",
    "message": "No tienes permiso para ver pedidos de compra."
  }
}
```

Códigos: `access_denied` (AccessError), `validation` (UserError/ValidationError o
argumentos que no cumplen el esquema), `not_found`, `draft_only` (guarda de §7),
`ambiguous` (varios candidatos; `data.candidates` con id y nombre), `internal`
(excepción inesperada, sin traza ni detalle interno).

### 4.2 Errores JSON-RPC (protocolo, no de herramienta)

| HTTP | code   | Cuándo                                                           |
| ---- | ------ | ---------------------------------------------------------------- |
| 401  | -32001 | Token o clave de servicio inválidos o caducados                  |
| 403  | -32003 | Compañía no permitida u otras comprobaciones de §2.7             |
| 409  | -32004 | Ejecución cancelada, terminada o tope de 30 iteraciones superado |
| 200  | -32601 | Método o herramienta inexistente o no visible para el usuario    |
| 200  | -32602 | params mal formados                                              |
| 503  | -32010 | Gateway sin configurar (`XTD_AI_SERVICE_KEY` ausente)            |

### 4.3 History

```json
{
  "user": {"name": "...", "lang": "es_ES", "tz": "Europe/Madrid"},
  "company": {"id": 1, "name": "Xtendoo Demo SL", "currency": "EUR"},
  "allowed_companies": [{"id": 1, "name": "..."}],
  "today": "2026-10-20",
  "confirm_writes": true,
  "messages": [{"role": "user"|"assistant", "text": "...", "date": "..."}]
}
```

Últimos 20 mensajes de la conversación en orden cronológico, incluido el mensaje que
inició la ejecución. Los mensajes del agente que dejaron una acción pendiente incluyen
su estado final (`"[Acción #12: creada S00042]"` / `"[Acción #12: cancelada]"`) para que
el modelo sepa qué pasó.

### 4.4 Reply

```json
{
  "text": "Respuesta en markdown básico",
  "status": "done" | "failed",
  "error": "mensaje corto si failed",
  "usage": {"provider": "anthropic", "model": "claude-haiku-5-5",
            "input_tokens": 0, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "iterations": 0, "tool_calls": 0, "cost_estimate": 0.0}
}
```

Odoo guarda el mensaje del asistente, cierra la ejecución con su uso, enlaza las
`pending_action` y los `records` creados en esa ejecución y avisa al navegador por bus
(§9).

**Límite técnico:** el gateway cuenta las `tools/call` de cada ejecución en
`xtd.ai.run.tool_calls`. El servicio corta a las 30 iteraciones del bucle del LLM. No
hay más límites de coste en esta fase.

## 5. Modelos núcleo (`xtd_ai_gateway`)

| Modelo                  | Campos principales                                                                                                                                                                                                                                                      | Acceso                                                                                                                                                                                             |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `xtd.ai.conversation`   | `name`, `user_id`, `company_id`, `state` (open/closed), `message_ids`, `run_ids`, `create_date`                                                                                                                                                                         | Regla: solo las del propio usuario; el administrador del agente, todas en lectura                                                                                                                  |
| `xtd.ai.message`        | `conversation_id`, `role` (user/assistant/notice), `body` (Text, sin HTML), `run_id`, `pending_action_ids`, `record_refs` (JSON)                                                                                                                                        | Como su conversación                                                                                                                                                                               |
| `xtd.ai.run`            | `conversation_id`, `user_id`, `state` (queued/running/done/failed/cancelled), `jti`, `provider`, `model`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_estimate`, `iterations`, `tool_calls`, `started_at`, `finished_at`, `error` | Usuario: lectura de las suyas. Escritura solo vía gateway (`sudo` comentado, campos de control)                                                                                                    |
| `xtd.ai.pending_action` | `run_id`, `conversation_id`, `user_id`, `tool_name`, `arguments` (JSON), `preview` (JSON), `state` (pending/confirmed/cancelled/expired/failed), `result_model`, `result_res_id`, `error`, `expires_at` (24 h)                                                          | Solo el propio usuario; confirmar requiere sesión web (§9)                                                                                                                                         |
| `xtd.ai.audit`          | `run_id`, `user_id`, `company_id`, `event` (tool_call/auth_failed/confirm/cancel/guard_blocked), `tool_name`, `arguments` (JSON, textos > 300 caracteres cortados), `outcome` (ok/error/pending/denied), `error_code`, `record_refs` (JSON), `duration_ms`              | Solo lectura para el administrador del agente; nadie escribe ni borra por UI (`create` vía `sudo` en el gateway). Retención por cron, 365 días por defecto (`xtd_ai_gateway.audit_retention_days`) |

`res.users`: campo `xtd_ai_confirm_writes` (Boolean, por defecto True), editable por el
propio usuario. Parámetro `xtd_ai_gateway.force_confirmation` (por defecto `False`): si
es `True`, la confirmación es obligatoria para todos.

## 6. Registro de herramientas

Cada módulo declara herramientas como métodos de un modelo abstracto que hereda de
`xtd.ai.toolbox` (definido en el gateway) y los decora con `@xtd_ai_tool(...)`:

```python
from odoo.addons.xtd_ai_gateway.tools import xtd_ai_tool

class XtdAiToolboxSale(models.AbstractModel):
    _name = "xtd.ai.toolbox.sale"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: sales"

    @xtd_ai_tool(
        name="create_sale_quotation",
        title="Crear presupuesto",
        description="...",            # español, preciso: cuándo usarla y cuándo no
        input_schema={...},
        kind="draft",                 # read | draft | create
        skill="ventas",
        groups=["sales_team.group_sale_salesman"],
        preview="_preview_create_sale_quotation",   # obligatorio si kind != read
    )
    def tool_create_sale_quotation(self, args):
        ...
        return {"data": {...}, "records": [order]}
```

- El gateway descubre las herramientas recorriendo los modelos que heredan de
  `xtd.ai.toolbox`. Nombres únicos; un duplicado bloquea el arranque con error claro.
- La herramienta recibe `args` ya validados con el esquema (librería `jsonschema` si
  está en la imagen; si no, un validador propio mínimo). Se ejecuta con `self.env` del
  usuario (`su=False`) y el contexto de §3.
- Devuelve `{"data": ..., "records": recordset | list}`; el gateway arma el
  `ToolResult`. Helpers en `xtd.ai.toolbox`: `_xtd_ai_text(value)`,
  `_xtd_ai_money(amount, currency)`, `_xtd_ai_resolve(model, name_or_id, domain=None)`
  (devuelve el registro o lanza el error `ambiguous` o `not_found`).
- **Prohibido `sudo()`** en código de herramientas. Hay un test que recorre el código de
  los módulos `xtd_ai_tools_*` y falla si aparece.
- **Escrituras** (`kind` draft/create): el gateway llama a `preview(args)` (solo
  lecturas, devuelve `{"summary": str, "lines": [...]}`). Si la confirmación es
  necesaria, crea `xtd.ai.pending_action` y devuelve `pending_confirmation`. Si no, o al
  confirmar, ejecuta la herramienta. Para `kind="create"` la confirmación es **siempre**
  obligatoria. La confirmación vuelve a validar `args` contra el esquema y ejecuta como
  el usuario de la sesión, con `xtd_ai_run` en el contexto.
- Cada llamada produce exactamente un registro `xtd.ai.audit`.

**Skills:** cada módulo registra sus textos (Markdown en español) en
`data/skills/<skill>.md` y declara
`_xtd_ai_skills = {"ventas": "data/skills/ventas.md"}` en su toolbox. La herramienta
común `load_skill` los sirve. La `description` de cada herramienta debe bastar para
usarla; la skill añade el criterio de negocio (qué preguntar antes de crear, cómo
interpretar «vencida», etc.).

## 7. Guardas «solo borrador»

Con `xtd_ai_run` en el contexto, estos métodos lanzan `UserError` con el código
`draft_only` (excepción `XtdAiDraftOnlyError`, subclase de `UserError`, definida en el
gateway). El gateway la convierte en `error.code = "draft_only"` y la audita como
`guard_blocked`.

| Módulo               | Modelo                | Métodos bloqueados                                                                                                                                                 |
| -------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| tools_sale           | `sale.order`          | `action_confirm`, `action_quotation_send`, `action_lock`, `action_cancel`, `_action_confirm`, `unlink`                                                             |
| tools_sale           | `crm.lead`            | `action_set_won`, `action_set_lost`, `action_set_won_rainbowman`, `unlink`                                                                                         |
| tools_purchase_stock | `purchase.order`      | `button_confirm`, `button_approve`, `action_rfq_send`, `button_cancel`, `unlink`                                                                                   |
| tools_purchase_stock | `stock.picking`       | `button_validate`, `action_confirm`, `action_assign`, `_action_done`, `unlink`                                                                                     |
| tools_account        | `account.move`        | `action_post`, `_post`, `button_cancel`, `action_register_payment`, `unlink`                                                                                       |
| tools_account        | `account.payment`     | `action_post`, `create`                                                                                                                                            |
| gateway              | `res.partner`         | `unlink`; `write` sobre partners existentes                                                                                                                        |
| gateway              | `mail.thread` (mixin) | `message_post` con `message_type` `comment` o `email` (el agente no escribe en el chatter ni envía correos). El tracking automático (`notification`) sí se permite |

Para no enviar avisos automáticos (p. ej. «se te ha asignado esta oportunidad»), el
gateway añade al contexto de toda ejecución `mail_auto_subscribe_no_notify=True` y
`mail_notify_force_send=False`. Así no se bloquea la creación, pero tampoco sale nada.

Además, en `create`/`write` dentro de `xtd_ai_run`, las herramientas usan listas blancas
explícitas de campos, y los campos de estado (`state`, `stage_id` a etapas ganadas,
`payment_state`…) nunca se aceptan. Tras crear, la herramienta comprueba que
`record.state == 'draft'`; si no, lanza `XtdAiDraftOnlyError` y la transacción se
revierte.

`create` de `res.partner` sí está permitido (herramienta `create_contact`), pero siempre
con confirmación. La guarda de `write` sobre partners no afecta a los cambios de campos
calculados o rangos (`customer_rank`/`supplier_rank`) que el ORM hace al crear
documentos; se implementa bloqueando solo las escrituras con campos de la lista
`_xtd_ai_protected_partner_fields` (nombre, NIF, email, teléfono, dirección, `active`,
cuentas bancarias, empresa padre).

## 8. Herramientas comunes (gateway)

### 8.1 En `xtd_ai_gateway`

| Herramienta           | Tipo   | Argumentos principales                                                                                                                      |
| --------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_user_context`    | read   | —                                                                                                                                           |
| `load_skill`          | read   | `skill` (enum de las skills instaladas)                                                                                                     |
| `search_partners`     | read   | `query`, `kind` (customer/supplier/any), `limit`                                                                                            |
| `get_partner_summary` | read   | `partner_id`                                                                                                                                |
| `search_products`     | read   | `query`, `limit`                                                                                                                            |
| `create_contact`      | create | `name`, `is_company`, `vat`, `email`, `phone`, `street`, `zip`, `city`, `country_code`, `parent_id`; el preview incluye posibles duplicados |

Las de ventas, compras, stock, contabilidad y CRM se detallan en el §6 del plan y las
implementa cada módulo de herramientas con este mismo contrato.

## 9. Chat (rutas de la UI, `xtd_ai_chat`)

Rutas `auth='user'`, `type='jsonrpc'` (sesión web normal, CSRF del cliente web):

| Ruta                           | Hace                                                                                            |
| ------------------------------ | ----------------------------------------------------------------------------------------------- |
| `/xtd_ai/chat/conversations`   | Lista las conversaciones del usuario                                                            |
| `/xtd_ai/chat/open`            | Abre una conversación nueva o devuelve la abierta                                               |
| `/xtd_ai/chat/messages`        | Mensajes de una conversación, con sus acciones pendientes                                       |
| `/xtd_ai/chat/send`            | Guarda el mensaje, crea `xtd.ai.run` y el token, llama al servicio (§10) y devuelve el `run_id` |
| `/xtd_ai/chat/pending/confirm` | Ejecuta la acción pendiente como el usuario de la sesión                                        |
| `/xtd_ai/chat/pending/cancel`  | Cancela la acción pendiente                                                                     |
| `/xtd_ai/chat/run/cancel`      | Cancela la ejecución en curso (`state = cancelled`)                                             |
| `/xtd_ai/chat/settings`        | Lee y escribe `xtd_ai_confirm_writes` (si no está forzado)                                      |

Bus:
`user.partner_id._bus_send("xtd_ai/update", {"conversation_id", "message_id", "run_id", "state"})`.
El panel vuelve a pedir los mensajes al recibirlo.

La UI muestra el texto del asistente con markdown básico (negrita, listas, tablas
simples) **sin HTML, sin imágenes y sin enlaces escritos por el modelo**. Los únicos
enlaces son los de `record_refs`, generados por Odoo (`/odoo/<model>/<id>`).

## 10. API del servicio (`ai_service`)

`POST {XTD_AI_SERVICE_URL}/v1/runs`

- Cabecera: `X-XTD-AI-Service-Key`.
- Cuerpo: `{"run_id": int, "conversation_id": int, "db": str, "token": str}`.
- Respuesta: `202 {"accepted": true}`, o 401 si la clave es inválida.
- El servicio procesa en segundo plano: `initialize`, `xtd_ai/history`, `tools/list` y
  el bucle LLM con `tools/call`, y termina **siempre** con `xtd_ai/post_reply` (también
  si falla, con `status: failed`).

`GET /healthz` → `{"status": "ok"}`.

La URL de Odoo la toma el servicio de su configuración (`XTD_AI_ODOO_URL`), nunca de la
petición. Odoo llama al servicio con un timeout de 5 s. Si falla, marca la ejecución
como `failed` y muestra un aviso en el chat.

Variables de entorno:

| Variable                | Dónde           | Ejemplo                        |
| ----------------------- | --------------- | ------------------------------ |
| `XTD_AI_SERVICE_KEY`    | Odoo y servicio | secreto aleatorio (≥ 32 bytes) |
| `XTD_AI_SERVICE_URL`    | Odoo            | `http://ai_service:8000`       |
| `XTD_AI_ODOO_URL`       | servicio        | `http://odoo:8069`             |
| `XTD_AI_PROVIDER`       | servicio        | `anthropic` \| `fake`          |
| `XTD_AI_MODEL`          | servicio        | `claude-haiku-5-5`             |
| `XTD_AI_EFFORT`         | servicio        | `low`                          |
| `XTD_AI_MAX_ITERATIONS` | servicio        | `30`                           |
| `ANTHROPIC_API_KEY`     | servicio        | (secreto)                      |

## 11. Servicio: capas

```
ai_service/
  pyproject.toml   Dockerfile   README.md
  xtd_ai_service/
    domain/      # tipos neutros (Message, ToolSpec, ToolCall, Usage, LLMRequest/Response),
                 # protocolo LLMProvider, AgentLoop, prompts/system_es.md
    providers/   # anthropic.py (SDK oficial anthropic), fake.py (guiones para tests)
    odoo/        # cliente MCP hacia /xtd_ai/mcp (httpx), errores tipados
    api/         # FastAPI: /v1/runs, /healthz
    config.py    # settings desde entorno (pydantic-settings)
  tests/
```

- `domain` no importa `anthropic`, `httpx` ni `fastapi`.
- Mapeo de herramientas: `inputSchema` de MCP → `input_schema` con `strict: true` en el
  adaptador de Anthropic.
- Caché de prompt: herramientas y prompt de sistema estables y ordenados, con
  `cache_control` al final del bloque estable; el contexto variable (usuario, fecha,
  compañía) va en el primer mensaje, no en `system`.
- El token solo vive en memoria durante la ejecución y nunca va al LLM ni a los logs.
- Costes: tabla de precios por modelo en configuración (USD por millón de tokens), usada
  para `cost_estimate`.

## 12. Cambios aceptados tras H1 (v1.1)

- `@xtd_ai_tool(..., requires=["product.product"])`: la herramienta solo se registra si
  esos modelos existen. `groups` se evalúa como «cualquiera de» (semántica de Odoo).
- Tope de llamadas a herramientas por ejecución: parámetro
  `xtd_ai_gateway.max_tool_calls_per_run` (por defecto 30) → 409 / -32004 al superarlo.
- Conversación cerrada → 401; ejecución terminada o cancelada → 409.
- Los métodos de herramienta son `@api.private` (no se pueden llamar por `/json/2`).
- Las vistas previas se ejecutan en un savepoint que siempre se revierte.
- `xtd.ai.audit` rechaza `write`/`unlink` incluso con sudo, salvo el cron de retención.
- Guarda adicional: crear `mail.mail` dentro de `xtd_ai_run` lanza
  `XtdAiDraftOnlyError`.
- Base de tests reutilizable: `odoo.addons.xtd_ai_gateway.tests.common.XtdAiCase`
  (`start_run`, `tool_env`, `call`, `audits`…).
- API Python para el chat: `xtd.ai.conversation._xtd_ai_open()`,
  `conversation._xtd_ai_start_run(text) -> (run, token)`, `run.action_cancel()`,
  `run._xtd_ai_fail(error)`,
  `pending_action.action_confirm() -> {state, records, error}`,
  `pending_action.action_cancel()`, `conversation.action_close()`,
  `res.users._xtd_ai_needs_confirmation(kind)`,
  `res.users._xtd_ai_force_confirmation()`.

## 13. Cambios aceptados tras la prueba real con Haiku (v1.2)

- **Historial con herramientas usadas (§4.3):** cada mensaje `assistant` de
  `xtd_ai/history` incluye
  `tools_used: [{tool, outcome: "ok"|"error"|"pending"|"denied", records?: [{model, id, name}]}]`
  (puede ser lista vacía; máximo 30 herramientas y 5 registros por herramienta, nombres
  truncados a 60 caracteres). Sale de `xtd.ai.audit`; nunca incluye argumentos ni
  resultados. Los mensajes `user` no llevan el campo y el servicio tolera su ausencia.
  El servicio lo convierte en una línea `[Consultas hechas en esta respuesta: …]` (solo
  nombre y resultado) y el prompt de sistema indica no retractarse de respuestas previas
  sin motivo.
- **`add_sale_order_lines`** devuelve `added_lines` (producto, cantidad, precio,
  descuento, subtotal) y los importes del pedido.
- **`get_product_availability`** (ventas, solo lectura): disponibilidad de stock para
  comerciales sin permiso de inventario, con el env del usuario (requiere `stock`
  instalado; con `sale_stock` los comerciales pueden leer `stock.move`; si no, devuelve
  solo existencias y libre, sin previsto).
- **Multicompañía en herramientas:** argumento opcional `company` (id o nombre, solo
  entre las compañías activas del usuario), etiqueta `company` en resultados cuando hay
  varias compañías activas y totales separados por compañía en los informes.
- **Servicio:** `XTD_AI_PROVIDER_TIMEOUT` (30 s por defecto) antes de reintentar una
  llamada al proveedor.

## 14. Adjuntos en el chat (v1.3)

Objetivo: el usuario adjunta un documento (p. ej. la factura en PDF que le ha mandado un
proveedor) y el agente prepara el borrador correspondiente (factura de proveedor), que
queda con el documento original adjunto.

**Tipos y límites** (constantes en el gateway, configurables por parámetro):
`application/pdf`, `image/png`, `image/jpeg`, `image/webp`; máximo 10 MB por fichero, 5
ficheros por mensaje y 20 páginas por PDF. Fuera de límites → error en español al subir,
sin crear nada.

**Almacenamiento:** `ir.attachment` con `res_model = "xtd.ai.conversation"` y
`res_id = <conversación>`, creado con el env del usuario. `xtd.ai.message` gana
`attachment_ids` (Many2many). Se borran con la retención de conversaciones.

**Subida (xtd_ai_chat):** `POST /xtd_ai/chat/upload` (`type="http"`, `auth="user"`,
multipart, con CSRF del cliente web) → `{attachment_id, name, mimetype, size}`. Solo en
la conversación abierta del usuario. `/xtd_ai/chat/send` acepta `attachment_ids` (lista
de ids subidos a esa conversación y aún no enlazados a otro mensaje).

**API Python del gateway:** `conversation._xtd_ai_start_run(text, attachment_ids=None)`
valida (propietario, conversación abierta, tipo, tamaño, número) y enlaza los adjuntos
al mensaje del usuario. Un mensaje puede llevar solo adjuntos (texto vacío).

**Historial (§4.3):** los mensajes `user` incluyen
`attachments: [{id, name, mimetype, size}]` (sin contenido).

**Contenido para el servicio:** método MCP `xtd_ai/attachment` con params `{id}` →
`{id, name, mimetype, data_base64}`. Solo si el adjunto está enlazado a un mensaje de la
conversación de la ejecución del token y el usuario puede leerlo; si no, `-32003`. Se
audita como evento `attachment_read` (sin contenido).

**Servicio:** descarga y envía al modelo **solo los adjuntos del último mensaje del
usuario** (bloques `document` para PDF e `image` para imágenes, en el mismo turno). Los
de mensajes anteriores se mencionan como texto `[Adjunto anterior: factura.pdf (id 12)]`
sin reenviar el contenido. Tipos neutros en `domain/` (`Attachment`), mapeo en el
adaptador.

**Herramientas:** `create_vendor_bill` y `create_customer_invoice` aceptan
`attachment_id` opcional (un adjunto de la conversación actual). Al crear el borrador se
copia el adjunto al asiento (`res_model = "account.move"`, `res_id`) y se marca como
adjunto principal. La skill `contabilidad` explica cómo leer una factura: identificar al
proveedor por NIF y nombre (`search_partners`; si no existe, proponer `create_contact`),
fecha, número de factura del proveedor como `ref`, líneas e impuestos, y comprobar que
el total calculado por Odoo coincide con el del documento (avisar si no).

**Seguridad:** el contenido de un documento es **dato no confiable** (puede contener
instrucciones). Si el mensaje que inicia la ejecución lleva adjuntos, toda escritura de
esa ejecución exige confirmación, aunque el usuario tenga la confirmación desactivada.
El prompt de sistema lo explica. Nada del documento llega a logs.

## 15. Agente integrado en Odoo (v2.0)

Objetivo: **implantar = instalar módulos y poner la clave de Anthropic en Ajustes**. Sin
contenedores extra ni librerías nuevas en la imagen de Odoo. El servicio externo
(`ai_service`, §10–§11) sigue existiendo como modo alternativo.

**Módulo nuevo `xtd_ai_agent`** (depends: `xtd_ai_gateway`, `queue_job`). Contiene el
bucle del agente, la capa de proveedor y la ejecución en segundo plano. Es una
traducción **síncrona** del dominio de `ai_service` (`domain/`: tipos neutros, bucle,
precios, prompts; `providers/`: Anthropic y Fake). El dominio no importa nada de Odoo ni
de HTTP; el adaptador de Anthropic usa **`requests`** (ya está en la imagen de Odoo)
contra `POST https://api.anthropic.com/v1/messages`, con las mismas reglas que el
adaptador del servicio: `strict` dentro de los límites (20 herramientas, 24 parámetros
opcionales), quitar del esquema las restricciones no soportadas, caché en herramientas +
sistema + último bloque, bloques `document`/`image` para adjuntos,
`output_config.effort`, cabeceras `anthropic-version` y `anthropic-workspace-id`
(opcional), reintentos 408/409/429/5xx con espera exponencial (máx. 2) y timeout por
llamada.

**Puerto hacia Odoo en proceso** (sustituye al cliente MCP): `xtd_ai_gateway` expone
`env["xtd.ai.mcp"]._xtd_ai_dispatch(method, params)`, que ejecuta exactamente lo mismo
que el endpoint HTTP `/xtd_ai/mcp` para `initialize`, `tools/list`, `tools/call`,
`xtd_ai/history`, `xtd_ai/attachment` y `xtd_ai/post_reply`, con el mismo resultado JSON
y la misma auditoría, guardas y flujo de acciones pendientes. El endpoint HTTP pasa a
ser una capa fina sobre este método. Se llama con un env construido por
`env["xtd.ai.run"]._xtd_ai_runner_env(run)`: `with_user(run.user_id)`, `su=False`,
contexto `allowed_company_ids` (las `cids` guardadas en la ejecución), `lang`, `tz`,
`xtd_ai_run`, `mail_auto_subscribe_no_notify`, `mail_notify_force_send=False`. Antes de
cada llamada se revalida lo mismo que en el token (§2 pasos 4–7: usuario activo,
interno, con grupo; ejecución activa; conversación abierta; compañías permitidas). Las
ejecuciones guardan `cids` al crearse (`_xtd_ai_start_run`).

**Ejecución en segundo plano:**

- Al enviar (`/xtd_ai/chat/send`): si `XTD_AI_SERVICE_URL` está configurada, modo
  externo (como hasta ahora). Si no, modo integrado:
  - Con el ejecutor de `queue_job` activo (`queue_job` en `server_wide_modules`):
    `run.with_delay(channel="root.xtd_ai", max_retries=1, description=...)._xtd_ai_job_run()`.
    El trabajo se crea en la misma transacción que la ejecución, así que no hay carrera.
  - Si no: hilo de respaldo tras el commit (`cr.postcommit`) con cursor propio. En
    Ajustes se avisa de que conviene activar `queue_job` para producción.
- El trabajo nunca relanza la excepción hacia `queue_job` para un fallo «normal»
  (proveedor, Odoo): termina la ejecución con `post_reply` `failed` y un mensaje en
  español, para evitar reintentos que repitan llamadas pagadas. Tope de 30 iteraciones.
- Cancelar una ejecución desde el chat se respeta entre iteraciones del bucle.

**Configuración (Ajustes → Agente IA, solo administradores del sistema):** proveedor
(`anthropic` | `fake`), modelo (por defecto `claude-haiku-5-5`), esfuerzo (`low`),
timeout por llamada (30 s), workspace de Anthropic (opcional), registrar detalle de
errores 400 (desactivado), y la **clave de Anthropic** como campo contraseña guardado en
`ir.config_parameter` `xtd_ai_agent.anthropic_api_key` (solo `base.group_system`; nunca
se devuelve al cliente, el campo se muestra vacío con «clave configurada»). La variable
de entorno `ANTHROPIC_API_KEY` del contenedor, si existe, tiene prioridad. Un botón
«Probar conexión» hace una llamada mínima y muestra el resultado (sin datos de negocio).
Tabla de precios editable para `cost_estimate`.

**Red:** en Doodba, el gatekeeper de Odoo debe permitir `api.anthropic.com`
(`ALLOWED_HOSTS`). Fuera de Doodba no hace falta nada.

**Sin cambios** en seguridad: las herramientas, guardas, confirmaciones, adjuntos,
auditoría, multicompañía y el chat funcionan igual; el LLM sigue sin ver credenciales y
sin poder elegir usuario ni compañía.
