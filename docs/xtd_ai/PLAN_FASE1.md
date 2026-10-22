# Agente IA para Odoo 19 Community: plan de la Fase 1

> Estado: **revisado con las respuestas del 2026-10-20; pendiente del visto bueno
> final**. Decisiones de la Fase 0: confirmación de borradores configurable por usuario;
> código solo en local; base de pruebas nueva `ai_agent_test`; API de Anthropic directa.

## 1. Principio rector

**La barrera de seguridad vive dentro de Odoo; la inteligencia, fuera.** El servicio
externo puede fallar, ser atacado o recibir instrucciones maliciosas a través del LLM, y
aun así no puede hacer nada que el usuario no pueda hacer, ni confirmar o contabilizar
nada, porque Odoo solo ofrece un catálogo cerrado de herramientas que ejecuta con la
identidad real del usuario.

## 2. Componentes

| Componente                    | Dónde                      | Responsabilidad                                                                                                                                          |
| ----------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `xtd_ai`              | `odoo/custom/src/private/` | Tokens de identidad, autenticación propia, endpoint MCP de herramientas, registro de herramientas, guardas «solo borrador», auditoría, grupos y ajustes. |
| `xtd_ai_tools_sale`           | idem                       | Herramientas de ventas (`depends: sale_management`).                                                                                                     |
| `xtd_ai_tools_crm`            | idem                       | Herramientas de CRM (`depends: crm`).                                                                                                                    |
| `xtd_ai_tools_purchase`       | idem                       | Herramientas de compras (`depends: purchase`).                                                                                                           |
| `xtd_ai_tools_stock`          | idem                       | Herramientas de inventario (`depends: stock`).                                                                                                           |
| `xtd_ai_tools_account`        | idem                       | Herramientas de contabilidad (`depends: account`).                                                                                                       |
| `xtd_ai`                 | idem                       | Panel de chat OWL en la barra superior, conversaciones, tarjetas de confirmación, preferencias de usuario y notificaciones por bus.                      |
| `ai_service`                  | `~/Odoo_19/ai_service/`    | Servicio Python 3.12 (FastAPI): bucle del agente, capa de proveedor LLM, gestión de contexto y límites de coste. Sin estado propio de negocio.           |

Separar las herramientas por dominio permite instalar en cada cliente solo las de las
apps que tiene, sin dependencias rotas. Esto prepara el paso a multi-cliente.

## 3. Flujo de una petición

```
 Usuario (navegador)
   │ 1. escribe "hazme un presupuesto para Deco Addict con 5 sillas"
   ▼
 xtd_ai  (ruta auth='user', sesión Odoo normal)
   │ 2. guarda el mensaje en xtd.ai.message
   │ 3. emite un TOKEN CORTO firmado {uid, db, conv_id, run_id, company_ids, lang, tz, exp≈10 min}
   │ 4. POST ai_service /v1/runs  (cabecera con secreto de servicio + token)  → 202
   ▼
 ai_service
   │ 5. pide a Odoo el historial de la conversación y la lista de herramientas (con el token)
   │ 6. bucle LLM: Claude decide qué herramienta usar
   │ 7. tools/call → xtd_ai /xtd_ai/mcp (Authorization: Bearer <token>)
   ▼
 xtd_ai
   │ 8. valida el token (firma, caducidad, usuario activo e interno, grupo IA, conversación abierta)
   │ 9. reconstruye env: with_user(uid), su=False, allowed_company_ids, lang, tz, flag xtd_ai_run
   │10. valida argumentos con JSON Schema y ejecuta la herramienta (ACL y reglas de Odoo)
   │11. escritura con confirmación activada → NO crea; guarda xtd.ai.pending_action y devuelve
   │    "pendiente de confirmación"
   │12. audita (xtd.ai.audit) y devuelve un resultado mínimo (campos de la lista blanca)
   ▼
 ai_service
   │13. termina el bucle → POST respuesta final al gateway (post_reply, mismo token)
   ▼
 xtd_ai
   │14. guarda la respuesta y avisa al navegador por bus → aparece en el panel
   │15. si hay acción pendiente: tarjeta con vista previa y botones Crear / Cancelar
   │16. el usuario pulsa Crear → ruta auth='user' (sesión, NO token) ejecuta la acción
   │    validada como ese usuario → borrador creado y enlazado en el chat
```

