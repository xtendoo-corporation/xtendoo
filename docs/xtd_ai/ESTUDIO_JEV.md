# Estudio: ¿qué papel puede tener Jev en el agente IA de Odoo?

Fecha: 2026-10-20. Investigación solo documental: no se ha creado cuenta, ni llamado a
la API, ni enviado datos nuestros.

## 1. Resumen y recomendación

**No usar Jev en la ruta principal ahora. Hacer, como mucho, un piloto offline en modo
sombra con el banco de preguntas (datos demo), para un solo uso: el enrutado de
área/skill antes del LLM.** Nuestro cuello de botella no es el coste (0,0007 $/pregunta;
Jev ahorraría fracciones de céntimo) sino la latencia (7,4 s), y de esa latencia la
parte evitable es sobre todo la vuelta extra de `load_skill` (31 de 49 preguntas). Esa
vuelta se puede eliminar sin proveedor nuevo (precarga de skill por reglas o skill de
área en el prompt cacheado), y eso debe probarse primero. Jev solo tendría sentido si,
tras esa línea base, un clasificador de ~0,3 s añade acierto o ahorro medible. Para
seguridad (inyección, "fuera de rol") **no**: el propio fabricante lo declara débil con
contenido adversarial y no apto como frontera de seguridad, y sumaría un segundo
encargado del tratamiento en EE. UU. con retención no documentada.

## 2. Qué es Jev

**Hechos verificados en documentación primaria o reflejada por varias fuentes:**

- Modelo de "decisiones tipadas": recibe `state` (texto/JSON) y un mapa `questions`, y
  devuelve tipos acotados (Choice con probabilidades y `confidence`, Score 2-10 niveles,
  Noul = probabilidad de verdadero). No genera prosa ni explicaciones.
- Endpoint `POST /v1/systemone`; modelos `jev-1.13.0`, `jev-1.14.0` (desde 14-oct-2026);
  `jev-latest` apunta a 1.13. Disponible también vía Cloudflare, OpenRouter y Requesty
  (en Requesty la integración es "experimental", sin streaming y puede cambiar sin aviso
  de deprecación).
- Precio: 0,042 $/Mtok de entrada, salida gratis. Contexto 64k por petición y 32k por
  pregunta (modo "long context" hasta 262k, más lento y menos preciso). Solo texto; el
  inglés da la mejor precisión.
- Límites de tasa por organización (429 al excederlos). No se declara nada de regiones,
  SLA ni inyección de prompt en la página de modelos.
- Reconocido por TypeSafe como débil en: aritmética y conteo, comparación de fechas,
  preguntas negadas o indirectas, mucho contexto irrelevante, **contenido adversarial en
  el estado**; "no usar como frontera de seguridad". Tipado seguro no implica corrección
  semántica.
- No se entrena con datos de clientes. Retención: la página remite al DPA y a "ZDR para
  enterprise"; fuentes secundarias dicen que el DPA no fija plazo y que no hay región UE
  documentada (hosting EE. UU., con cláusulas contractuales tipo).

**Afirmaciones de la empresa (no verificadas de forma independiente):** latencia 70-500
ms, "193× más rápido, 444× más barato" (TypeSafe admite que sale de flujos internos y es
el extremo alto). El único dato de cliente es de un caso propio (Jack & Jill: retención
de preselección 94,6 % frente a 93,9 % de Gemini Flash Lite, diferencia no
significativa). No encontré evaluación independiente reproducida. Producto de ~1 mes.

## 3. Encaje en nuestro flujo

Referencia medida (Haiku): 7,4 s de media, 2,4 iteraciones (~3 s por llamada al LLM),
~18k tokens de entrada casi todo cacheado, 2,3 herramientas, 45/49.

| #   | Uso                                                          | Beneficio estimado                                                                                                                                                          | Riesgo                                                                                                                 | Veredicto                                                                                    |
| --- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 1   | Router de área/skill antes del LLM                           | Quitar la vuelta de `load_skill` (~2-3 s en ~63 % de preguntas, es decir ~1,5 s de media) menos ~0,3 s del salto; coste: sin ahorro real, la caché ya abarata tools+sistema | Español con erratas ("confimaods"), inglés es su punto fuerte; un área errónea empeora la respuesta; segundo proveedor | **Piloto sombra**, tras probar la alternativa sin Jev                                        |
| 2   | Clasificador de inyección sobre `untrusted_text` o mensajes  | Poco: ya hay envoltorio, truncado a 300 caracteres, confirmación previa y guarda ORM (T1, T5)                                                                               | TypeSafe lo cita como debilidad; envía texto no confiable de clientes a un 2.º encargado; falsa sensación de seguridad | **No**                                                                                       |
| 3   | Pre-check "fuera de rol/acción prohibida"                    | Ninguno: Odoo ya impone permisos; los `refuse` pasan 8/8                                                                                                                    | Falsas denegaciones, ruido, frontera de seguridad paralela                                                             | **No**                                                                                       |
| 4   | Enrutado de modelo Haiku vs Sonnet                           | Los 4 fallos del banco son de datos/expectativas (compañía no permitida, valores esperados), no de capacidad; estimar "dificultad" es justo lo que Jev lee mal              | Perder caché por cambio de modelo (§7 del plan); complejidad                                                           | **No por ahora**; revisar si aparecen fallos de capacidad                                    |
| 5   | Respuesta sin LLM para consultas triviales                   | Latencia de 7 s a ~1 s en lookups                                                                                                                                           | Rompe la conversación, plantillas por área, auditoría y mantenimiento; Haiku ya cuesta céntimos                        | **No**; mejor optimizar el bucle                                                             |
| 6   | Anomalías en la tarjeta de confirmación (cantidades/precios) | Valor real, pero es aritmética y comparación numérica, su punto débil                                                                                                       | Falsos positivos que adormecen al usuario                                                                              | **No con Jev**: reglas deterministas en Odoo (precio vs tarifa/histórico, cantidad vs media) |

