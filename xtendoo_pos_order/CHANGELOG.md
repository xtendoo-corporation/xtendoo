# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [19.0.1.0.0] - 2025-01-19

### Añadido

#### Funcionalidad principal
- Nuevo módulo `xtendoo_pos_order` para Odoo 19.0
- Campo `interface_type` en `pos.config` para elegir entre:
  - `frontend`: Interfaz JavaScript estándar del POS
  - `backend`: Gestión de órdenes desde el backend
- Redirección automática según el tipo de interfaz configurado
- Validación de creación de órdenes solo en modo backend
- Cálculos automáticos de totales, impuestos y descuentos

#### Modelos
- Extensión de `pos.config`:
  - Campo `interface_type` (Selection)
  - Método `open_ui()` sobrescrito para redirección
  - Método `_open_backend_orders_interface()` para abrir vista de órdenes
  - Método `open_existing_session_cb()` sobrescrito
- Extensión de `pos.order`:
  - Validación en `create()` para modo backend
  - Método `action_pos_order_paid()` mejorado
  - Método `action_pos_order_invoice()` mejorado
  - Cálculo automático de totales
- Extensión de `pos.order.line`:
  - Onchange de producto para autocompletar datos
  - Cálculos automáticos de línea

#### Vistas
- Vista heredada de `pos.config` con nuevo campo de configuración
- Vista heredada de `pos.order` (tree) con botón "Crear" habilitado
- Vista heredada de `pos.order` (form) mejorada para uso desde backend
- Nueva acción `action_pos_order_backend` para acceso directo
- Nuevo menú "Órdenes Backend" en Punto de Venta

#### Seguridad
- Permisos de acceso para `pos.order` y `pos.order.line`
- Roles para usuarios y administradores del POS

#### Documentación
- README.md con descripción completa del módulo
- INSTALL.md con guía detallada de instalación y uso
- Casos de uso y ejemplos prácticos
- Solución de problemas comunes
- Checklist de implementación

#### Tests
- Test de creación de orden en modo backend (éxito)
- Test de creación de orden en modo frontend (debe fallar)
- Test de creación desde UI (debe funcionar siempre)
- Test de creación con líneas de producto
- Test de redirección según modo
- Test de gestión de sesiones
- Test de asignación automática de sesión

#### Otros
- Hooks de post-instalación y desinstalación
- Página de descripción HTML para el módulo
- Archivo LICENSE (LGPL-3)
- Estructura completa de módulo Odoo estándar

### Notas técnicas

- Compatible con Odoo 19.0
- Dependencias: `point_of_sale`
- API moderna de Odoo (decoradores, env, etc.)
- Código documentado en español
- Reutilización de lógica estándar del POS

### Uso recomendado

Este módulo es ideal para:
- TPV sin pantalla táctil
- Órdenes telefónicas o por email
- Integración con flujo ERP estándar
- Personalización de flujos de venta
- Formación de personal en entorno familiar

---

## Formato de versiones

- **MAYOR.ODOO.MINOR.PATCH**
- MAYOR (19): Versión de Odoo
- ODOO (0): Compatibilidad con serie de Odoo
- MINOR (1): Nueva funcionalidad (backwards-compatible)
- PATCH (0): Correcciones de bugs (backwards-compatible)