Claves del flujo:

- **El LLM nunca ve el token** ni puede pasar `uid`, `company_id` de otra compañía o
  `context`. Las herramientas no tienen esos parámetros.
- **La confirmación la hace Odoo, no el LLM.** Confirmar una acción pendiente solo es
  posible con la sesión web del usuario, nunca con el token del servicio, así que el
  agente no puede «autoconfirmarse».
- **El servicio no guarda datos de negocio.** Odoo es la fuente de verdad del historial,
  lo que simplifica el RGPD y permite varias réplicas del servicio.
- El trabajo del LLM no ocupa un worker de Odoo: el servicio contesta 202 y responde
  después por el endpoint del gateway.

## 4. Identidad y tokens

- **Formato**: token firmado con HMAC-SHA256 (estructura tipo JWT compacta), con una
  clave secreta por base generada al instalar (`ir.config_parameter`, solo sistema) y
  rotable desde ajustes. Lleva `jti` y `run_id`.
- **Caducidad**: 10 minutos por ejecución. Sin renovación; una ejecución larga se corta
  con un mensaje claro.
- **Revocación**: cada llamada comprueba en la base que el usuario está activo, es
  interno (`share=False`), pertenece al grupo «Agente IA / Usuario», la conversación
  está abierta y la ejecución (`run_id`) no ha sido cancelada. Desactivar al usuario,
  quitarle el grupo, cerrar la conversación o rotar la clave lo invalida al momento.
- **Cambio de rol o compañía**: los permisos se leen de la base en cada llamada; las
  compañías del token se cruzan con las actuales del usuario (Odoo lanza `AccessError`
  si sobra alguna).
- **Ámbito**: el token solo sirve en las rutas `/xtd_ai/*` con un método de
  autenticación propio (`_auth_method_xtd_ai`; Odoo 19 no tiene `bearer_scope`). **No
  sirve en `/json/2`, `/web` ni XML-RPC.**
- **Servicio ↔ Odoo**: además, cada lado se autentica con un secreto de servicio
  compartido en variables de entorno (`XTD_AI_SERVICE_KEY`), para que nadie más pueda
  lanzar ejecuciones ni hacerse pasar por el servicio.

## 5. Modelo de amenazas

