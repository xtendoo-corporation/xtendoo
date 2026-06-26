====================================
Xtendoo Work Order Management
====================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-Xtendoo%2Fxtendoo-lightgray.png?logo=github
    :target: https://github.com/Xtendoo/xtendoo/tree/17.0/xtendoo_fsm
    :alt: Xtendoo/xtendoo

|badge1| |badge2| |badge3|

Módulo unificado de gestión integral de órdenes de trabajo.
Consolida toda la funcionalidad de gestión de órdenes de trabajo en una sola aplicación compacta.

**Tabla de contenidos**

.. contents::
   :local:

Características principales
===========================

* **Gestión de órdenes de trabajo**: Creación, seguimiento y gestión completa del ciclo de vida de órdenes de trabajo
* **Programación y seguimiento de técnicos**: Asignación de técnicos, gestión de equipos y seguimiento de disponibilidad
* **Integración con ventas y facturación**: Creación automática de órdenes de venta y facturas desde órdenes de trabajo
* **Gestión de inventario y materiales**: Control de materiales utilizados en cada trabajo
* **Sistema de etapas personalizable**: Workflow configurable con colores para seguimiento visual
* **Geolocalización y ubicaciones**: Gestión de ubicaciones de clientes con coordenadas GPS
* **Gestión de equipos y mantenimiento**: Registro de equipos de clientes y programación de mantenimientos
* **Hojas de trabajo y timesheet**: Integración con hojas de tiempo para facturación de servicios
* **Portal para clientes**: Acceso de clientes a sus órdenes de trabajo
* **Reportes y análisis especializados**: Estadísticas y análisis de rendimiento

Instalación
===========

Para instalar este módulo:

1. Descargar el módulo en tu directorio de addons de Odoo
2. Actualizar la lista de aplicaciones en Odoo
3. Buscar "Xtendoo - Work Order Management"
4. Hacer clic en "Instalar"

Dependencias
------------

Este módulo depende de los siguientes módulos de Odoo:

* ``base``
* ``mail``
* ``project``
* ``sale_management``
* ``stock``
* ``hr_timesheet``
* ``base_geolocalize``
* ``portal``
* ``contacts``
* ``resource``
* ``account``
* ``repair``

Configuración
=============

Después de la instalación, el módulo creará automáticamente:

* **Etapas por defecto**:
  * Nuevo (por defecto)
  * Programado
  * En Progreso
  * Completado
  * Cancelado

* **Etiquetas predeterminadas**:
  * Mantenimiento
  * Reparación
  * Instalación
  * Emergencia

* **Secuencia** para numeración automática de órdenes (FSM0001, FSM0002, etc.)

Configuración inicial recomendada
---------------------------------

1. **Configurar técnicos**:
   - Ir a ``Órdenes de Trabajo > Planificación > Técnicos``
   - Asociar empleados existentes como técnicos FSM
   - Configurar habilidades y especialidades

2. **Personalizar etapas**:
   - Ir a ``Órdenes de Trabajo > Configuración > Etapas``
   - Modificar colores y nombres según necesidades
   - Configurar etapas como cerradas o abiertas

Uso
===

Creación de órdenes de trabajo
-------------------------------

1. Ir a ``Órdenes de Trabajo > Órdenes > Todas las Órdenes``
2. Hacer clic en "Crear"
3. Completar información básica:
   - **Cliente**: Seleccionar cliente existente
   - **Ubicación**: Elegir ubicación del trabajo (opcional)
   - **Descripción**: Describir el trabajo a realizar
   - **Técnico responsable**: Asignar técnico principal
   - **Fecha programada**: Programar fecha y hora del servicio

4. En las pestañas adicionales:
   - **Notas**: Registrar notas internas y notas visibles para el cliente

Flujo de trabajo típico
----------------------

1. **Nueva orden** (Etapa: Nuevo)
   - Se crea la orden de trabajo
   - Se asignan técnicos
   - Se programa fecha

2. **Programación** (Etapa: Programado)
   - Se confirma la programación
   - Cliente es notificado
   - Técnicos reciben asignación

3. **Inicio de trabajo** (Etapa: En Progreso)
   - Técnico hace clic en "Iniciar Trabajo"
   - Se registra fecha/hora de inicio
   - Se puede registrar tiempo trabajado

4. **Finalización** (Etapa: Completado)
   - Técnico hace clic en "Finalizar Trabajo"
   - Se registra fecha/hora de fin
   - Se calculan totales y márgenes

Gestión de clientes y ubicaciones
--------------------------------

**Ubicaciones de servicio**:

1. Ir a ``Órdenes de Trabajo > Clientes > Ubicaciones``
2. Crear nueva ubicación:
   - Asociar a cliente
   - Completar dirección completa
   - Añadir coordenadas GPS (opcional)
   - Registrar información de acceso
   - Asociar equipos instalados

**Equipos de clientes**:

1. Ir a ``Órdenes de Trabajo > Clientes > Equipos``
2. Registrar equipos:
   - Información básica (marca, modelo, serie)
   - Fechas importantes (compra, instalación, garantía)
   - Configurar frecuencia de mantenimiento
   - Especificaciones técnicas
   - Documentación (manuales, etc.)

