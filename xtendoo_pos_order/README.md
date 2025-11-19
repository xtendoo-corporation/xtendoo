# Xtendoo POS Order Backend

## Descripción

Módulo para Odoo 19.0 que permite crear y gestionar órdenes de Punto de Venta (POS) directamente desde el backend, como alternativa a la interfaz JavaScript estándar del POS.

## Características

- **Configuración flexible por caja**: Cada punto de venta puede elegir entre:
  - **Standard POS Frontend**: Interfaz JavaScript tradicional de Odoo
  - **Backend Orders Interface**: Gestión de órdenes desde el backend

- **Creación manual de órdenes**: Cuando está activado el modo backend, el botón "Crear" está habilitado en las vistas de órdenes POS

- **Validaciones de seguridad**: Solo se permite la creación manual de órdenes cuando la caja está configurada en modo backend

- **Cálculos automáticos**: Los totales, impuestos y subtotales se calculan automáticamente al igual que en el POS estándar

- **Gestión completa**: Permite crear órdenes, agregar líneas, registrar pagos y generar facturas

## Instalación

1. Copie el módulo en el directorio de addons personalizado:
   ```bash
   /odoo/custom/src/xtendoo/xtendoo_pos_order/
   ```

2. Actualice la lista de aplicaciones:
   - Vaya a **Aplicaciones**
   - Haga clic en el botón de actualizar lista de aplicaciones

3. Busque "Xtendoo POS Order Backend" e instale el módulo

## Configuración

### Configurar un Punto de Venta en modo Backend

1. Vaya a **Punto de Venta → Configuración → Puntos de Venta**
2. Abra el punto de venta que desea configurar
3. En la sección **Interface Configuration**, seleccione:
   - **Backend Orders Interface** para habilitar la creación desde backend
   - **Standard POS Frontend** para usar la interfaz JS normal
4. Guarde los cambios

### Abrir una sesión

Antes de crear órdenes, debe abrir una sesión:

1. Vaya a **Punto de Venta → Configuración → Puntos de Venta**
2. Seleccione el punto de venta configurado en modo backend
3. Haga clic en el botón **Abrir Sesión**
4. Si el POS está en modo backend, se abrirá automáticamente la vista de órdenes

## Uso

### Crear una orden de POS desde el backend

**Método 1: Desde el botón del POS**

1. Vaya a **Punto de Venta → Configuración → Puntos de Venta**
2. Haga clic en el botón de la caja configurada en modo backend
3. Se abrirá la vista de órdenes filtrada por esa caja
4. Haga clic en **Crear**

**Método 2: Desde el menú directo**

1. Vaya a **Punto de Venta → Órdenes Backend**
2. Haga clic en **Crear**
3. Seleccione el punto de venta y la sesión

### Completar una orden

1. **Información básica**:
   - Punto de Venta (obligatorio)
   - Sesión (obligatorio - debe estar abierta)
   - Cliente (opcional)
   - Lista de precios
   - Posición fiscal

2. **Agregar productos**:
   - Haga clic en "Agregar una línea"
   - Seleccione el producto
   - El precio se auto-completa desde la lista de precios
   - Los impuestos se asignan automáticamente
   - Especifique cantidad y descuento si es necesario

3. **Registrar pagos**:
   - En la pestaña de pagos, agregue las líneas de pago
   - Asegúrese de que el total de pagos cubra el total de la orden

4. **Marcar como pagado**:
   - Haga clic en el botón **Marcar como Pagado**

5. **Generar factura** (opcional):
   - Haga clic en el botón **Crear Factura**
   - Solo disponible si hay un cliente asignado

## Validaciones y seguridad

- **Creación restringida**: Solo se pueden crear órdenes manualmente en cajas configuradas con modo backend
- **Sesión obligatoria**: Debe existir una sesión abierta para crear órdenes
- **Permisos**: Los usuarios necesitan el rol "Usuario de Punto de Venta" o superior
- **Integridad de datos**: Se mantienen todas las validaciones estándar del POS

## Estructura técnica

```
xtendoo_pos_order/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── pos_config.py          # Extensión de pos.config
│   ├── pos_order.py            # Extensión de pos.order
│   └── pos_order_line.py       # Extensión de pos.order.line
├── views/
│   ├── pos_config_view.xml     # Vista de configuración
│   └── pos_order_view.xml      # Vistas de órdenes
├── security/
│   └── ir.model.access.csv     # Permisos de acceso
└── README.md
```

## Compatibilidad

- **Versión de Odoo**: 19.0
- **Dependencias**: `point_of_sale`

## Autor

**Xtendoo**
- Web: https://www.xtendoo.es
- Licencia: LGPL-3

## Soporte

Para reportar problemas o sugerencias, contacte con el equipo de desarrollo de Xtendoo.