Alternativas sin Jev para el mismo objetivo (hacerlas antes): precarga de la skill por
reglas simples (palabras clave, apps/grupos del usuario), o skills cortas de área dentro
del bloque cacheado; fusionar `get_user_context` en el arranque. Si con eso `load_skill`
cae a ~0 y la latencia baja cerca de 5,5 s, Jev no aporta.

Presupuesto: una llamada Jev con ~2k tokens cuesta ~0,00008 $, un ~11 % de la pregunta;
irrelevante en coste. El valor está solo en ~0,3 s frente a ~3 s de una iteración de
Haiku, y solo si evita esa iteración.

## 4. Propuesta concreta

**Experimento único: router de skill en modo sombra.**

- **Puerto opcional** en `ai_service/xtd_ai_service/domain/ports.py`:
  `DecisionProvider.decide(state: str, questions: Mapping) -> Mapping`, sin SDK en el
  dominio; adaptador `providers/jev.py` y `providers/null.py` (por defecto, sin efecto).
  Configuración `XTD_AI_DECISION_PROVIDER=none|jev`.
- **Dónde se llama:** en `domain/loop.py` antes de la primera `complete()`. Entrada:
  solo el mensaje del usuario y la lista de nombres de skills (nunca resultados de
  herramientas ni datos de negocio). Pregunta Choice sobre el área con timeout de ~800
  ms.
- **Fallback:** cualquier error, 429, timeout o `confidence` baja lleva al
  comportamiento actual (el modelo llama a `load_skill`). Nunca bloquea ni cambia la
  seguridad.
- **Fase 0 (sin Jev):** implementar precarga por reglas y repetir el banco. Es la línea
  base.
- **Fase 1 (sombra, datos demo):** sobre las 49 preguntas, pedir a Jev el área y
  compararla con la skill que Haiku cargó y con la etiqueta del banco. No altera el
  flujo. Coste del piloto: menos de 0,01 $ vía API directa (o OpenRouter para no abrir
  cuenta nueva). Solo datos sintéticos, nunca de clientes.
- **Fase 2 (activa en banco):** inyectar la skill elegida y medir.
- **Criterios de adopción (todos):** acierto de área ≥ 95 % (≥ 90 % con erratas);
  `confidence` calibrada (los errores concentrados en confianza baja); aprobadas ≥ 45/49
  sin regresión; latencia media al menos 1 s por debajo de la línea base de la Fase 0;
  p90 de Jev < 600 ms; coste por pregunta no sube más de un 15 %. Si no se cumplen,
  descartar.
- Pinar `jev-1.13.0`/`1.14.0` (no `latest`) y repetir el banco en cada cambio de
  versión.

## 5. Riesgos y qué pedir a TypeSafe

- **Vendor:** un mes de vida, cifras de rendimiento autodeclaradas, integraciones
  "experimentales", versiones que cambian rápido (1.13 a 1.14 en un mes).
- **Seguridad:** nunca frontera de seguridad; ningún permiso ni decisión de escritura
  depende de Jev. Odoo sigue siendo el límite (T2, T5, T8).
- **RGPD:** segundo encargado, hosting en EE. UU., retención sin plazo claro. Mensajes
  de usuario pueden contener datos personales. Mientras no haya garantías, solo datos
  demo.
- **Disponibilidad:** salto de red extra y 429; el diseño con fallback lo cubre, pero
  hay que registrar la tasa de fallback.
- **Antes de usarlo con datos de cliente, exigir por escrito:** DPA firmable con plazo
  de retención y ZDR confirmado en nuestra cuenta; región UE o vía UE (p. ej. proveedor
  europeo) o justificación de transferencia; lista de subencargados; SLA y política de
  deprecación de versiones; resultados de calidad en español; comportamiento ante
  contenido adversarial.

Incertidumbres: no pude leer el DPA ni la página legal ni las páginas de TypeSafe sobre
región; la calidad en español no está documentada; la latencia real desde España no está
medida.

## 6. Fuentes

- [TypeSafe docs: modelos, límites, precio](https://docs.typesafe.ai/models)
- [Requesty: Jev explicado (API, limitaciones, experimental)](https://www.requesty.ai/blog/typesafe-jev-explained)
- [Referencia comunitaria (gist pjburnhill), tercero](https://gist.github.com/pjburnhill/adf8d28efcad9df037bfdece178ef965)
- [Cloudflare AI docs: Jev](https://developers.cloudflare.com/ai/models/typesafe/jev/)
  (solo vía resumen de búsqueda, no leído)
- [NeuralTrust: guía de seguridad](https://neuraltrust.ai/blog/jev-typesafe-ai-security)
  (solo vía resumen de búsqueda)
- [innFactory: Jev](https://innfactory.ai/en/ai-models/typesafe-jev/) (solo vía resumen
  de búsqueda)
- [Futura Sciences](https://www.futura-sciences.com/en/?p=900220),
  [NewsBytes](https://www.newsbytesapp.com/news/science/chatgpt-co-inventor-unveils-jev-a-new-kind-of-frontier-ai/story),
  [GT OMSCS](https://omscs.gatech.edu/external-news/new-kind-ai-model-chatgpt-inventor-thrilling-developers),
  [Towards AI](https://pub.towardsai.net/what-is-jev-and-why-is-everyone-talking-about-it-a20ebe495ac2),
  [Level Up](https://levelup.gitconnected.com/jev-ai-the-cheaper-model-that-runs-faster-than-claude-and-gpt-51c618fd25ac)
  (cobertura de prensa; no accesibles por mí)
