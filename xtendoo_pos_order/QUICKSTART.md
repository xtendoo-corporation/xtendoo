# 🚀 Instalación Rápida - Xtendoo POS Order Backend

## Instalación en 3 pasos

### 1️⃣ Instalar el módulo

```bash
# El módulo ya está en: /odoo/custom/src/xtendoo/xtendoo_pos_order/
```

En Odoo:
1. Activar **Modo Desarrollador** (Ajustes → parte inferior)
2. Ir a **Aplicaciones**
3. Actualizar lista de aplicaciones (menú ☰)
4. Buscar: `xtendoo_pos_order`
5. Hacer clic en **Instalar**

### 2️⃣ Configurar un Punto de Venta

1. Ir a **Punto de Venta → Configuración → Puntos de Venta**
2. Seleccionar (o crear) un punto de venta
3. En **Interface Configuration**, seleccionar:
   - ✅ **Backend Orders Interface** (para gestión desde backend)
   - ⬜ **Standard POS Frontend** (para interfaz JS normal)
4. **Guardar**

### 3️⃣ Usar el módulo

**Opción A: Desde el botón del POS**
1. Ir a **Punto de Venta → Configuración → Puntos de Venta**
2. Clic en el botón del POS configurado
3. Se abre automáticamente la vista de órdenes
4. Clic en **Crear** para nueva orden

**Opción B: Desde el menú**
1. Ir a **Punto de Venta → Órdenes Backend**
2. Clic en **Crear**
3. Completar datos y guardar

---

## ✅ Checklist Rápido

- [ ] Módulo instalado
- [ ] POS configurado en modo "Backend Orders Interface"
- [ ] Sesión de POS abierta
- [ ] Productos marcados como "Available in POS"
- [ ] Primera orden creada con éxito

---

## 📚 Documentación Completa

- **README.md**: Características y descripción general
- **INSTALL.md**: Guía detallada de instalación y uso
- **SUMMARY.md**: Resumen ejecutivo técnico
- **CHANGELOG.md**: Historial de versiones

---

## ⚠️ Requisitos

- Odoo 19.0
- Módulo `point_of_sale` instalado
- Permisos de "Usuario de Punto de Venta" o superior

---

## 🆘 Soporte

**Xtendoo** - https://www.xtendoo.es

---

¡Listo para usar! 🎉

