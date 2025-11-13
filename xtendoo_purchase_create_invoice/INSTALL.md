# 🚀 Instalación Rápida - Xtendoo Purchase Create Invoice

## ¿Qué hace este módulo?

**Crear facturas de compra con UN SOLO CLIC.**

- ✅ Sin subir documentos
- ✅ Sin wizards
- ✅ Sin decisiones
- ✅ En 5 segundos

---

## Instalación (4 Pasos)

### Paso 1: Reiniciar Odoo
```bash
cd /home/xtendoo/Documentos/odoo/19
docker-compose restart odoo
```

### Paso 2: Actualizar Lista de Módulos
1. Abrir Odoo
2. Ir a **Aplicaciones**
3. Menú (⋮) → **Actualizar lista de aplicaciones**
4. Confirmar actualización

### Paso 3: Buscar e Instalar
1. En Aplicaciones, buscar: **"Xtendoo Purchase Create Invoice"**
2. Hacer clic en **Instalar**
3. Esperar confirmación

### Paso 4: ¡Listo!
Ya puedes usar el módulo.

---

## Uso (Ultra Simple)

```
1. Ir a Compras → Pedidos de Compra
2. Abrir un pedido confirmado con recepciones
3. Hacer clic en "Crear Factura"
4. ✅ La factura se crea automáticamente
```

**Eso es todo. No hay más pasos.**

---

## ⚡ Prueba Rápida (Test de Instalación)

### Test Completo
1. Crear un pedido de compra
   - Añadir proveedor
   - Añadir 2-3 productos
   - Guardar

2. Confirmar el pedido
   - Clic en "Confirmar"

3. Recibir productos
   - Ir a la recepción vinculada
   - Hacer clic en "Validar"

4. Volver al pedido
   - Abrir el pedido de compra
   - **Verificar que aparece botón "Crear Factura"**

5. Crear factura
   - Clic en "Crear Factura"
   - ✅ **Debe crearse la factura instantáneamente**

### Resultado Esperado
- Factura en estado "Borrador"
- Todas las líneas recibidas incluidas
- Factura vinculada al pedido
- Tiempo total: ~5 segundos

---

## 🎯 Verificación Post-Instalación

### Checklist de Verificación

- [ ] Módulo aparece como "Instalado" en Aplicaciones
- [ ] Botón "Crear Factura" visible en pedidos confirmados
- [ ] Al hacer clic, la factura se crea sin wizard
- [ ] La factura se abre automáticamente
- [ ] La factura contiene las líneas correctas
- [ ] No aparecen errores en el log

### Si Todo Está OK
✅ **Instalación exitosa**
✅ **Módulo funcionando correctamente**
✅ **Listo para producción**

---

## 🐛 Resolución de Problemas

### Problema 1: El módulo no aparece en la lista
**Solución:**
1. Verificar que el módulo está en la ruta correcta
2. Reiniciar Odoo
3. Actualizar lista de aplicaciones
4. Buscar de nuevo

### Problema 2: El botón no aparece
**Causas comunes:**
- El pedido no está confirmado → Confirmar
- No hay recepciones → Recibir productos
- Ya está todo facturado → Verificar estado

### Problema 3: Error al crear factura
**Verificar:**
- El proveedor tiene configuración fiscal
- Las líneas tienen productos válidos
- Los productos tienen precios
- El usuario tiene permisos de facturación

### Problema 4: La factura está vacía
**Causa:** No hay cantidades recibidas pendientes de facturar
**Solución:** Recibir productos primero

---

## 📊 Especificaciones Técnicas

### Versión del Módulo
- **Versión:** 19.0.2.0.0
- **Odoo:** 19.0
- **Licencia:** AGPL-3

### Dependencias
- `purchase` (incluido en Odoo)
- `account` (incluido en Odoo)

**No requiere módulos adicionales.**

### Archivos del Módulo
```
11 archivos totales
~200 líneas de código
0 dependencias externas
0 wizards
0 complejidad innecesaria
```

### Compatibilidad
✅ Odoo 19.0 Community
✅ Odoo 19.0 Enterprise
✅ Multi-compañía
✅ Multi-almacén
✅ Multi-moneda

---

## 📚 Documentación Adicional

### Archivos de Documentación
- **README.md** - Documentación técnica
- **GUIA_USO.md** - Guía detallada de uso
- **CHANGELOG.md** - Historial de cambios
- **LICENSE** - Licencia AGPL-3

### Recursos Online
- **Website:** https://xtendoo.es
- **Soporte:** Contactar a través del website

---

## 🎉 Siguiente Paso

### Una Vez Instalado

**Forma a tus usuarios:**
```
"Ahora crear facturas es más fácil:
1. Abrir pedido
2. Clic en 'Crear Factura'
3. Listo"
```

**Monitoriza el ahorro:**
- Cronometra cuánto tardabais antes: ~60 segundos
- Cronometra cuánto tardáis ahora: ~5 segundos
- Calcula el ahorro mensual

**Recoge feedback:**
- ¿Es más fácil?
- ¿Es más rápido?
- ¿Hay algo que mejorar?

---

## 💡 Tips de Uso

### Tip 1: Recepciones Parciales
Puedes crear múltiples facturas para el mismo pedido si recibes en varias entregas.

### Tip 2: Revisión Rápida
La factura se abre en borrador. Revísala antes de confirmar.

### Tip 3: Cambios Manuales
Si necesitas ajustar algo, la factura está en borrador y puedes editarla.

### Tip 4: Historial
Puedes ver todas las facturas del pedido en la pestaña "Facturas".

---

## 🚀 ¡Listo Para Usar!

```
┌────────────────────────────────────┐
│    INSTALACIÓN COMPLETADA  ✅      │
├────────────────────────────────────┤
│  Módulo: Instalado                 │
│  Funcionalidad: Activa             │
│  Complejidad: Mínima               │
│  Velocidad: Máxima                 │
│  Wizards: 0                        │
│  Clics necesarios: 1               │
│  Ahorro de tiempo: 12x             │
└────────────────────────────────────┘
```

**¡Disfruta creando facturas con un solo clic!** ⚡

---

**Versión:** 19.0.2.0.0
**Última actualización:** 13 de noviembre de 2025
**Autor:** Xtendoo
**Filosofía:** Simplicidad máxima, complejidad mínima

