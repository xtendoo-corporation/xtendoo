# 🔍 Checklist de Verificación del Módulo

## Pre-instalación

### Verificar estructura de archivos

```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_order/

# Verificar archivos principales
ls -l __init__.py __manifest__.py hooks.py

# Verificar modelos
ls -l models/__init__.py models/pos_config.py models/pos_order.py models/pos_order_line.py

# Verificar vistas
ls -l views/pos_config_view.xml views/pos_order_view.xml

# Verificar seguridad
ls -l security/ir.model.access.csv

# Verificar tests
ls -l tests/__init__.py tests/test_pos_order_backend.py

# Verificar documentación
ls -l README.md INSTALL.md QUICKSTART.md SUMMARY.md CHANGELOG.md LICENSE
```

### Verificar sintaxis Python

```bash
python3 -m py_compile __init__.py
python3 -m py_compile hooks.py
python3 -m py_compile models/*.py
python3 -m py_compile tests/*.py
```

### Verificar sintaxis XML

```bash
xmllint --noout views/pos_config_view.xml
xmllint --noout views/pos_order_view.xml
xmllint --noout demo/pos_config_demo.xml
```

---

## Instalación

### 1. Activar modo desarrollador

- Ir a **Ajustes**
- Scroll hasta el final
- Clic en **Activar el modo desarrollador**

### 2. Actualizar lista de aplicaciones

- Ir a **Aplicaciones**
- Menú (☰) → **Actualizar lista de aplicaciones**
- Confirmar

### 3. Instalar módulo

- Buscar: `xtendoo_pos_order`
- Verificar que aparezca el módulo
- Clic en **Instalar**
- Esperar a que complete

### 4. Verificar logs de instalación

Buscar en los logs de Odoo:
```
XTENDOO POS ORDER BACKEND: Módulo instalado correctamente
```

---

## Post-instalación

### Verificar que se crearon los registros

#### 1. Verificar campo en pos.config

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pos_config'
AND column_name = 'interface_type';
```

Resultado esperado: Una fila con `interface_type` de tipo `character varying`

#### 2. Verificar vistas creadas

En Odoo:
- Ir a **Ajustes → Técnico → Interfaz de usuario → Vistas**
- Buscar: `pos.config.form.interface.type`
- Buscar: `pos.order.tree.backend.create`
- Buscar: `pos.order.form.backend`

Deben existir las 3 vistas.

#### 3. Verificar acción creada

- Ir a **Ajustes → Técnico → Acciones → Acciones de Ventana**
- Buscar: `Órdenes POS (Backend)`
- Verificar que existe

#### 4. Verificar menú creado

- Ir a **Punto de Venta**
- Verificar que existe el menú **Órdenes Backend**

---

## Pruebas Funcionales

### Test 1: Configurar POS en modo Backend

1. Ir a **Punto de Venta → Configuración → Puntos de Venta**
2. Crear o editar un punto de venta
3. Verificar que existe la sección **Interface Configuration**
4. Verificar que existen las opciones:
   - ⚪ Standard POS Frontend
   - ⚪ Backend Orders Interface
5. Seleccionar **Backend Orders Interface**
6. Guardar
7. ✅ Debe guardarse sin errores

### Test 2: Redirección a backend

1. Ir a **Punto de Venta → Configuración → Puntos de Venta**
2. Abrir el POS configurado en modo backend
3. Clic en el botón del POS (o "Abrir Sesión")
4. ✅ Debe abrir una vista de lista de órdenes POS
5. ✅ Debe mostrar el botón "Crear"

### Test 3: Crear orden en modo backend (con sesión)

**Pre-requisito:** Tener una sesión abierta

1. Desde la vista de órdenes, clic en **Crear**
2. Completar:
   - Punto de Venta: (seleccionar el POS backend)
   - Sesión: (seleccionar la sesión abierta)
   - Cliente: (opcional, seleccionar uno)
3. En "Líneas de orden", clic en **Agregar una línea**
4. Seleccionar un producto
5. Verificar que se autocompleta:
   - Precio unitario
   - Impuestos
6. Establecer cantidad: 2
7. Guardar
8. ✅ La orden debe crearse correctamente
9. ✅ Los totales deben calcularse automáticamente

### Test 4: Intentar crear orden en modo frontend (debe fallar)

1. Configurar un POS en modo **Standard POS Frontend**
2. Abrir una sesión para ese POS
3. Ir a **Punto de Venta → Órdenes Backend**
4. Clic en **Crear**
5. Seleccionar el POS en modo frontend
6. Seleccionar la sesión
7. Intentar guardar
8. ✅ Debe mostrar un error:
   ```
   "No se permite crear órdenes manualmente para el Punto de Venta..."
   ```

### Test 5: Crear orden sin sesión (debe fallar)

1. Cerrar todas las sesiones de un POS backend
2. Ir a **Punto de Venta → Órdenes Backend**
3. Clic en **Crear**
4. Seleccionar el POS sin sesión abierta
5. Intentar guardar
6. ✅ Debe mostrar un error:
   ```
   "No hay ninguna sesión abierta para el Punto de Venta..."
   ```

### Test 6: Marcar orden como pagada

1. Crear una orden en modo backend con productos
2. En la pestaña **Pagos**, agregar una línea de pago
3. Método de pago: Efectivo
4. Monto: (igual o mayor al total de la orden)
5. Guardar
6. Clic en el botón **Marcar como Pagado**
7. ✅ La orden debe cambiar a estado "Paid"

### Test 7: Generar factura

1. Crear una orden con un cliente asignado
2. Marcar como pagada
3. Clic en el botón **Crear Factura**
4. ✅ Debe crear una factura vinculada
5. Verificar que el campo `invoice_id` tiene un valor

### Test 8: Redirección en modo frontend

1. Configurar un POS en modo **Standard POS Frontend**
2. Ir a **Punto de Venta → Configuración → Puntos de Venta**
3. Clic en el botón del POS
4. ✅ Debe abrir la interfaz JavaScript del POS (pantalla completa)

---

## Ejecutar Tests Unitarios

```bash
# Desde el contenedor/entorno de Odoo
odoo-bin -d nombre_base_datos -u xtendoo_pos_order --test-enable --stop-after-init --log-level=test

