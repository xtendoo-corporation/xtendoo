# Product Archive Duplicate Name

## Descripción

Este módulo permite archivar automáticamente productos con nombres duplicados en la tabla `product.template`.

## Funcionalidad

El módulo añade:
- Un método `archive_duplicate_names()` en el modelo `product.template` que busca y archiva productos duplicados
- Una acción de servidor disponible en la vista de lista de productos para ejecutar el proceso

### Comportamiento

Cuando se ejecuta el proceso:
1. Busca todos los nombres de productos que aparecen más de una vez en productos activos
2. Para cada nombre duplicado, mantiene activo el producto con el ID más bajo (el primero creado)
3. Archiva todos los demás productos con ese mismo nombre
4. Registra en el log la información del proceso
5. Muestra una notificación con el resultado

**IMPORTANTE**: Solo archiva las copias duplicadas (2ª, 3ª, etc.), manteniendo siempre el primer producto activo.

## Uso

### Desde la interfaz
1. Ir a **Inventario > Productos > Productos**
2. En la vista de lista, hacer clic en el menú **Acción**
3. Seleccionar **Archive Duplicate Products**
4. El sistema mostrará una notificación con el número de productos archivados

### Desde código Python
```python
result = self.env['product.template'].archive_duplicate_names()
# Retorna: {'duplicate_names': [...], 'archived_count': n, 'errors': [...]}
```

### Desde la línea de comandos (Método manual)
Si el módulo no funciona desde la interfaz, puedes ejecutar el script manual:

```bash
# Primero, verifica qué bases de datos tienes
docker-compose exec db psql -U odoo -l

# Luego ejecuta el script (reemplaza DATABASE por tu base de datos)
docker-compose run --rm odoo odoo shell -d DATABASE < archive_duplicates_manual.py
```

## Características técnicas

- **Versión**: 18.0.1.0.0
- **Autor**: Xtendoo
- **Licencia**: AGPL-3
- **Categoría**: Product
- **Dependencias**: product

### Compatibilidad

- ✅ **Odoo 18**: Totalmente compatible
- ✅ **Campos JSONB**: Maneja correctamente campos traducibles multiidioma
- ✅ **Nombres traducibles**: Detecta duplicados sin importar el idioma
- ✅ **Texto simple**: Compatible con nombres no traducibles

### Manejo de campos traducibles

En Odoo 18, el campo `name` de `product.template` puede ser traducible (multiidioma) y se almacena como JSONB:

```json
{
  "en_US": "THREADED ROD 8mm",
  "es_ES": "VARILLA ROSCADA 8mm"
}
```

Este módulo **detecta correctamente duplicados** extrayendo el texto real del nombre, independientemente del idioma o formato de almacenamiento. Utiliza búsqueda por IDs para evitar problemas con el contexto de idioma.

## Seguridad

El módulo solo archiva productos, no los elimina. Los productos archivados pueden ser restaurados manualmente si es necesario.

## Notas

- El primer producto (por ID) de cada grupo de duplicados siempre se mantiene activo
- Solo se procesan productos activos
- Se excluyen productos con nombres vacíos o que empiezan con `[`

## Solución de problemas

### El módulo no archiva ningún producto

**Verificaciones**:

1. **¿Está el módulo instalado?**
   - Ve a Aplicaciones y busca "product_archive_duplicate_name"
   - Si no está instalado, instálalo y actualiza la aplicación

2. **¿Hay realmente productos duplicados?**
   - Ejecuta el script SQL de diagnóstico:
   ```bash
   docker-compose exec db psql -U odoo -d DATABASE < check_duplicates.sql
   ```

3. **¿Hay errores en los logs?**
   - Revisa los logs de Odoo:
   ```bash
   docker-compose logs -f odoo | grep -i "archive\|duplicate"
   ```

4. **Ejecutar el script manual**:
   - Si todo lo demás falla, usa el script manual:
   ```bash
   docker-compose run --rm odoo odoo shell -d DATABASE < archive_duplicates_manual.py
   ```

### Los productos se archivan pero luego reaparecen

- Verifica que no haya procesos automáticos que estén creando productos duplicados
- Revisa si hay importaciones de datos que estén sobreescribiendo los cambios

### Quiero recuperar productos archivados

1. Ve a **Inventario > Productos > Productos**
2. Añade un filtro personalizado: `Archivado = True`
3. Selecciona los productos que quieres recuperar
4. Haz clic en **Acción > Desarchivar**

- El proceso registra información detallada en los logs de Odoo