| #   | Amenaza                                                                                                                                 | Mitigación                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | **Inyección de prompt** en datos (nombre de contacto, nota, descripción de oportunidad, línea de factura) que pide al agente hacer algo | Los textos de registros se devuelven envueltos como datos no confiables y truncados; prompt de sistema que lo explica; **confirmación previa** de escrituras por defecto; ninguna herramienta envía correos, mensajes ni llama a URLs; todo lo que se crea queda en borrador.                                                                                                                                                               |
| T2  | **Escalada de privilegios** pidiendo al LLM actuar como otro usuario o compañía                                                         | El LLM no controla identidad ni contexto; uid y compañías salen del token firmado; Odoo valida `allowed_company_ids`.                                                                                                                                                                                                                                                                                                                       |
| T3  | **Robo del token**                                                                                                                      | Vida de 10 min, ligado a una conversación y ejecución, solo sirve en `/xtd_ai/*`, nunca se registra en logs, se transmite solo entre Odoo y el servicio por red interna.                                                                                                                                                                                                                                                                    |
| T4  | **Servicio comprometido**                                                                                                               | Solo puede hacer lo que permiten los tokens vigentes de esos minutos y el catálogo cerrado; no tiene credenciales de larga duración de usuarios ni acceso a la base.                                                                                                                                                                                                                                                                        |
| T5  | **Salto de «solo borrador»** (crear con `state='sale'`, `action_post`, automatizaciones que confirman al crear)                         | Tres capas: (a) el catálogo no ofrece esas acciones; (b) lista blanca de campos que excluye `state` y similares, y comprobación del estado tras crear; (c) **guarda en el ORM**: con el flag `xtd_ai_run` en el contexto, `action_confirm`, `button_confirm`, `action_post`, `button_validate`, `action_register_payment`, `unlink`, etc. lanzan error. Esto bloquea también automatizaciones (`base_automation`) disparadas por el agente. |
| T6  | **Exfiltración** de datos vía renderizado (imagen markdown con URL, enlaces)                                                            | El panel no muestra imágenes ni HTML del modelo; solo texto con formato básico y enlaces internos a registros de Odoo generados por el gateway, no por el LLM.                                                                                                                                                                                                                                                                              |
| T7  | **Fugas entre usuarios** en el servicio (caché, mezcla de conversaciones)                                                               | Servicio sin estado de negocio; cada ejecución lleva su token; cachés de prompt solo para la parte común (sistema y herramientas); tests específicos con dos usuarios concurrentes.                                                                                                                                                                                                                                                         |
| T8  | **Saltarse ACL** vía `sudo` en herramientas o campos relacionados                                                                       | Prohibido `sudo` en código de herramientas (revisión y test que lo detecta); env reconstruido con `su=False`; lecturas con `search_read`/`read_group` normales; campos fuera de lista blanca no se devuelven aunque el usuario pueda verlos.                                                                                                                                                                                                |
| T9  | **Abuso de coste o DoS**                                                                                                                | Límites por ejecución (iteraciones, llamadas a herramientas, tokens), cuota diaria por usuario y presupuesto mensual global, rate limit por usuario en Odoo.                                                                                                                                                                                                                                                                                |
| T10 | **Datos personales al proveedor LLM** (RGPD)                                                                                            | Minimización por lista blanca de campos, sin adjuntos, cuerpos de correo ni chatter; ver §10.                                                                                                                                                                                                                                                                                                                                               |
| T11 | **Manipulación de la auditoría**                                                                                                        | `xtd.ai.audit` solo se escribe desde el gateway; sin permisos de escritura ni borrado para nadie (incluido admin vía UI); retención por cron.                                                                                                                                                                                                                                                                                               |
| T12 | **Enumeración** con dominios sobre campos restringidos                                                                                  | Los filtros de las herramientas son parámetros tipados (fechas, estado, ids), no dominios libres; los que se construyen pasan por el ORM con permisos del usuario.                                                                                                                                                                                                                                                                          |

## 6. Catálogo de herramientas (MVP)

Leyenda: **L** = solo lectura; **B** = crea o modifica borrador (con confirmación si
está activada); **C** = crea un registro sin estado borrador (confirmación siempre). Los
permisos los aplica siempre Odoo; la columna «Grupo mínimo» solo sirve para no ofrecer
herramientas inútiles en `tools/list`.

### Comunes (`xtd_ai`)

| Herramienta           | Qué hace                                                                                                                                                                                                                                                                     | Modelo(s)                        | Tipo | Grupo mínimo         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ---- | -------------------- |
| `get_user_context`    | Usuario, compañías activas, idioma, zona horaria, fecha de hoy                                                                                                                                                                                                               | res.users, res.company           | L    | Agente IA / Usuario  |
| `load_skill`          | Carga las instrucciones detalladas de un área (ventas, compras, stock, contabilidad, CRM, contactos) solo cuando hacen falta                                                                                                                                                 | —                                | L    | Agente IA / Usuario  |
| `search_partners`     | Busca contactos por nombre, NIF, ciudad, ref; tipo cliente o proveedor                                                                                                                                                                                                       | res.partner                      | L    | Usuario interno      |
| `create_contact`      | Crea una empresa o persona (nombre, NIF, email, teléfono, dirección, empresa padre). Antes busca duplicados por NIF, email y nombre y los muestra. **Confirmación siempre obligatoria**, aunque el usuario la tenga desactivada, porque un contacto no tiene estado borrador | res.partner                      | C    | Contactos / creación |
| `get_partner_summary` | Ficha corta y totales visibles de ventas, compras, facturas pendientes                                                                                                                                                                                                       | res.partner + lecturas agregadas | L    | Usuario interno      |
| `search_products`     | Busca productos por nombre o referencia, precio y unidad                                                                                                                                                                                                                     | product.product                  | L    | Usuario interno      |

