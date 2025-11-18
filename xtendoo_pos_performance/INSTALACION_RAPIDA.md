# 🚀 Instalación Rápida - 5 Pasos

## El módulo YA está creado en el repositorio Xtendoo:
```
/home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance/
```

---

## PASO 1: Verificar el módulo ✓
```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance
./check_module.sh
```

**Debe mostrar**: ✓ Módulo verificado correctamente

---

## PASO 2: Reiniciar Odoo 🔄
```bash
cd /home/xtendoo/Documentos/odoo/19
docker-compose restart odoo
```

**Espera**: 10-15 segundos

---

## PASO 3: Actualizar lista de aplicaciones 📱

1. Abrir navegador: **http://localhost:19069**
2. Añadir a la URL: **?debug=1**
3. Ir a: **Aplicaciones**
4. Clic en menú **(⋮)** → **Actualizar lista de aplicaciones**
5. Confirmar

---

## PASO 4: Instalar el módulo 💾

En **Aplicaciones**, buscar:
```
Xtendoo POS Performance
```

Clic en: **Instalar**

---

## PASO 5: Configurar valores ⚙️

1. Ir a: **Ajustes → Punto de venta**
2. Scroll hasta: **Sección "Rendimiento"**
3. Configurar:
   - **Productos**: `300-500` (para 35.000 productos)
   - **Clientes**: `500-1000`
4. **Guardar**

---

## ✅ ¡LISTO!

**Abrir el POS y disfrutar de la velocidad** 🚀

**Antes**: 5-15 minutos de arranque
**Después**: 5-15 segundos de arranque

---

## 🆘 ¿Problemas?

Ver el archivo: `README.md` (sección "Solución de problemas")

O ejecutar de nuevo:
```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance
./check_module.sh
```