Integración con ventas
---------------------

**Crear orden de venta desde FSM**:

1. En una orden de trabajo, hacer clic en "Crear Orden de Venta"
2. Se crea automáticamente una orden de venta vinculada
3. Añadir líneas de productos/servicios
4. Confirmar la venta
5. Las líneas aparecerán en la pestaña "Ventas y Facturación" de la orden FSM

**Facturación**:

1. Con una orden de venta confirmada, hacer clic en "Crear Factura"
2. Se abre el wizard de facturación
3. Seleccionar líneas a facturar
4. Crear y validar factura

Vistas disponibles
=================

Órdenes de trabajo
------------------

* **Vista Kanban**: Organizada por etapas con colores personalizables
* **Vista Lista**: Tabla con información resumida y totales
* **Vista Formulario**: Formulario completo con todas las funcionalidades
* **Vista Calendario**: Calendario de servicios programados

Técnicos y equipos
-----------------

* **Vista Lista**: Listado de técnicos con estadísticas
* **Vista Formulario**: Perfil completo del técnico con habilidades
* **Botón Agenda**: Vista de calendario personal del técnico

Ubicaciones y equipos
--------------------

* **Vista Lista**: Listado con información resumida
* **Vista Formulario**: Información completa con geolocalización
* **Botones estadísticos**: Acceso rápido a órdenes y equipos relacionados

Funcionalidades avanzadas
=========================

Materiales y stock
-----------------

* Registro de materiales utilizados por orden
* Cálculo automático de costos
* Integración con gestión de inventario
* Solicitud de materiales mediante wizard

Hojas de tiempo
--------------

* Integración con módulo ``hr_timesheet``
* Registro de tiempo trabajado por técnico
* Cálculo automático de costos laborales
* Facturación de servicios basada en tiempo

Portal de clientes
-----------------

* Acceso de clientes a sus órdenes de trabajo
* Seguimiento del estado en tiempo real
* Historial de servicios realizados
* Comunicación directa con técnicos

Reportes y análisis
------------------

* Estadísticas por técnico y equipo
* Análisis de márgenes y rentabilidad
* Tiempos promedio por tipo de servicio
* Indicadores de performance (KPIs)

Configuración avanzada
=====================

Etapas personalizadas
--------------------

Las etapas se pueden personalizar completamente:

* **Nombre y descripción**
* **Color hexadecimal** para vista kanban
* **Secuencia** de ordenación
* **Etapa cerrada**: Para marcar órdenes como completadas
* **Etapa por defecto**: Para nuevas órdenes

Etiquetas y categorización
-------------------------

* Crear etiquetas personalizadas para clasificar órdenes
* Asignar colores para identificación visual
* Usar para filtros y análisis
* Asociar con técnicos especialistas

Grupos de seguridad
------------------

El módulo incluye dos grupos de usuarios:

* **FSM Usuario**:
  - Ver y editar sus propias órdenes asignadas
  - Registrar tiempo y materiales
  - Actualizar estado de órdenes

* **FSM Manager**:
  - Acceso completo a todas las funcionalidades
  - Crear y asignar órdenes
  - Configurar etapas y equipos
  - Acceso a reportes y análisis

Solución de problemas
====================

Problemas comunes
----------------

**Las órdenes no aparecen en el kanban**:
- Verificar que tengan etapa asignada
- Comprobar filtros activos
- Revisar permisos de usuario

**No se pueden crear órdenes de venta**:
- Verificar que el cliente tenga configuración fiscal correcta
- Comprobar que el usuario tenga permisos de ventas
- Revisar configuración de productos/servicios

**Los técnicos no ven sus órdenes**:
- Verificar que estén asignados a la orden
- Comprobar que tengan grupo FSM Usuario
- Revisar reglas de seguridad

**Problemas con geolocalización**:
- Verificar configuración de API de mapas
- Comprobar conexión a internet
- Revisar formato de coordenadas

Mantenimiento
============

Tareas regulares recomendadas:

* **Limpieza de órdenes antiguas**: Archivar órdenes completadas
* **Backup de configuración**: Exportar etapas y configuraciones
* **Análisis de performance**: Revisar KPIs mensualmente
* **Actualización de equipos**: Mantener información de equipos actualizada

Errores conocidos / Hoja de ruta
================================

Limitaciones actuales:

* Geolocalización requiere configuración adicional de APIs
* Reportes avanzados en desarrollo
* Integración móvil en roadmap

Próximas funcionalidades:

* App móvil para técnicos
* Optimización de rutas automática
* Integración con IoT para equipos
* Reportes avanzados con gráficos

Créditos
========

Autores
-------

* Xtendoo Software SLU

Contribuidores
--------------

* Equipo de desarrollo Xtendoo

Mantenedores
-----------

Este módulo es mantenido por Xtendoo Software SLU.

.. image:: https://www.xtendoo.es/logo.png
   :alt: Xtendoo Software SLU
   :target: https://www.xtendoo.es

Xtendoo es una empresa especializada en implementaciones de Odoo y desarrollo de módulos personalizados.

Esta documentación está sujeta a cambios según evolucione el módulo.