### Ventas y CRM (`xtd_ai_tools_sale`, `xtd_ai_tools_crm`)

| Herramienta             | Qué hace                                                       | Modelo(s)         | Tipo | Grupo mínimo               |
| ----------------------- | -------------------------------------------------------------- | ----------------- | ---- | -------------------------- |
| `search_sale_orders`    | Filtra por cliente, estado, fechas, comercial, importe         | sale.order        | L    | Ventas / Usuario (propios) |
| `get_sale_order`        | Cabecera y líneas                                              | sale.order(.line) | L    | idem                       |
| `sales_report`          | Agregados por cliente, producto, comercial o mes               | sale.report       | L    | idem                       |
| `create_sale_quotation` | Presupuesto nuevo con líneas                                   | sale.order        | B    | idem                       |
| `add_sale_order_lines`  | Añade líneas a un presupuesto **en borrador**                  | sale.order.line   | B    | idem                       |
| `search_opportunities`  | Filtra por etapa, comercial, equipo, cliente, ingresos, fechas | crm.lead          | L    | Ventas / Usuario           |
| `get_opportunity`       | Detalle                                                        | crm.lead          | L    | idem                       |
| `pipeline_report`       | Agregados por etapa, comercial o equipo                        | crm.lead          | L    | idem                       |
| `create_opportunity`    | Oportunidad nueva (sin ganar ni perder)                        | crm.lead          | B    | idem                       |

### Compras e inventario (`xtd_ai_tools_purchase`, `xtd_ai_tools_stock`)

| Herramienta              | Qué hace                                                | Modelo(s)                    | Tipo | Grupo mínimo         |
| ------------------------ | ------------------------------------------------------- | ---------------------------- | ---- | -------------------- |
| `search_purchase_orders` | Filtra por proveedor, estado, fechas, importe           | purchase.order               | L    | Compras / Usuario    |
| `get_purchase_order`     | Cabecera y líneas                                       | purchase.order(.line)        | L    | idem                 |
| `purchase_report`        | Agregados por proveedor, producto o mes                 | purchase.report              | L    | idem                 |
| `create_purchase_rfq`    | Solicitud de presupuesto nueva                          | purchase.order               | B    | idem                 |
| `get_stock_levels`       | Disponible, previsto y reservado por producto y almacén | stock.quant, product.product | L    | Inventario / Usuario |
| `search_pickings`        | Albaranes por tipo, estado, socio, fecha, origen        | stock.picking                | L    | idem                 |
| `get_picking`            | Detalle con movimientos                                 | stock.picking, stock.move    | L    | idem                 |
| `stock_move_history`     | Movimientos de un producto en un periodo                | stock.move.line              | L    | idem                 |

### Contabilidad (`xtd_ai_tools_account`)

| Herramienta                    | Qué hace                                                                                   | Modelo(s)           | Tipo | Grupo mínimo |
| ------------------------------ | ------------------------------------------------------------------------------------------ | ------------------- | ---- | ------------ |
| `search_invoices`              | Facturas y rectificativas de cliente o proveedor por estado, pago, socio, fechas, vencidas | account.move        | L    | Facturación  |
| `get_invoice`                  | Cabecera, líneas, impuestos, pendiente                                                     | account.move(.line) | L    | idem         |
| `receivables_payables_summary` | Pendiente de cobro o pago por socio y antigüedad                                           | account.move        | L    | idem         |
| `create_customer_invoice`      | Factura de cliente en borrador                                                             | account.move        | B    | idem         |
| `create_vendor_bill`           | Factura de proveedor en borrador                                                           | account.move        | B    | idem         |

**Fuera del catálogo, a propósito:** confirmar, aprobar, contabilizar, validar
albaranes, registrar pagos, cancelar, borrar, enviar correos o mensajes, notas en
chatter, cambiar etapas a ganado o perdido, modificar o archivar contactos existentes.

