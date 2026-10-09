# xtendoo_hr_attendance_mobile_portal

Fichaje desde el móvil (`/fichaje`) sobre el modelo estándar `hr.attendance`, sin cuenta de
backend. Odoo 19. Depende solo de `hr_attendance` (no requiere `website`).

## Uso
1. **Ajustes > Asistencias > Portal móvil de fichaje**: activar por empresa (desactivado por defecto).
2. Ficha del empleado > pestaña **Fichaje móvil** > *Generar enlace de activación*. El enlace se
   muestra una sola vez (en BD solo se guarda su hash). Enviarlo al empleado por el canal que se quiera.
3. El empleado abre el enlace, pulsa *Activar* y ese dispositivo queda vinculado (cookie `HttpOnly`).
4. **Desvincular dispositivo** (p. ej. cambio de móvil): cierra la sesión de ese dispositivo y el MISMO enlace
   vuelve a funcionar (con la caducidad renovada). **Renovar**: anula el acceso y genera un enlace nuevo.
5. Revocación: botón *Revocar* en la ficha, o menú Asistencias > Configuración > *Accesos de fichaje móvil*.
   El empleado también puede cerrar sesión desde el portal.

## Configuración (por empresa)
Validez del enlace (48 h), validez de la sesión (90 días), política de ubicación
(`optional` = ficha igualmente y marca el estado; `required` = rechaza), precisión máxima (100 m),
aviso de ubicación (texto mostrado al empleado).

## Seguridad
* Tokens `secrets.token_urlsafe(32)`, guardados como SHA-256, caducidad. El enlace solo sirve para un dispositivo a la vez:
  mientras haya uno vinculado no se puede reutilizar (salvo que se desvincule).
* El GET del enlace solo muestra una pantalla de confirmación (los previsualizadores de WhatsApp/correo
  no consumen el enlace); la activación es un POST con CSRF.
* Escritura (`/fichaje/marcar`, `/fichaje/salir`) con CSRF obligatorio. El empleado sale siempre de la
  sesión, nunca de parámetros de la petición.
* Límite de 5 activaciones fallidas / 15 min por IP (se guarda un hash con clave de la IP).
* El fichaje delega en `hr.employee._attendance_action_change` (restricciones estándar de Odoo),
  con bloqueo de fila del empleado y comprobación de "estado esperado" contra dobles pulsaciones.
* `sudo()` solo en el servicio tras validar la sesión, acotado a un empleado.

## Ubicación y limitaciones
* Se pide únicamente al pulsar el botón (`getCurrentPosition`, sin seguimiento).
* **Es declarativa**: la envía el navegador y puede falsearse; no es prueba auténtica.
* Si se deniega o falla, con política `optional` el fichaje se registra marcado como
  *Permiso denegado* / *No disponible* (`in_/out_location_status`) y sin coordenadas.
* Requiere HTTPS en producción (`localhost` vale en desarrollo).
* PWA básica: manifiesto + iconos, sin service worker. El diálogo de instalación depende del navegador
  (puede no aparecer; hay instrucciones manuales). En iPhone, la cookie de Safari puede no compartirse con la
  app añadida a la pantalla de inicio: **no verificado en dispositivo real**.
* No hay geovalla, mapa, notificaciones ni integración de mensajería.

## Tests
```
docker compose run --rm -e PGDATABASE=<bd> odoo odoo -d <bd> --db-filter='^<bd>$' \
  -u xtendoo_hr_attendance_mobile_portal --test-enable \
  --test-tags /xtendoo_hr_attendance_mobile_portal --stop-after-init --workers=0
```
`--db-filter` es necesario si hay varias BD (los tests HTTP no llevan sesión).
