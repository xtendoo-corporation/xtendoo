# 📚 Índice de Documentación - Xtendoo POS Performance

---

## 📁 Archivos de Documentación

### 🚀 Para empezar:

1. **QUICK_START.md** ⚡
   - Resumen ultra-rápido en 1 página
   - 3 comandos para instalar
   - Configuración básica
   - **Tiempo de lectura: 1 minuto**

2. **INSTALACION_RAPIDA.md** 📋
   - Guía de instalación en 5 pasos
   - Comandos copy-paste listos
   - Valores recomendados
   - **Tiempo de lectura: 3 minutos**

3. **README.md** 📖
   - Documentación completa del módulo
   - Características detalladas
   - Instrucciones de configuración
   - Tabla de valores recomendados
   - Solución de problemas
   - **Tiempo de lectura: 10 minutos**

---

### 🔧 Para administradores:

4. **GIT_COMMANDS.md** 📋
   - Comandos para commitear al repositorio Git
   - Verificación post-commit
   - Checklist antes de pushear
   - **Útil para**: Integrar en control de versiones

5. **check_module.sh** 🔍
   - Script de verificación automática
   - Valida estructura y sintaxis
   - Ejecutable desde terminal
   - **Uso**: `./check_module.sh`

---

### 🎓 Para desarrolladores:

6. **RECORD_RULES_GUIDE.md** ⭐
   - **BONUS**: Guía completa de record rules
   - Reglas multi-compañía para res.partner
   - Dominio exacto y XML completo
   - 10 buenas prácticas Odoo 19.0
   - Ejemplos de debugging
   - **Tiempo de lectura: 15 minutos**
   - **Extra**: Responde tu pregunta inicial sobre seguridad

---

## 🎯 ¿Qué archivo leer según tu objetivo?

### Quiero instalar el módulo AHORA:
→ **QUICK_START.md** (1 min) o **INSTALACION_RAPIDA.md** (3 min)

### Quiero entender qué hace el módulo:
→ **README.md** (10 min)

### Quiero añadirlo al repositorio Git:
→ **GIT_COMMANDS.md** (5 min)

### Quiero verificar que todo está bien:
→ Ejecutar **check_module.sh**

### Quiero aprender sobre record rules:
→ **RECORD_RULES_GUIDE.md** (15 min)

---

## 📂 Archivos técnicos del módulo

### Código Python:
- `__init__.py` - Inicialización del módulo
- `__manifest__.py` - Configuración y metadatos
- `models/__init__.py` - Inicialización de modelos
- `models/res_config_settings.py` - Campos de configuración

### Archivos XML:
- `data/ir_config_parameter_data.xml` - Parámetros por defecto
- `views/res_config_settings_views.xml` - Vista de ajustes

### Recursos estáticos:
- `static/description/index.html` - Descripción visual para Odoo

### Configuración:
- `.gitignore` - Archivos ignorados por Git

---

## 📊 Estadísticas del módulo

- **Total archivos**: 14 archivos
- **Archivos documentación**: 7 archivos
- **Archivos código**: 7 archivos
- **Líneas de código Python**: ~100 líneas
- **Líneas de código XML**: ~150 líneas
- **Líneas de documentación**: ~1000 líneas

---

## 🎯 Flujo de trabajo recomendado

```
1. Leer QUICK_START.md (1 min)
   ↓
2. Ejecutar check_module.sh para verificar
   ↓
3. Seguir INSTALACION_RAPIDA.md (5 pasos)
   ↓
4. Configurar en Odoo (Ajustes → POS → Rendimiento)
   ↓
5. Probar el POS y ver la mejora
   ↓
6. [Opcional] Leer README.md completo
   ↓
7. [Opcional] Commitear con GIT_COMMANDS.md
   ↓
8. [Opcional] Estudiar RECORD_RULES_GUIDE.md
```

---

## 🔗 Enlaces rápidos

### Documentación online:
- Web Xtendoo: https://xtendoo.es
- Soporte: soporte@xtendoo.es

### Ubicación del módulo:
```
/home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance/
```

### Odoo local:
- URL: http://localhost:19069
- Modo debug: http://localhost:19069?debug=1

---

## ✅ Checklist de lectura

- [ ] QUICK_START.md - Leído
- [ ] INSTALACION_RAPIDA.md - Seguido
- [ ] Módulo instalado en Odoo
- [ ] Configuración ajustada
- [ ] POS probado (mejora confirmada)
- [ ] README.md - Leído (opcional)
- [ ] GIT_COMMANDS.md - Aplicado (opcional)
- [ ] RECORD_RULES_GUIDE.md - Estudiado (opcional)

---

## 🎉 ¡Empieza aquí!

**Si tienes 1 minuto**: Lee `QUICK_START.md`
**Si tienes 5 minutos**: Lee `INSTALACION_RAPIDA.md` e instala
**Si tienes 30 minutos**: Lee toda la documentación

---

**¡Buena suerte con tu instalación!** 🚀

---

*Xtendoo Software S.L.U. - 2025*