**Diseño común de las herramientas:**

- Parámetros tipados con JSON Schema estricto (`additionalProperties: false`).
- Resultados JSON compactos: máximo 50 filas por defecto y 200 como tope, importes con
  moneda, textos truncados y marcados como no confiables.
- Cada resultado incluye ids para que el gateway genere los enlaces internos.
- Una herramienta se declara con un decorador o registro en Python dentro de su módulo;
  no se usan server actions editables, para que el catálogo no se pueda ampliar desde la
  UI sin desplegar código.

## 7. Capa de proveedor LLM, contexto y costes

**Interfaz neutra en `ai_service/domain/`:** `LLMProvider.complete(request) -> response`
con tipos propios (mensajes, especificaciones de herramienta en JSON Schema, llamadas a
herramienta, uso de tokens, motivo de parada). El dominio no importa ningún SDK.

**Adaptadores en `ai_service/providers/`:**

- `anthropic.py`: SDK oficial `anthropic`, tool use, streaming, prompt caching y manejo
  de `refusal`.
- `fake.py`: proveedor con guion para tests (determinista, sin red, sin coste).
- Futuro: `bedrock.py` y `vertex.py` (Claude en región UE) u `openai.py`, cada uno solo
  un adaptador más una entrada de configuración.

**Configuración por variables de entorno:** `XTD_AI_PROVIDER=anthropic`, `XTD_AI_MODEL`,
`XTD_AI_EFFORT`, `ANTHROPIC_API_KEY`.

**Elección de modelo: el más barato que haga bien la tarea.** El trabajo de razonar se
pone en el diseño, no en el modelo:

- Herramientas muy concretas (no CRUD genérico), con descripciones precisas, esquemas
  estrictos y resultados ya agregados. El modelo elige y rellena; no programa.
- **Skills por área**: el prompt de sistema es corto y común. Las instrucciones de cada
  área (cómo se arma un presupuesto, qué significa «vencida», cómo responder sobre
  stock) se cargan con `load_skill` solo cuando hacen falta.
- `tools/list` solo ofrece las herramientas de las apps y grupos del usuario. Un
  almacenero no recibe las de contabilidad.
- Candidatos: **`claude-haiku-5-5`** (0,10 $ / 0,50 $ por millón de tokens de entrada /
  salida) y **`claude-sonnet-5-5`** (2 $ / 10 $), ambos con esfuerzo `low`.
  `claude-opus-5-5` (4 $ / 20 $) queda descartado como defecto.
- Se decide con el banco de preguntas (§8): coste **por tarea bien resuelta**, no por
  llamada. Un modelo barato que necesita reintentos o se equivoca al elegir el producto
  acaba saliendo caro.
- Un solo modelo por conversación. Cambiar de modelo a mitad pierde la caché, que es por
  modelo. Si Haiku falla en una área concreta, la opción es fijar ese modelo por skill o
  por tipo de petición, pero solo si las pruebas lo justifican.

**Contexto:**

- Prompt de sistema fijo en español y lista de herramientas estable y ordenada, con
  `cache_control` para cachearlos. Los datos variables (fecha, usuario, compañía) van
  después del punto de caché.
- Historial: últimos N turnos de la conversación; los resultados de herramientas
  antiguos se resumen o se sustituyen por un marcador.
- Resultados de herramientas acotados en tamaño por el gateway.

**Límites: medir primero, limitar después.**

- En la fase de pruebas **no hay límites de coste** ni cuotas.
- Sí se **registra el uso** de cada ejecución en Odoo: modelo, tokens de entrada, salida
  y caché, coste estimado, iteraciones, herramientas llamadas, usuario y compañía. Con
  un informe por usuario, día y compañía se fijarán los límites según el presupuesto de
  cada empresa.
- Única excepción, técnica y no de coste: un **tope de seguridad de 30 iteraciones por
  ejecución** para cortar bucles infinitos por un fallo. Se registra cuando salta.
