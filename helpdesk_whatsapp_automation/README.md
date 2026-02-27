# Helpdesk WhatsApp Automation

[![License: AGPL-3](https://img.shields.io/badge/licence-AGPL--3-blue.svg)](http://www.gnu.org/licenses/agpl)

Módulo para Odoo 18 que automatiza la creación y gestión de tickets de Helpdesk a través
de WhatsApp, incluyendo asignación automática de empleados, notificaciones por email y
espejo de conversaciones en el chatter del ticket.

## Tabla de Contenidos

- [Características](#características)
- [Dependencias](#dependencias)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Flujo de Trabajo](#flujo-de-trabajo)
- [Funcionalidades Detalladas](#funcionalidades-detalladas)
- [Estructura Técnica](#estructura-técnica)
- [Créditos](#créditos)

---

## Características

- **Creación automática de tickets** desde mensajes de WhatsApp.
- **Menú interactivo por tipo de ticket** (Duda, Error, Solicitud de Cambio) con prompts
  específicos.
- **Asignación automática** del encargado y empleado de comunicación del contacto.
- **Notificaciones por email** al abrir y cerrar tickets (al empleado y encargado de
  comunicación).
- **Espejo de conversaciones**: todos los mensajes de la conversación de WhatsApp se
  copian automáticamente al chatter del ticket de Helpdesk, incluyendo adjuntos.
- **Reproducción de audio inline**: los audios recibidos por WhatsApp (notas de voz) se
  reproducen directamente en Odoo sin necesidad de descargarlos.
- **Bypass de automatización**: si un cliente ya tiene un ticket abierto, los mensajes
  posteriores no vuelven a crear un ticket nuevo.

---

## Dependencias

| Módulo                            | Descripción                                      |
| --------------------------------- | ------------------------------------------------ |
| `helpdesk_mgmt`                   | Módulo base de gestión de tickets Helpdesk (OCA) |
| `helpdesk_type`                   | Tipos de ticket para Helpdesk                    |
| `mail_gateway_whatsapp_chatter`   | Integración de WhatsApp en el chatter de Odoo    |
| `mail_gateway_whatsapp_variables` | Variables de WhatsApp para plantillas            |

---

## Instalación

1. Colocar el módulo en la carpeta de addons de Odoo.
2. Actualizar la lista de módulos desde **Ajustes > Activar el modo desarrollador >
   Actualizar lista de módulos**.
3. Buscar **"Helpdesk WhatsApp Automation"** e instalarlo.
4. Reiniciar el servidor de Odoo para cargar los assets de JavaScript.

---

## Configuración

### 1. Manager de Comunicación por Defecto

Ir a **Servicio de Asistencia > Configuración > Ajustes** y configurar:

- **Manager de comunicación por defecto**: Usuario que se asignará automáticamente como
  encargado a todos los contactos que no tengan uno específico.
- **Plantilla de solicitud de incidencia**: Plantilla de WhatsApp que se enviará cuando
  un cliente inicie la creación de un ticket.

### 2. Contactos

En cada ficha de contacto se pueden configurar dos campos:

- **Encargado de comunicación**: El usuario responsable de gestionar la comunicación con
  este cliente (se asigna como `user_id` del ticket).
- **Empleado para comunicación**: El empleado asignado para la comunicación directa con
  el cliente (se asigna como `assigned_employee_id` del ticket).

> Si no se configura un encargado en el contacto, se usará el manager por defecto de la
> compañía.

---

## Flujo de Trabajo

### Ejemplo Completo

```
1. Cliente escribe por WhatsApp
   └── El sistema muestra un menú con los tipos de ticket:
       • Error
       • Consulta
       • Llamame

2. Cliente selecciona un tipo (ej: "Error")
   └── El sistema envía un prompt específico pidiendo detalles:
       "Gracias 👍 Para revisar la incidencia necesitamos que nos indiques:
        • Qué acción estabas realizando
        • Qué mensaje de error aparece (texto exacto)
        • En qué momento ocurre
        Si puedes adjuntar captura de pantalla, mejor aún."

3. Cliente describe el problema (texto + imagen/audio opcional)
   └── Se crea automáticamente un ticket de Helpdesk:
       • Número: HT00025
       • Nombre: "WhatsApp Incident: [primeras 50 letras]"
       • Cliente: [contacto vinculado]
       • Tipo: Error
       • Encargado (Manager): [usuario configurado en el contacto]
       • Empleado Asignado: [empleado configurado en el contacto]
       • Canal: WhatsApp
       • Adjuntos: se copian al ticket

4. Se envía email de notificación
   └── Al empleado asignado y al encargado de comunicación
       con enlace directo "Ver Ticket" en Odoo.

5. Conversación continua
   └── Todos los mensajes posteriores del cliente y del agente
       se copian automáticamente al chatter del ticket.
   └── Los audios de WhatsApp se pueden escuchar directamente
       en el chatter sin descargarlos.

6. Agente cierra el ticket (mueve a etapa "Cerrado")
   └── Se envía email de notificación de cierre
       al encargado y empleado de comunicación del contacto.
```

### Diagrama de Estados del Canal

```
┌──────────┐     Cualquier mensaje      ┌───────────────────┐
│   Idle   │ ─────────────────────────► │ waiting_incident  │
│          │     (si no hay ticket)      │                   │
└──────────┘                             └───────────────────┘
      ▲                                          │
      │          Ticket creado                    │
      └──────────────────────────────────────────┘
```

---

## Funcionalidades Detalladas

### Creación Automática de Tickets

Cuando un cliente sin ticket abierto escribe por WhatsApp:

1. Se muestra un menú con los **tipos de ticket** configurados en Odoo (datos de
   demostración: Duda, Error, Solicitud nuevo cambio).
2. Se solicitan detalles con un **prompt personalizado** según el tipo.
3. Se crea el ticket con toda la información del contacto.

### Notificaciones por Email

| Evento         | Destinatarios                                                     | Plantilla                                             |
| -------------- | ----------------------------------------------------------------- | ----------------------------------------------------- |
| Ticket creado  | Empleado asignado + Encargado                                     | `email_template_assigned_employee_whatsapp_ticket_v2` |
| Ticket cerrado | Empleado de comunicación + Encargado de comunicación del contacto | `email_template_closed_whatsapp_ticket`               |

Ambos emails incluyen un botón **"Ver Ticket"** que abre directamente el ticket en la
interfaz de Odoo.

### Espejo de Conversación en el Chatter

Todos los mensajes que se envían y reciben en el canal de WhatsApp de un cliente que
tiene un ticket abierto se copian automáticamente al **chatter** del ticket de Helpdesk.
Esto incluye:

- Mensajes de texto del cliente
- Respuestas del agente desde Odoo
- Imágenes y documentos adjuntos (se copian al ticket)
- Audios y notas de voz

### Reproducción de Audio Inline

Los archivos de audio recibidos por WhatsApp (notas de voz, audios `.ogg`, `.opus`,
`.mp3`, etc.) se reproducen directamente dentro de Odoo con controles de reproducción
nativos del navegador (play, pausa, barra de progreso), tanto en la conversación como en
el chatter del ticket. No es necesario descargarlos.

### Bypass de Automatización

Si un cliente ya tiene un ticket abierto (en cualquier etapa no cerrada), el sistema
**no** vuelve a mostrar el menú de creación de ticket. En su lugar, los mensajes fluyen
directamente a la conversación y se espejan al chatter del ticket existente.

---

## Estructura Técnica

### Modelos

| Modelo                  | Archivo                           | Descripción                                                        |
| ----------------------- | --------------------------------- | ------------------------------------------------------------------ |
| `helpdesk.ticket`       | `models/helpdesk_ticket.py`       | Añade `assigned_employee_id` y lógica de notificación al cerrar    |
| `discuss.channel`       | `models/discuss_channel.py`       | Campos de sesión WhatsApp y lógica de espejo de mensajes           |
| `mail.gateway.whatsapp` | `models/mail_gateway_whatsapp.py` | Procesamiento de mensajes entrantes y flujo de creación de tickets |
| `res.partner`           | `models/res_partner.py`           | Campos `communication_manager_id` y `communication_employee_id`    |
| `res.company`           | `models/res_company.py`           | Configuración de manager por defecto y plantilla de incidencias    |
| `res.config.settings`   | `models/res_config_settings.py`   | Interfaz de configuración                                          |

### Campos Principales

| Campo                          | Modelo            | Tipo                 | Descripción                                      |
| ------------------------------ | ----------------- | -------------------- | ------------------------------------------------ |
| `assigned_employee_id`         | `helpdesk.ticket` | Many2one (res.users) | Empleado asignado al ticket                      |
| `communication_manager_id`     | `res.partner`     | Many2one (res.users) | Encargado de comunicación del contacto           |
| `communication_employee_id`    | `res.partner`     | Many2one (res.users) | Empleado de comunicación del contacto            |
| `whatsapp_session_state`       | `discuss.channel` | Selection            | Estado de la sesión: `idle` / `waiting_incident` |
| `whatsapp_ticket_type_id`      | `discuss.channel` | Many2one             | Tipo de ticket seleccionado                      |
| `whatsapp_default_manager_id`  | `res.company`     | Many2one (res.users) | Manager por defecto para asignación              |
| `incident_request_template_id` | `res.company`     | Many2one             | Plantilla de WhatsApp para solicitud             |

### Assets (Frontend)

| Archivo                               | Descripción                                |
| ------------------------------------- | ------------------------------------------ |
| `static/src/js/audio_attachment.js`   | Parche OWL para detectar adjuntos de audio |
| `static/src/xml/audio_attachment.xml` | Template para renderizar `<audio>` inline  |
| `static/src/css/audio_attachment.css` | Estilos del reproductor                    |

---

## Créditos

### Autor

- [Xtendoo](https://github.com/xtendoo-corporation)

### Licencia

Este módulo está licenciado bajo AGPL-3.0. Ver
[LICENSE](http://www.gnu.org/licenses/agpl) para más detalles.
