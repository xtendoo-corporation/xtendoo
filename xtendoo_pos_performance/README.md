# Xtendoo POS Performance

## Descripción

Módulo para Odoo 19.0 que mejora significativamente el rendimiento del Punto de Venta (TPV/POS) en bases de datos con catálogos grandes de productos y/o muchos clientes.

## Problema que resuelve

En instalaciones de Odoo con catálogos grandes (por ejemplo, 35.000 productos o más), el tiempo de arranque del POS puede ser muy largo porque carga todos los productos y clientes de golpe al iniciar la sesión.

Este módulo soluciona este problema utilizando los parámetros internos de Odoo para limitar la carga inicial, permitiendo que el POS:
- Cargue solo un número limitado de registros en el primer batch
- El resto se carga bajo demanda o en segundo plano
- Reduce drásticamente el tiempo de arranque de la sesión de TPV

## Características

✅ **Configuración visual desde Ajustes**: No es necesario editar parámetros del sistema manualmente
✅ **Valores por defecto razonables**: 500 productos y 500 clientes al instalar
✅ **Interfaz en español**: Todos los textos en español para usuarios funcionales
✅ **Recomendaciones incluidas**: Guía de valores según tamaño del catálogo
✅ **Compatible con multi-compañía**: Funciona correctamente en entornos multi-empresa
✅ **Sin modificaciones de JavaScript**: Solo configuración, no toca código del POS

## Instalación

### En entorno Doodba/Docker

1. **El módulo está ubicado en el repositorio Xtendoo:**

```bash
/home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance/
```

El módulo ya está en la ubicación correcta dentro del repositorio `xtendoo`.

2. **Reiniciar el contenedor de Odoo:**

```bash
cd /home/xtendoo/Documentos/odoo/19
docker-compose restart odoo
```

3. **Actualizar la lista de módulos en Odoo:**
   - Ir a: **Aplicaciones**
   - Activar el **Modo desarrollador** (si no está activo)
   - Clic en **Actualizar lista de aplicaciones**
   - Buscar "Xtendoo POS Performance"
   - Clic en **Instalar**

### En instalación tradicional de Odoo

1. Copiar el módulo a la ruta de addons:
```bash
cp -r xtendoo_pos_performance /ruta/a/odoo/addons/
```

2. Reiniciar el servicio de Odoo

3. Actualizar lista de aplicaciones e instalar desde la interfaz

## Configuración

### Acceso a la configuración

Una vez instalado el módulo:

1. Ir a: **Ajustes → Punto de venta**
2. Desplazarse hasta la sección **"Rendimiento"**
3. Configurar los valores deseados:
   - **Productos cargados al iniciar el POS**
   - **Clientes cargados al iniciar el POS**

### Valores recomendados

#### Según el tamaño del catálogo de productos:

| Número de productos | Valor recomendado |
|---------------------|-------------------|
| < 5.000             | 0 (sin límite)    |
| 5.000 - 15.000      | 500 - 1.000       |
| 15.000 - 50.000     | 300 - 500         |
| > 50.000            | 200 - 300         |

#### Según el número de clientes:

| Número de clientes | Valor recomendado |
|--------------------|-------------------|
| < 5.000            | 0 (sin límite)    |
| 5.000 - 15.000     | 500 - 1.000       |
| 15.000 - 50.000    | 300 - 500         |
| > 50.000           | 200 - 300         |

**Nota:** El valor `0` desactiva el límite y carga todos los registros (comportamiento por defecto de Odoo).

## Parámetros técnicos

El módulo configura los siguientes parámetros del sistema (ir.config_parameter):

- `point_of_sale.limited_product_count`: Límite de productos
- `point_of_sale.limited_customer_count`: Límite de clientes

Estos parámetros también pueden editarse manualmente desde:
**Ajustes → Técnico → Parámetros → Parámetros del sistema**

## Estructura del módulo

```
xtendoo_pos_performance/
├── __init__.py                              # Inicialización del módulo
├── __manifest__.py                          # Manifiesto del módulo
├── README.md                                # Esta documentación
├── models/
│   ├── __init__.py                          # Inicialización de modelos
│   └── res_config_settings.py              # Extensión de res.config.settings
├── views/
│   └── res_config_settings_views.xml       # Vista de configuración en Ajustes
└── data/
    └── ir_config_parameter_data.xml        # Valores iniciales de parámetros
```

## Dependencias

- `point_of_sale`: Módulo estándar de Odoo

## Información técnica

- **Versión del módulo**: 19.0.1.0.0
- **Versión de Odoo**: 19.0 (Community y Enterprise)
- **Autor**: Xtendoo Software S.L.U.
- **Sitio web**: https://xtendoo.es
- **Licencia**: LGPL-3

## Soporte

Para soporte técnico o consultas:
- Web: https://xtendoo.es
- Email: soporte@xtendoo.es

## Changelog

### 19.0.1.0.0 (2025-01-18)
- Primera versión del módulo
- Configuración de límites de productos y clientes en POS
- Interfaz de configuración en español
- Valores por defecto: 500 productos y 500 clientes

