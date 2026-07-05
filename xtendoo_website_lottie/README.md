# Xtendoo Website Lottie

## Descripción

`xtendoo_website_lottie` añade soporte para animaciones Lottie JSON en el frontend de Odoo 18.0 Community.

El módulo:

- carga `lottie-web` desde assets locales;
- añade un snippet reutilizable al editor web;
- inicializa automáticamente múltiples animaciones en una misma página;
- evita dobles inicializaciones sobre el mismo elemento;
- expone una función global para reinicializar animaciones si el DOM cambia.

## Instalación

1. Copia el módulo en tu ruta de addons, en este caso dentro de `xtendoo`.
2. Descarga la librería oficial `lottie.min.js` del proyecto `lottie-web`.
3. Colócala exactamente en:

   `xtendoo_website_lottie/static/lib/lottie/lottie.min.js`

4. Añade tus animaciones `.json` en:

   `xtendoo_website_lottie/static/src/lottie/`

5. Actualiza la lista de apps e instala el módulo.

## Dónde colocar `lottie.min.js`

Este repositorio deja preparado el archivo:

`static/lib/lottie/lottie.min.js`

pero como placeholder para respetar el flujo de despliegue sin CDN. Debes sustituir su contenido por la librería oficial real antes de usar animaciones en producción.

## Dónde colocar los ficheros `.json`

Guárdalos dentro de:

`static/src/lottie/`

Puedes usar uno o varios ficheros. El snippet por defecto apunta a:

`/xtendoo_website_lottie/static/src/lottie/example.json`

## Ejemplo de uso manual

```html
<div class="xtd-lottie"
   data-lottie-path="/xtendoo_website_lottie/static/src/lottie/mi_animacion.json"
     data-lottie-loop="true"
     data-lottie-autoplay="true"
     data-lottie-renderer="svg">
</div>
```

## Comando de actualización

```bash
./odoo-bin -u xtendoo_website_lottie -d nombre_base_datos
```

## Recomendaciones

- Usa animaciones vectoriales ligeras para reducir el peso de la página.
- Evita imágenes externas embebidas dentro del JSON.
- Prueba siempre el resultado en móvil.
- Usa `svg` como renderer por defecto.
- No dependas de CDN en producción.

## Uso desde el editor web

Una vez instalado el módulo, el snippet `Lottie Animation` estará disponible en el panel de snippets de Website. Inserta el bloque y cambia la ruta del JSON mediante el atributo `data-lottie-path` si necesitas otra animación.

## Nota sobre el ejemplo JSON

El fichero `static/src/lottie/example.json` es un placeholder válido y mínimo para dejar el módulo estructurado. Sustitúyelo por una animación real exportada desde LottieFiles, Bodymovin o una herramienta equivalente cuando prepares contenido definitivo.
