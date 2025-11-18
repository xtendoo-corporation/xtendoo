# 🎯 Comandos para añadir el módulo al repositorio Git

## Ubicación del módulo

El módulo está correctamente ubicado en:
```
/home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance/
```

---

## 📋 Pasos para commitear al repositorio Xtendoo

### 1. Verificar el estado del repositorio

```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo
git status
```

Esto mostrará si el módulo `xtendoo_pos_performance/` aparece como "untracked" (sin seguimiento).

---

### 2. Ver qué archivos se añadirán

```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo
git add -n xtendoo_pos_performance/
```

El flag `-n` (dry-run) muestra qué archivos se añadirían sin hacerlo realmente.

---

### 3. Añadir el módulo al staging

```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo
git add xtendoo_pos_performance/
```

---

### 4. Verificar los archivos añadidos

```bash
git status
```

Deberías ver algo como:
```
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        new file:   xtendoo_pos_performance/.gitignore
        new file:   xtendoo_pos_performance/__init__.py
        new file:   xtendoo_pos_performance/__manifest__.py
        new file:   xtendoo_pos_performance/README.md
        ...
```

---

### 5. Hacer commit del módulo

```bash
git commit -m "feat: Añadir módulo xtendoo_pos_performance

- Mejora el rendimiento del POS con catálogos grandes
- Limita carga inicial de productos y clientes
- Configurable desde Ajustes → Punto de venta
- Interfaz en español
- Valores por defecto: 500/500
- Documentación completa incluida
- Compatible con Odoo 19.0 CE/EE

Resuelve: Lentitud del POS con 35.000+ productos
Tiempo de arranque: 5-15 min → 5-15 seg (90-95% mejora)"
```

---

### 6. Pushear al repositorio remoto

```bash
git push origin main
```

O si tu rama principal se llama `master`:
```bash
git push origin master
```

O si estás en una rama de desarrollo:
```bash
git push origin nombre-de-tu-rama
```

---

## 🔍 Verificación post-commit

### Ver el commit realizado

```bash
git log -1 --stat
```

### Ver los archivos del módulo en el repositorio

```bash
git ls-files xtendoo_pos_performance/
```

---

## 📝 Archivos que se commitearán

Los siguientes 12 archivos serán añadidos al repositorio:

```
xtendoo_pos_performance/.gitignore
xtendoo_pos_performance/__init__.py
xtendoo_pos_performance/__manifest__.py
xtendoo_pos_performance/README.md
xtendoo_pos_performance/INSTALACION_RAPIDA.md
xtendoo_pos_performance/RECORD_RULES_GUIDE.md
xtendoo_pos_performance/check_module.sh
xtendoo_pos_performance/data/ir_config_parameter_data.xml
xtendoo_pos_performance/models/__init__.py
xtendoo_pos_performance/models/res_config_settings.py
xtendoo_pos_performance/views/res_config_settings_views.xml
xtendoo_pos_performance/static/description/index.html
```

**Nota**: Los archivos `__pycache__/` y `*.pyc` NO se commitearán gracias al `.gitignore`.

---

## ⚠️ Notas importantes

### Si el repositorio usa branches/pull requests:

```bash
# Crear una nueva rama para el módulo
git checkout -b feature/xtendoo-pos-performance

# Añadir y commitear
git add xtendoo_pos_performance/
git commit -m "feat: Añadir módulo xtendoo_pos_performance"

# Pushear la rama
git push origin feature/xtendoo-pos-performance

# Crear Pull Request desde la interfaz de GitHub/GitLab/Bitbucket
```

### Si hay archivos que no quieres commitear:

El `.gitignore` ya está configurado para excluir:
- `__pycache__/`
- `*.pyc`
- `*.pyo`
- `.idea/`
- `.vscode/`
- Archivos temporales

---

## 🎯 Comando rápido (todo en uno)

Si quieres hacer todo de una vez:

```bash
cd /home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo && \
git add xtendoo_pos_performance/ && \
git commit -m "feat: Añadir módulo xtendoo_pos_performance - mejora rendimiento POS" && \
git push origin main
```

**⚠️ Cuidado**: Asegúrate de que `main` es tu rama principal. Cámbialo por `master` u otro nombre si es diferente.

---

## ✅ Checklist antes de pushear

- [ ] El módulo está en `/src/xtendoo/xtendoo_pos_performance/`
- [ ] Se ejecutó `./check_module.sh` sin errores
- [ ] Se revisó `git status` y todo es correcto
- [ ] El mensaje de commit es descriptivo
- [ ] Se verificó la rama destino (`main`, `master`, etc.)
- [ ] Hay acceso de escritura al repositorio remoto

---

## 📞 Si necesitas ayuda

Contacta con el equipo de desarrollo de Xtendoo o revisa:
- Documentación del proyecto
- Políticas de commits del repositorio
- Guía de contribución del equipo

---

**Creado para facilitar la integración del módulo al repositorio Xtendoo**
**Xtendoo Software S.L.U. - 2025**

