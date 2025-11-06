# Changelog - Migración a Odoo 17.0

## Versión 17.0.1.0.0

### Cambios realizados para compatibilidad con Odoo 17.0

#### 1. Manifest
- ✅ Actualizada la versión de `18.0.1.0.0` a `17.0.1.0.0`

#### 2. Modelos Python
- ✅ **models/ai_job.py**: Implementado el modelo completo `xtendoo.invoice.ai.job` que estaba vacío
  - Agregados campos: filename, state, invoice_id, company_id, user_id, processing_time, tokens_used, pages_processed, detected_language, detected_country, supplier_name, invoice_number, invoice_amount, error_message
  - Implementado método `action_view_invoice()` para navegar a la factura relacionada

#### 3. Archivos JavaScript
- ✅ Ya estaban usando la sintaxis correcta de Odoo 17:
  - `/** @odoo-module **/`
  - Imports desde `@web/` y `@odoo/owl`
  - Componentes OWL modernos
  - No se requirieron cambios

#### 4. Archivos XML
- ✅ Todas las vistas ya son compatibles con Odoo 17
- ✅ Los templates XML ya usan la sintaxis correcta
- ✅ **views/wizard_views.xml**: Corregido problema de compatibilidad con Odoo 17
  - Removido atributo `groups="base.group_multi_company"` del campo `company_id` en el wizard
  - En Odoo 17, los campos con restricciones de grupo no pueden usarse en dominios de otros campos
  - Ahora el campo `company_id` es visible para todos, permitiendo que el domain de `journal_id` funcione correctamente

#### 5. Dependencias
- ✅ Agregadas al archivo `odoo/custom/dependencies/pip.txt`:
  - `openai` - Para integración con OpenAI API (ChatGPT)
  - `pdf2image` - Para convertir PDFs a imágenes
  - `jsonschema` - Para validación de schemas JSON

### Instalación

1. Las dependencias de Python se instalarán automáticamente al reconstruir la imagen Docker
2. El módulo se puede instalar normalmente desde la interfaz de Odoo o mediante CLI

### Características

- Importación automática de facturas de proveedor usando IA (OpenAI Vision API)
- Extracción estructurada de datos de facturas en PDF, PNG, JPG
- Validación automática de totales
- Creación automática de partners si no existen
- Mapeo inteligente de impuestos
- Adjuntar documento original a la factura creada
- Histórico completo de trabajos de IA con métricas (tokens usados, tiempo de procesamiento)

### Requisitos

- Odoo 17.0
- Clave API de OpenAI configurada en Configuración > Técnico > Parámetros del Sistema
- Poppler-utils instalado en el sistema (para pdf2image)

### Configuración

1. Ir a Configuración > Técnico > Parámetros del Sistema
2. Configurar los siguientes parámetros:
   - `xtendoo_invoice_ai.api_key`: Tu clave API de OpenAI
   - `xtendoo_invoice_ai.model`: Modelo a usar (default: gpt-4o-mini)
   - `xtendoo_invoice_ai.tolerance`: Tolerancia para diferencias en totales (default: 0.02)
   - `xtendoo_invoice_ai.max_retries`: Número máximo de reintentos (default: 3)

### Uso

1. **Desde lista de facturas de proveedor**:
   - Click en botón "OCR" en la barra superior
   - Seleccionar uno o varios archivos PDF/imágenes
   - El sistema procesará automáticamente y creará las facturas

2. **Desde una factura individual**:
   - Crear factura de proveedor borrador
   - Subir archivo en el campo "AI Invoice File"
   - Click en "Import with AI"
   - Los datos se importarán automáticamente

### Notas técnicas

- Compatible con Odoo 17.0
- Usa OpenAI Vision API con extracción estructurada
- Soporta múltiples idiomas y formatos de factura
- Validación de totales con tolerancia configurable
- Sistema de jobs para tracking y auditoría

