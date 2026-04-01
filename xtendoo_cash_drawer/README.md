# Xtendoo Cash Drawer

Módulo de Odoo para configurar el cajón portamonedas en el Punto de Venta.

## Descripción

Este módulo añade en la configuración del TPV dos campos necesarios para gestionar
la apertura del cajón portamonedas:

- **Nombre de la impresora**: Nombre exacto del dispositivo de impresión tal como
  aparece en el sistema operativo o servidor de impresión (p. ej. `EPSON TM-T20III`).
- **URL de apertura del cajón**: Dirección URL a la que se envía la petición de
  apertura del cajón portamonedas (p. ej. `http://localhost:9100/open_drawer`).

## Configuración

Los campos están disponibles en dos lugares:

1. **Ajustes del TPV individual** — `Punto de Venta > Configuración > TPV > (formulario)`
   en la sección *Cajón portamonedas*.
2. **Ajustes generales del POS** — `Ajustes > Punto de Venta` en la sección de
   *Dispositivos conectados*.

## Autor

- **Empresa**: Xtendoo
- **Sitio web**: https://xtendoo.es
- **Licencia**: LGPL-3

