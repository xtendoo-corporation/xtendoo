# Xtendoo Website Dark Mode

Addon para Odoo 18 que añade un toggle de modo oscuro/claro en la cabecera de la website y permite configurar la paleta del modo oscuro por website.

## Qué incluye

- Botón toggle en el menú superior de la website.
- Preferencia del visitante guardada en `localStorage`.
- Modo inicial configurable: claro, oscuro o seguir sistema.
- Colores configurables del modo oscuro:
  - fondo
  - texto
  - enlaces
  - fondo de cabecera
  - texto de cabecera
- Botón de mostrar/ocultar en el editor de website, dentro de las opciones del header.

## Configuración

1. Instala el módulo `xtendoo_website_darkmode`.
2. Ve a `Website > Configuración > Ajustes`.
3. En el bloque **Modo oscuro**:
   - activa la funcionalidad,
   - define el modo inicial,
   - configura los colores HEX del modo oscuro.
4. En el editor de la website, selecciona la cabecera y usa el botón del icono de ajuste/contraste para mostrar u ocultar el toggle si lo necesitas.

## Notas técnicas

- La preferencia del usuario se guarda por website.
- Si el usuario no ha elegido manualmente un modo, se aplica el modo por defecto configurado en la website.
- El addon se apoya en `website.layout` y en el placeholder del selector de idioma para inyectar el botón en la cabecera sin modificar directamente todos los layouts del header.