# O específicamente los tests del módulo
odoo-bin -d nombre_base_datos --test-tags=xtendoo_pos_order --stop-after-init --log-level=test
```

Resultado esperado:
```
8/8 tests passed
```

---

## Verificar Permisos

### Usuario normal (group_pos_user)

1. Crear/usar un usuario con rol "Usuario de Punto de Venta"
2. Verificar que puede:
   - ✅ Ver órdenes POS
   - ✅ Crear órdenes (en modo backend)
   - ✅ Editar órdenes
   - ❌ NO puede eliminar órdenes

### Administrador (group_pos_manager)

1. Crear/usar un usuario con rol "Administrador de Punto de Venta"
2. Verificar que puede:
   - ✅ Ver órdenes POS
   - ✅ Crear órdenes
   - ✅ Editar órdenes
   - ✅ Eliminar órdenes

---

## Verificar Documentación

### Archivos que deben existir

- [ ] README.md (descripción general)
- [ ] INSTALL.md (guía completa)
- [ ] QUICKSTART.md (instalación rápida)
- [ ] SUMMARY.md (resumen técnico)
- [ ] CHANGELOG.md (historial)
- [ ] LICENSE (licencia)

### Contenido de README.md

- [ ] Descripción del módulo
- [ ] Características principales
- [ ] Requisitos
- [ ] Estructura técnica
- [ ] Información de autor/licencia

### Contenido de INSTALL.md

- [ ] Pasos de instalación
- [ ] Pasos de configuración
- [ ] Instrucciones de uso
- [ ] Casos de uso
- [ ] Solución de problemas
- [ ] Checklist de implementación

---

## Verificar Limpieza del Código

### Standards de Odoo

```bash
# Si tienes pylint-odoo instalado
pylint --load-plugins=pylint_odoo models/ tests/

# Verificar imports
grep -r "from odoo import" models/
```

### Comentarios y documentación

```bash
# Verificar que todos los métodos tienen docstrings
grep -A 1 "def " models/*.py | grep '"""'
```

---

## Checklist Final

### Estructura
- [x] Todos los archivos .py tienen licencia
- [x] Todos los archivos .xml tienen declaración XML
- [x] __init__.py en todas las carpetas de Python
- [x] __manifest__.py válido

### Funcionalidad
- [ ] Campo interface_type visible en pos.config
- [ ] Redirección funciona según configuración
- [ ] Creación permitida solo en modo backend
- [ ] Cálculos automáticos funcionan
- [ ] Validaciones lanzan errores apropiados
- [ ] Botones personalizados funcionan

### Tests
- [ ] Todos los tests pasan
- [ ] Coverage adecuado de casos de uso
- [ ] Tests de validaciones incluidos

### Documentación
- [ ] README completo
- [ ] INSTALL con pasos claros
- [ ] CHANGELOG actualizado
- [ ] Comentarios en código

### Seguridad
- [ ] Permisos correctos en ir.model.access.csv
- [ ] Validaciones de permisos funcionan
- [ ] Mensajes de error son informativos

---

## ✅ Módulo Listo para Producción

Si todos los checks están marcados, el módulo está listo para:
- Instalación en producción
- Uso por usuarios finales
- Documentación entregada
- Soporte técnico

---

**Fecha de verificación:** _____________
**Verificado por:** _____________
**Resultado:** ⚪ Aprobado / ⚪ Requiere ajustes

