# Agente IA para Odoo 19: instalación y configuración

Asistente de IA dentro de Odoo 19 Community. Responde preguntas sobre ventas, compras,
inventario, contabilidad, CRM y contactos, y prepara **borradores** (presupuestos,
solicitudes de compra, facturas, oportunidades, contactos) que una persona revisa y
confirma. El agente actúa siempre con los permisos del usuario que chatea: no ve ni
hace nada que Odoo no le permita a esa persona.

## Módulos

| Módulo | Qué aporta | Obligatorio |
|---|---|---|
| `xtd_ai_gateway` | Barrera de seguridad: permisos, «solo borrador», auditoría, adjuntos | Sí |
| `xtd_ai_agent` | El agente en sí, dentro de Odoo, con `queue_job` y Claude | Sí |
| `xtd_ai_chat` | Chat: icono en la barra, ventana flotante y app «Asistente IA» | Sí |
| `xtd_ai_tools_sale` | Herramientas de ventas y CRM | Si se usan Ventas/CRM |
| `xtd_ai_tools_purchase_stock` | Herramientas de compras e inventario | Si se usan Compras/Inventario |
| `xtd_ai_tools_account` | Herramientas de contabilidad (facturas, cobros y pagos) | Si se usa Facturación |

Dependencia externa: **`queue_job`** (repositorio OCA `queue`, rama 19.0). No hace falta
instalar ninguna librería de Python nueva: el agente usa `requests`, que ya trae Odoo.

## 1. Configuración del servidor (una vez)

Añadir `queue_job` a los módulos de servidor para que arranque su ejecutor de trabajos en
segundo plano. En Doodba, un fichero `odoo/custom/conf.d/50-queue_job.conf`:

```ini
[options]
server_wide_modules = base,web,queue_job

[queue_job]
channels = root:2,root.xtd_ai:2
```

- `root.xtd_ai:2` = hasta 2 preguntas al agente a la vez. Súbelo si hay muchos usuarios.
- El ejecutor de `queue_job` solo atiende las bases de datos de `db_name` / `PGDATABASE`.
  En una instalación normal de Doodba hay una sola y no hay que hacer nada más.
- Sin esta configuración el agente **funciona igual** con un hilo de respaldo, pero en
  Ajustes aparece un aviso: para producción conviene `queue_job`.

**Salida a internet (solo Doodba con `egress-gatekeeper`):** permitir
`api.anthropic.com` en `ALLOWED_HOSTS` del servicio `gatekeeper` de Odoo.

Reiniciar Odoo.

## 2. Instalación

1. Añadir el repositorio `xtendoo` y el de OCA `queue` a `repos.yaml`/`addons.yaml` (si no
   están ya).
2. Instalar los módulos: `xtd_ai_agent`, `xtd_ai_chat` y las herramientas de las apps que
   use el cliente (`xtd_ai_tools_sale`, `xtd_ai_tools_purchase_stock`,
   `xtd_ai_tools_account`). Las dependencias (`xtd_ai_gateway`, `queue_job`) se instalan
   solas.

## 3. Configuración en Odoo

**Ajustes → Agente IA** (solo administradores):

1. Pegar la **clave de la API de Anthropic** y guardar. La clave no se vuelve a mostrar
   (aparece «Clave configurada»). Alternativa: variable de entorno `ANTHROPIC_API_KEY`
   en el contenedor, que tiene prioridad.
2. Si la clave de Anthropic no está ligada a un *workspace*, indicar el **ID del
   workspace** (o la variable de entorno `ANTHROPIC_WORKSPACE_ID`).
3. Pulsar **«Probar conexión»**. Debe responder OK.
4. Opcional: modelo (por defecto `claude-haiku-5-5`, el recomendado), esfuerzo (`low`),
   tiempo de espera por llamada (30 s) y tabla de precios para estimar el coste.

**Usuarios:** dar el grupo **Agente IA / Usuario** a quien vaya a usar el chat, y
**Agente IA / Administrador** a quien deba ver la auditoría y todas las conversaciones.
Cada usuario ve y crea solo lo que ya le permiten sus permisos de Odoo.

**Confirmación de escrituras:** por defecto cada borrador se muestra en una tarjeta para
aceptarlo o cancelarlo. Cada usuario puede desactivarla en el chat (menú «⋯»); el
administrador puede forzarla para todos. Crear contactos y cualquier escritura que parta
de un documento adjunto piden confirmación siempre.

## 4. Uso

- Icono del asistente en la barra superior: abre una conversación nueva en una ventana
  flotante. Los enlaces a registros se abren sin recargar y la ventana sigue abierta.
- App **Asistente IA** en el menú: chat a pantalla completa con el historial (las
  conversaciones antiguas son de solo lectura).
- Se pueden adjuntar PDF e imágenes (máx. 10 MB, 5 por mensaje), por ejemplo una factura
  de proveedor para preparar su borrador con el documento adjunto.

## 5. Qué no hace nunca

Confirmar, publicar, validar, pagar, cancelar o borrar documentos; enviar correos o
escribir en el chatter; ver o crear nada fuera de los permisos del usuario o de sus
compañías activas. Todo queda auditado en **Ajustes → Agente IA → Auditoría**.

## 6. Datos personales (RGPD)

Las preguntas, los datos que el agente consulta para responderlas y los documentos
adjuntos se envían a Anthropic (EE. UU.) para generar la respuesta. Antes de activarlo en
un cliente: contrato de encargo del tratamiento, DPA de Anthropic, información a los
usuarios y revisión de la retención. Las herramientas solo devuelven los campos
necesarios y las conversaciones se borran pasados 365 días (configurable).

## 7. Coste orientativo

Con Claude Haiku 5.5, unos 0,001–0,003 $ por pregunta (medido en pruebas). El coste de
cada ejecución queda registrado en Odoo.

## Documentación de diseño

- `PLAN_FASE1.md`: arquitectura, modelo de amenazas, catálogo de herramientas.
- `CONTRACT.md`: contrato técnico entre componentes (§15: agente integrado en Odoo).
- `CASOS_DE_USO.md`: casos de prueba por rol.
- `ESTUDIO_JEV.md`: estudio de un modelo alternativo de decisiones.
