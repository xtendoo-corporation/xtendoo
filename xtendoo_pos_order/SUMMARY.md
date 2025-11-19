# Resumen Ejecutivo - Xtendoo POS Order Backend

## 📋 Información General

**Nombre:** xtendoo_pos_order
**Versión:** 19.0.1.0.0
**Autor:** Xtendoo
**Licencia:** LGPL-3
**Odoo:** 19.0

## 🎯 Objetivo

Permitir la creación y gestión de órdenes de Punto de Venta (POS) directamente desde el backend de Odoo, como alternativa a la interfaz JavaScript estándar del POS.

## ✨ Características Principales

### 1. Configuración Flexible por Caja

Cada `pos.config` puede elegir su modo de operación:

- **Standard POS Frontend**: Interfaz JavaScript tradicional de Odoo
- **Backend Orders Interface**: Gestión desde el backend

### 2. Validación de Seguridad

- Solo se permiten crear órdenes manualmente cuando el POS está en modo "backend"
- Previene inconsistencias en los datos
- Las órdenes desde el frontend JS siempre funcionan

### 3. Cálculos Automáticos

- Totales, impuestos y descuentos se calculan automáticamente
- Reutiliza la lógica estándar del POS de Odoo
- Autocompletado de precios desde lista de precios
- Asignación automática de impuestos

### 4. Gestión de Sesiones

- Validación de sesión abierta antes de crear órdenes
- Asignación automática de sesión si está disponible
- Mensajes de error claros y descriptivos

## 📂 Estructura del Módulo

```
xtendoo_pos_order/
├── __init__.py                          # Inicialización del módulo
├── __manifest__.py                      # Manifest con dependencias y datos
├── hooks.py                             # Hooks post-instalación/desinstalación
├── models/
│   ├── __init__.py
│   ├── pos_config.py                    # Extensión de pos.config
│   ├── pos_order.py                     # Extensión de pos.order
│   └── pos_order_line.py                # Extensión de pos.order.line
├── views/
│   ├── pos_config_view.xml              # Vista de configuración
│   └── pos_order_view.xml               # Vistas de órdenes + acción + menú
├── security/
│   └── ir.model.access.csv              # Permisos de acceso
├── tests/
│   ├── __init__.py
│   └── test_pos_order_backend.py        # Tests unitarios
├── static/
│   └── description/
│       └── index.html                   # Página de descripción
├── README.md                            # Documentación general
├── INSTALL.md                           # Guía de instalación y uso
├── CHANGELOG.md                         # Historial de cambios
└── LICENSE                              # Licencia LGPL-3
```

## 🔧 Componentes Técnicos

### Modelos Extendidos

#### pos.config
- **Campo nuevo:** `interface_type` (Selection)
- **Métodos sobrescritos:**
  - `open_ui()`: Redirección según configuración
  - `open_existing_session_cb()`: Gestión de sesión existente
- **Método nuevo:** `_open_backend_orders_interface()`: Abre vista de órdenes

#### pos.order
- **Método sobrescrito:** `create()`: Validación de modo backend
- **Métodos mejorados:**
  - `action_pos_order_paid()`: Validación de pagos
  - `action_pos_order_invoice()`: Generación de factura
  - `_compute_amount_all()`: Cálculo de totales

#### pos.order.line
- **Onchange:** `_onchange_product_id()`: Autocompletado de datos
- **Método sobrescrito:** `_compute_amount_line_all()`: Cálculo de línea

### Vistas

1. **pos_config_view.xml**: Agrega campo `interface_type` en configuración
2. **pos_order_view.xml**:
   - Habilita botón "Crear" en vista árbol
   - Mejora formulario para uso backend
   - Define acción `action_pos_order_backend`
   - Agrega menú "Órdenes Backend"

### Seguridad

Permisos para grupos:
- `point_of_sale.group_pos_user`: Lectura, escritura, creación
- `point_of_sale.group_pos_manager`: Todos los permisos incluyendo eliminación

### Tests

8 tests unitarios que cubren:
- Creación exitosa en modo backend
- Rechazo en modo frontend
- Creación desde UI (siempre permitido)
- Órdenes con líneas de producto
- Redirección según modo
- Gestión de sesiones
- Asignación automática de sesión

## 🚀 Flujo de Trabajo

### Para el Usuario

1. **Configuración inicial**
   - Ir a POS → Configuración → Puntos de Venta
   - Seleccionar "Backend Orders Interface"
   - Guardar

2. **Abrir sesión**
   - Clic en el botón del POS
   - Se abre automáticamente la vista de órdenes

3. **Crear orden**
   - Clic en "Crear"
   - Completar datos (POS, sesión, cliente)
   - Agregar productos
   - Registrar pagos
   - Marcar como pagado
   - (Opcional) Generar factura

### Para el Sistema

```
Usuario hace clic en POS
    ↓
pos.config.open_ui()
    ↓
¿interface_type == 'backend'?
    ├─ SÍ → _open_backend_orders_interface()
    │         ↓
    │       Busca sesión abierta
    │         ↓
    │       Devuelve ir.actions.act_window
    │         ↓
    │       Abre vista de pos.order filtrada
    │
    └─ NO → super().open_ui()
              ↓
            Abre POS JavaScript estándar
```

## 📊 Casos de Uso

### Caso 1: TPV Tradicional
**Problema:** PC sin pantalla táctil
**Solución:** Modo backend con mouse y teclado
**Beneficio:** Interfaz familiar para el personal

### Caso 2: Órdenes Telefónicas
**Problema:** Necesidad de registrar ventas remotas
**Solución:** Crear órdenes POS desde backoffice
**Beneficio:** Centralización de todas las ventas

### Caso 3: Integración ERP
**Problema:** Separación entre POS y ventas normales
**Solución:** Flujo unificado desde backend
**Beneficio:** Mejor integración con inventario y contabilidad

## 📈 Ventajas

✅ **Flexibilidad:** Cada caja elige su modo de operación
✅ **Seguridad:** Validaciones que previenen errores
✅ **Familiar:** Usa interfaz backend estándar de Odoo
✅ **Completo:** Todas las funciones del POS disponibles
✅ **Integrado:** Reutiliza lógica estándar de Odoo
✅ **Documentado:** Guías completas en español
✅ **Probado:** Suite de tests incluida

## ⚠️ Consideraciones

- Requiere sesión abierta para crear órdenes
- No modifica el comportamiento del POS frontend
- Los datos persisten al desinstalar el módulo
- Compatible solo con Odoo 19.0

## 📚 Documentación

| Archivo | Propósito |
|---------|-----------|
| `README.md` | Descripción general y características |
| `INSTALL.md` | Guía completa de instalación paso a paso |
| `CHANGELOG.md` | Historial de versiones y cambios |
| `LICENSE` | Términos de licencia LGPL-3 |

## 🎓 Formación del Personal

**Tiempo estimado:** 15-30 minutos

1. **Teoría** (5 min): Explicar diferencia entre modo frontend y backend
2. **Configuración** (5 min): Mostrar cómo configurar el POS
3. **Práctica** (10-15 min): Crear órdenes de ejemplo
4. **Casos especiales** (5 min): Pagos múltiples, facturas, clientes

## 📞 Soporte

**Xtendoo**
Web: https://www.xtendoo.es

Para cualquier consulta técnica o soporte, contacte con su representante de Xtendoo.

---

**Fecha de creación:** 2025-01-19
**Última actualización:** 2025-01-19
**Estado:** Producción

