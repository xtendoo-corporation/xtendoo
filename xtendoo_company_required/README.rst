Xtendoo Company Required
========================

Descripcion
-----------

Este modulo extiende la funcionalidad de Odoo para asegurar que:

1. Los productos siempre tengan una empresa asignada
2. Los contactos (partners) mantengan consistencia entre su empresa y las ubicaciones de stock asignadas

Funcionalidades
---------------

Validacion de Empresa en Productos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Previene la creacion de productos sin empresa asignada
* Previene la eliminacion de la empresa de un producto existente

Validacion de Ubicaciones de Stock en Contactos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

El modulo previene inconsistencias como:

* Un partner que pertenece a la empresa A pero tiene ubicaciones de stock de la empresa B
* Garantiza que property_stock_customer y property_stock_supplier sean consistentes con la empresa del partner

Correccion Automatica
~~~~~~~~~~~~~~~~~~~~~

Migracion Automatica
^^^^^^^^^^^^^^^^^^^^

Al actualizar a la version 19.0.1.0.2, el modulo ejecuta automaticamente un script de migracion que:

* Identifica todos los partners con inconsistencias
* Corrige las ubicaciones de stock para que coincidan con la empresa del partner
* Registra en el log todos los cambios realizados

Correccion Manual
^^^^^^^^^^^^^^^^^

Los usuarios pueden corregir manualmente los partners de dos formas:

1. Desde el formulario de contacto: Un boton aparece cuando el contacto tiene empresa asignada
2. Desde la vista de lista: Seleccionar uno o varios contactos y usar la accion del menu contextual

Actualizacion Automatica
~~~~~~~~~~~~~~~~~~~~~~~~~

Cuando se cambia la empresa de un partner, el modulo actualiza automaticamente las ubicaciones de stock para mantener la consistencia.

Instalacion
-----------

1. Copiar el modulo en la carpeta de addons
2. Actualizar la lista de modulos
3. Instalar el modulo Xtendoo Company Required

Actualizacion
-------------

Si ya tienes una version anterior instalada:

1. Actualizar el codigo del modulo
2. Actualizar el modulo desde Odoo
3. El script de migracion se ejecutara automaticamente y corregira las inconsistencias existentes

Solucion de Problemas
---------------------

Error: company inconsistencies here
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Este error aparece cuando hay inconsistencias entre la empresa del partner y las ubicaciones de stock. Para solucionarlo:

* Opcion 1: Actualizar el modulo. La migracion automatica lo resolvera
* Opcion 2: Correccion manual usando el boton o accion de correccion en los contactos afectados
* Opcion 3: Por codigo ejecutar en la consola de Odoo

Notas Tecnicas
--------------

* El modulo anade constraints a nivel de modelo para prevenir futuras inconsistencias
* Las validaciones se ejecutan al crear o modificar partners
* Las ubicaciones de stock se asignan segun la empresa del partner
* Si no existen ubicaciones especificas para una empresa, se usan las ubicaciones sin empresa asignada

Dependencias
------------

* product
* point_of_sale
* stock

Autor
-----

Manuel Calero Solis (Xtendoo)

Licencia
--------

AGPL-3