- Los límites de producción (por ejecución, cuota diaria por usuario, presupuesto
  mensual por compañía) quedan diseñados como ajustes desactivados, para activarlos sin
  tocar código.

## 8. Estrategia de pruebas

**Base `ai_agent_test`** (nueva, Community, con datos demo):

- Módulos: `sale_management`, `purchase`, `stock`, `account`, `crm`, `l10n_es` y los
  addons `xtd_ai_*`.
- Dos compañías: «Xtendoo Demo SL» y «Xtendoo Demo Norte SL».
- Al menos cuatro usuarios: comercial (ventas y CRM, solo sus documentos), jefe de
  ventas (todos los documentos de ventas), administración (facturación y compras, sin
  inventario) y almacén (inventario, sin ventas ni contabilidad). Uno de ellos con
  acceso a las dos compañías.
- Registros «trampa» con inyecciones de prompt en nombres, notas y descripciones.
- Todo creado por un script de seed reproducible.

**Niveles de prueba:**

| Nivel              | Qué                                                                                                                                                                        | Cómo                                                                                     |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Unitarias Odoo     | Tokens (caducado, alterado, usuario inactivo, sin grupo, compañía ajena, conversación cerrada, uso en `/json/2` rechazado), guardas ORM, lista blanca de campos, auditoría | `TransactionCase`/`HttpCase`, `invoke test` en Doodba                                    |
| Matriz de permisos | Cada usuario × cada herramienta: lo permitido funciona y lo prohibido da error de acceso, a través del endpoint del agente                                                 | Tests parametrizados en Odoo                                                             |
| Solo borrador      | Cada herramienta B deja el registro en borrador; intentos de colar `state`, automatización que confirma al crear, llamada directa a `action_post` con el flag: todo falla  | Tests Odoo                                                                               |
| Servicio           | Bucle, límites, adaptador de proveedor (respuestas grabadas), contrato de herramientas                                                                                     | `pytest` con `FakeProvider`                                                              |
| Integración        | Stack Doodba con el servicio real y `FakeProvider` con guiones maliciosos (pedir confirmar, cambiar de compañía, leer lo que el rol no permite)                            | `pytest` contra el stack local                                                           |
| Inyección          | Registros trampa y peticiones insistentes del usuario con el modelo real                                                                                                   | Banco de pruebas manual con clave real                                                   |
| Calidad            | Unas 40 preguntas reales en español (ventas, compras, stock, contabilidad, CRM) con respuesta esperada calculada desde la base                                             | Script de evaluación con clave real; solo se ejecuta con tu permiso porque cuesta dinero |

## 9. Despliegue

**Desarrollo local (Doodba):**

- `ai_service` como servicio nuevo en `devel.yaml`, en la red interna del stack, con su
  propia imagen (`ai_service/Dockerfile`).
- Salida a internet del servicio **solo hacia `api.anthropic.com`**, con un segundo
  `egress-gatekeeper` (mismo patrón que Odoo).
- Odoo llega al servicio por la red interna; no hace falta abrir el gatekeeper de Odoo a
  internet.
- Secretos en `.docker/ai.env` (ignorado por git), con un `.docker/ai.env.example` sin
  valores reales.
- Los addons en `odoo/custom/src/private/` se cargan sin tocar `addons.yaml`.

**Producto multi-cliente (más adelante):**

- Una instancia Odoo y un `ai_service` por cliente, con la misma imagen del servicio
  versionada.
- Bloque equivalente en `prod.yaml`, con secretos por cliente en su `.env`.
- Nada del diseño depende de una única instancia.

## 10. RGPD (anotación inicial)

- Anthropic actúa como **encargado del tratamiento**: firmar su DPA, revisar la política
  de retención vigente de la API y valorar retención cero si el contrato lo permite.
- Hay **transferencia internacional** (EE. UU.): documentarla con las garantías
  aplicables. Para clientes que exijan residencia en la UE se usará el adaptador de
  Bedrock o Vertex en región UE.
