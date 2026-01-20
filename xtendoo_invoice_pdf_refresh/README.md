# Xtendoo - Refresh Invoice PDF Attachment

## Descripción

Este módulo soluciona el problema del caché de PDF obsoleto en facturas de Odoo 17.

## Problema Resuelto

Cuando una factura se publica (`posted`) y se genera su PDF, Odoo lo guarda como adjunto para mejorar el rendimiento (función "Reload from attachment"). Sin embargo, si:

1. La factura se resetea a borrador (`Reset to Draft`)
2. Se editan los importes u otros datos
3. Se vuelve a publicar la factura

El PDF antiguo **no se actualiza automáticamente**, lo que puede llevar a que usuarios y clientes vean información incorrecta.

## Solución Implementada

Este addon intercepta el momento en que una factura se resetea a borrador y **elimina automáticamente los adjuntos PDF en caché** generados por el sistema. Cuando la factura se vuelva a publicar o imprimir, Odoo generará un PDF fresco con los datos actualizados.

### Características

- ✅ **Eliminación automática**: Los PDFs en caché se eliminan al resetear a borrador
- ✅ **Selectivo**: Solo elimina PDFs generados por el sistema de reportes
- ✅ **Seguro**: Preserva adjuntos subidos manualmente por usuarios
- ✅ **Multi-compañía**: Compatible con configuraciones multi-empresa
- ✅ **Sin desactivar caché**: Mantiene "Reload from attachment" activo para rendimiento óptimo
- ✅ **Tipos soportados**: `out_invoice`, `out_refund`, `in_invoice`, `in_refund`

## Funcionamiento Técnico

El módulo hereda `account.move` y sobrescribe el método `write()` para:

1. Detectar cuando el campo `state` cambia a `'draft'` desde `'posted'` o `'cancel'`
2. Filtrar solo facturas (no asientos contables genéricos)
3. Buscar adjuntos PDF vinculados a esas facturas
4. Comparar nombres de archivos con patrones esperados del reporte de facturas
5. Eliminar solo PDFs que coincidan (generados por el sistema)
6. Usar `sudo()` para evitar problemas de permisos (ACL)

### Patrones de Nombres Detectados

El módulo busca PDFs con nombres como:
- `INV/2024/00001.pdf`
- `Invoice - INV/2024/00001.pdf`
- `Bill - BILL/2024/00001.pdf`
- Variantes con guiones bajos en lugar de barras

## Instalación

### Requisitos Previos

- Odoo 17.0
- Módulo `account` instalado (viene por defecto)

### Pasos de Instalación

1. **Verificar que el módulo esté en el repositorio**

   El módulo debe estar en:
   ```
   /odoo/custom/src/xtendoo/xtendoo_invoice_pdf_refresh/
   ```

2. **Reiniciar el servidor Odoo**
   ```bash
   docker-compose restart odoo
   # O si usas el script de gestión:
   ./restart_odoo.sh
   ```

3. **Actualizar lista de aplicaciones**
   - Ir a Aplicaciones
   - Hacer clic en "Actualizar lista de aplicaciones" (puede requerir activar el modo desarrollador)

4. **Instalar el módulo**
   - Buscar "Xtendoo - Refresh Invoice PDF Attachment"
   - Hacer clic en "Instalar"

### Instalación desde Terminal (Alternativa)

```bash
# Conectar al contenedor de Odoo
docker-compose exec odoo bash

# Instalar el módulo
odoo -d TU_BASE_DE_DATOS -i xtendoo_invoice_pdf_refresh --stop-after-init

# Salir del contenedor
exit
```

## Uso

El módulo funciona **automáticamente**, sin necesidad de configuración:

1. Crea una factura y publícala → Se genera el PDF
2. Resetea la factura a borrador → **El PDF se elimina automáticamente**
3. Modifica los importes u otros datos
4. Vuelve a publicar la factura → Se genera un PDF **actualizado**

## Verificación

Para verificar que funciona correctamente:

1. Publica una factura y descarga su PDF
2. Anota el contenido (p.ej., importe total)
3. Ve a Configuración > Técnico > Adjuntos y busca el PDF de la factura
4. Resetea la factura a borrador
5. **Verifica que el adjunto PDF haya desaparecido**
6. Modifica algún importe
7. Vuelve a publicar
8. Descarga el PDF → Debe reflejar el nuevo importe

## Notas Importantes

### ✅ Mantiene el Rendimiento

Este módulo **NO desactiva** la función "Reload from attachment". El caché de PDF sigue activo para mejorar el rendimiento; simplemente se invalida en el momento correcto (al resetear a borrador).

### 🔒 Seguridad

- Usa `sudo()` para eliminar adjuntos, evitando errores de permisos
- Solo elimina PDFs que coincidan con patrones de reportes del sistema
- Los adjuntos subidos manualmente por usuarios **nunca se eliminan**

### 🌍 Localizaciones

Si usas módulos de localización que generan PDFs con nombres personalizados (p.ej., `l10n_es_facturae`), es posible que necesites extender el método `_xtd_get_expected_pdf_names()` para incluir esos patrones.

## Soporte

- **Autor**: Xtendoo
- **Web**: https://xtendoo.es
- **Versión**: 17.0.1.0.0
- **Licencia**: LGPL-3

## Desarrollo

### Extender Patrones de Nombres

Si necesitas añadir más patrones de nombres de PDF:

```python
from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def _xtd_get_expected_pdf_names(self, move):
        names = super()._xtd_get_expected_pdf_names(move)
        # Añadir patrones personalizados
        if move.name:
            names.append(f"MiPatron-{move.name}.pdf")
        return names
```

### Debugging

Para ver los logs de eliminación de PDFs:

1. Activa el nivel de log INFO para el módulo
2. Busca en los logs mensajes como:
   ```
   Clearing 1 cached invoice PDF(s) for INV/2024/00001: INV/2024/00001.pdf
   ```

## Changelog

### 17.0.1.0.0 (2026-01-20)

- 🎉 Versión inicial
- ✅ Soporte para facturas de cliente y proveedor
- ✅ Notas de crédito incluidas
- ✅ Detección inteligente de PDFs del sistema
- ✅ Compatible con multi-compañía
