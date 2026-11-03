# Exposición de herramientas: prueba de carga diferida (ola 2A)

Prueba real contra la API de Anthropic (claude-haiku-5-5, 30-10-2026) con las 46
herramientas que ve el administrador.

| Prueba                                                                    | Resultado                                                                                                                              |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 46 herramientas `strict`, sin diferir                                     | 400 «Too many strict tools (46). The maximum … is 20»                                                                                  |
| 46 `strict`, 40 con `defer_loading` + `tool_search_tool_regex` (o `bm25`) | **mismo 400**: las diferidas cuentan para el límite de 20                                                                              |
| 4 diferidas `strict` con 49 parámetros opcionales                         | 400 «too many optional parameters (49) … limit: 24»: también cuentan                                                                   |
| Base (6) `strict` + 40 diferidas sin `strict`                             | OK; Haiku busca, carga y llama a la herramienta diferida                                                                               |
| Misma petición repetida                                                   | `cache_read` > 0: descubrir herramientas no rompe la caché                                                                             |
| `load_skill` (herramienta propia) devolviendo bloques `tool_reference`    | OK; el `tool_result` solo puede llevar referencias (con texto: 400 «cannot be mixed»), el texto va en un bloque aparte del mismo turno |

Conclusión: la gramática `strict` se compila sobre **todo** el array `tools`, diferidas
incluidas, así que diferir no sirve para escapar de los límites (20 strict, 24
opcionales, «compiled grammar is too large»). Sí sirve para no meter en contexto ni en
el prefijo cacheado las herramientas que no tocan.

## Diseño elegido

- **Selección por área al inicio de cada petición, sin LLM** (`_xtd_ai_request_areas`):
  modelo de la pantalla, palabras de los dos últimos mensajes del usuario (catálogo
  `_xtd_ai_skill_hints` de cada módulo) y áreas de las herramientas usadas en la última
  respuesta. No depende del rol: el administrador recibe la misma selección que
  cualquiera.
- Se cargan las herramientas _core_ (sin skill, más `search_partners`) y las de las
  áreas elegidas; el resto va con `defer_loading: true` (`xtdDeferred` en `tools/list`).
- **`load_skill` carga un área a mitad de tarea**: devuelve sus herramientas como
  `tool_reference` (búsqueda de herramientas propia, sin herramienta de búsqueda del
  servidor). El array `tools` no cambia dentro de la ejecución: la caché se conserva.
- `strict` se reparte sobre todo el array: primero escrituras cargadas, luego lecturas
  cargadas y por último diferidas, dentro de 20 herramientas y 24 opcionales. El
  fallback de la ola 1B («compiled grammar is too large» → reducir strict) sigue como
  red.
- `xtd_ai.tool_exposure = all` vuelve a cargarlo todo (interruptor de emergencia).