- Al LLM llegan solo los campos de la lista blanca: ni adjuntos, ni chatter, ni correos.
  Los datos de empleados se limitan al nombre del comercial.
- Hay que actualizar el registro de actividades de tratamiento e informar a los usuarios
  de que el chat usa un proveedor externo.
- La auditoría y las conversaciones tienen una retención configurable, con borrado por
  cron.
- Para el producto se necesitará un contrato de encargo con cada cliente y una plantilla
  de cláusula sobre el uso de IA.

## 11. Hitos y reparto

Antes de lanzar subagentes, **yo escribo el contrato**: formato del token, endpoints
`/xtd_ai/*`, esquema MCP de herramientas, formato de resultados y errores, y API
`/v1/runs`. Así los subagentes trabajan en paralelo sin pisarse.

| Hito | Contenido                                                                                                                                  | Quién                                               | Depende de | Paralelo con |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- | ---------- | ------------ |
| H0   | Contrato (`docs/ai_agent/CONTRACT.md`), base `ai_agent_test` y script de seed                                                              | Yo + subagente **QA/infra**                         | —          | —            |
| H1   | `xtd_ai`: token, autenticación, endpoint MCP, registro, guardas ORM, auditoría, grupos, ajustes y sus tests                        | Subagente **Addon Odoo**                            | H0         | H2           |
| H2   | `ai_service`: interfaz de proveedor, adaptadores Anthropic y Fake, bucle, cliente MCP, API `/v1/runs`, límites, tests `pytest`, Dockerfile | Subagente **Proveedor LLM / Backend**               | H0         | H1           |
| H3a  | `xtd_ai_tools_sale` y sus tests de permisos                                                                                                | Subagente **Backend / herramientas**                | H1         | H3b, H3c, H4 |
| H3b  | `xtd_ai_tools_purchase`, `xtd_ai_tools_stock` y sus tests de permisos                                                                                      | Subagente **Backend / herramientas**                | H1         | H3a, H3c, H4 |
| H3c  | `xtd_ai_tools_account` y sus tests de permisos                                                                                             | Subagente **Backend / herramientas**                | H1         | H3a, H3b, H4 |
| H4   | `xtd_ai`: panel OWL, conversaciones, bus, tarjetas de confirmación, preferencias                                                      | Subagente **Addon Odoo**                            | H1         | H3           |
| H5   | Integración en Doodba, suite de inyección y banco de preguntas en español                                                                  | Subagente **QA**                                    | H2, H3, H4 | —            |
| H6   | Revisión adversarial y correcciones                                                                                                        | Subagente **Seguridad** (y luego quien corresponda) | H5         | —            |
| H7   | Documentación en español (instalación, configuración, operación, RGPD) y verificación final en el stack local                              | Yo + subagente **docs**                             | H6         | —            |

Todos los subagentes con `model: "sonnet"`. Yo reviso cada entrega leyendo el código y
ejecutando los tests antes de darla por buena. Las pruebas con la clave real de
Anthropic (cuestan dinero) las ejecuto solo cuando me des permiso y una clave en
variable de entorno.

## 12. Decisiones tomadas tras la revisión

1. **Confirmación**: cada usuario la activa o desactiva en sus preferencias; el
   administrador puede forzarla para todos. Para contactos es siempre obligatoria.
2. **Contactos**: se pueden crear (`create_contact`), con búsqueda de duplicados y
   confirmación obligatoria. No se modifican ni archivan.
3. **Modelo**: **Claude Haiku 5.5 con esfuerzo bajo es el modelo por defecto** (decisión
   del 2026-10-20 tras el banco: 45/49 a la primera, 48/49 tras corregir herramientas y
   skills, ~0,0007 $ por pregunta, 7,4 s de media). Los fallos se corrigen afinando
   herramientas y skills, no subiendo de modelo. Sonnet 5.5 solo se valoraría para casos
   concretos que Haiku no resuelva tras afinar.
4. **Límites**: ninguno de coste durante las pruebas; se registra todo el uso. Solo un
   tope técnico de 30 iteraciones contra bucles.
5. **Servicio** dentro de `devel.yaml`.
