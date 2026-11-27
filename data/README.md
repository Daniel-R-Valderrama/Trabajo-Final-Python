# Datos del proyecto

`data/raw/` guarda las copias crudas que descargan las funciones `descargar_<fuente>()` de `utils/scrapers.py`, llamadas desde `scripts/02_extraccion.py` cuando `ACTUALIZAR_DATOS = True`. Nunca se editan a mano y aquí no se guarda nada procesado.

- Hay una carpeta por fuente (`uniandes/`, `atenea/`, `betowa/`). Las páginas HTML se guardan comprimidas (`.html.gz`) y los PDF tal cual.
- Cada carpeta tiene un `manifiesto.csv` con una fila por archivo: `tipo_pagina`, `url`, `archivo`, `codigo_http` y `fecha_extraccion`.
- Una nueva descarga sobrescribe la carpeta y borra los archivos que ya no estén en el manifiesto.
- **Fecha de extracción de la copia actual: 2026-11-18** (las tres fuentes).

## Esquema común

Las funciones `leer_<fuente>()` convierten los archivos crudos en un DataFrame de pandas con estas columnas. Lo que no se pudo extraer queda como NaN.

| Columna | Contenido |
|---|---|
| `nombre` | Nombre del apoyo, convocatoria o programa. |
| `entidad` | Universidad de los Andes, Agencia Atenea o SENA. |
| `tipo` | "beca", "apoyo financiero" o "formación gratuita". Regla explícita (`clasificar_tipo`): si el texto dice "formación gratuita", es formación gratuita; si menciona "beca", es beca; si no, apoyo financiero. El SENA siempre es "formación gratuita". |
| `cobertura` | Qué cubre, tal como lo publica la entidad (texto). |
| `requisitos` | Requisitos o población a la que va dirigido (texto). |
| `fecha_apertura`, `fecha_cierre` | Tal como se publican (texto o ISO); se pasan a fecha en la Fase 3. |
| `enlace` | Página del apoyo. |
| `fuente_url` | Sección o listado de donde se tomó. |
| `fecha_extraccion` | Día de la descarga (del manifiesto). |
| `requisitos_origen` | Columna adicional: `html`, `pdf` o NaN. |
| `estado_publicado` | Columna adicional: estado que muestra Atenea en su listado (las otras fuentes no lo publican). |
| `periodos_cursos` | Columna adicional: períodos académicos de los cursos del SENA, cuando los publica. |

## Limpieza y validación (Fase 3, `scripts/03_limpieza_validacion.py`)

El resultado es `results/becas_apoyos.csv` (303 filas). Decisiones:

- **Duplicados:** no hay filas ni enlaces repetidos. Los nombres repetidos con enlace distinto son aperturas distintas del mismo programa y se conservan.
- **Texto:** se quitan caracteres invisibles y espacios sobrantes, sin cambiar el contenido.
- **Fechas:** pasan a datetime en hora de Bogotá. Ninguna fecha publicada quedó sin convertir y no hay cierres anteriores a la apertura.
- **Alcance:** se excluyen 14 convocatorias de Atenea que financian proyectos de investigación, empresas (Mipymes) o prácticas laborales. No son apoyos educativos para personas (regla `PATRON_NO_ESTUDIANTES` en `utils/scrapers.py`).
- **`estado`:** abierta, cerrada, próxima o sin fecha, a la fecha de extracción; `criterio_estado` dice qué regla se usó.
  - Se agregó "próxima" porque hay convocatorias publicadas que todavía no abren.
  - En Atenea, el estado calculado con las fechas coincide con el que publica la entidad en las 52 convocatorias donde se pueden comparar.
- **`enlace_valido`:** True si el enlace respondió HTTP 200 al validarlo (303 de 303 el 2026-11-18). El resultado queda en `results/validacion_enlaces.csv` y se reutiliza cuando `ACTUALIZAR_DATOS = False`.
- **`alertas`:** sin requisitos, sin fecha de cierre, enlace no válido, cierre antes de apertura y período vencido aún publicado. En las convocatorias cerradas de Atenea, "sin requisitos" es esperado porque sus PDF no se descargan.

## Universidad de los Andes — Apoyo Financiero

- **Sección de apoyos:** https://apoyofinanciero.uniandes.edu.co/explora-apoyos-financieros
- **Origen de datos:** El catálogo completo se obtiene consumiendo el backend del segmentador (`https://segmentador.mundosoft.com.co/api/backend/supports` y `/programs`), que alimenta el buscador interactivo de la universidad.
- **Fichas individuales:** Cada apoyo tiene una URL oficial a su ficha individual en `apoyofinanciero.uniandes.edu.co`, la cual se descarga respetando `robots.txt` y con pausas de cortesía.
- **Formato:** JSON estructurado para el catálogo de apoyos y HTML estático (`.html.gz`) para las fichas de detalle.
- **Qué representa una fila:** un apoyo financiero o beca de la Universidad de los Andes (54 apoyos en total; 52 tras deduplicar enlaces).
- **Cómo se llena cada campo:**
  - `nombre`: nombre oficial del apoyo (`nombreDelApoyo`).
  - `tipo`: clasificado con la regla del proyecto a partir de `tipoDeApoyo` y nombre ("beca" o "apoyo financiero").
  - `cobertura`: qué cubre (`cubre`).
  - `requisitos`: población objetivo y requisitos (`dirigidoA`).
  - `fecha_apertura` y `fecha_cierre`: se extraen del bloque "Fechas de convocatoria" del HTML de cada ficha individual mediante expresiones regulares en español (34 apoyos publican fechas de convocatoria activas/vigentes). Si no publica fechas o dice "Cerrada" / "En definición", queda como NaN.

## Agencia Atenea

- **Sección de convocatorias:** https://www.agenciaatenea.gov.co/convocatorias (7 páginas: `?page=0` a `?page=6`).
- **robots.txt:** permite `/convocatorias` y los PDF en `/sites/default/files/`. Bloquea `/admin/`, `/search/`, `/user/*` y carpetas de Drupal.
- **Formato:** HTML estático (Drupal) para el listado y el detalle; PDF para el lineamiento operativo. HTML con requests + BeautifulSoup; PDF con pdfplumber.
- **Fecha de extracción:** 2026-11-18. Se bajaron 8 páginas de listado (la última, vacía, marca el final), 68 detalles y 4 PDF de lineamiento.
- **Qué representa una fila:** una convocatoria publicada en el listado (68 filas, incluidas las finalizadas).
- **Cómo se llena cada campo:**
  - `nombre`: título de la convocatoria (si viene vacío, el `<title>` de la página).
  - `cobertura`: primer bloque de texto principal que dice qué se cubre ("cubre", "financia", "matrícula", "subsidio", "gratuito", "beneficio", "apoyo económico"). Si no hay, el primer bloque largo; si tampoco, la sección "Descripción", "Propósito" u "Objetivos" del acordeón.
  - Fechas: las dos etiquetas `<time datetime>` del campo de apertura y cierre (ISO con zona horaria).
  - `requisitos`: sección del acordeón sobre requisitos o a quién va dirigido. Si no existe, la sección "Requisitos … de participación" del PDF de lineamiento (función `extraer_requisitos_pdf`, recortada a 3.000 caracteres).
  - `estado_publicado`: píldora de estado de la tarjeta en el listado.
- **Problemas conocidos:**
  - Los PDF de lineamiento solo se descargan para las convocatorias no finalizadas: a quien busca hoy no le sirven los requisitos de una convocatoria cerrada, y así el .zip pesa menos. Por eso 59 finalizadas quedan sin requisitos.
  - De las 8 no finalizadas, 5 tienen requisitos. Las 3 que abren en diciembre de 2026 aún no publican lineamiento.
  - Cuando un lineamiento cubre varias líneas (por ejemplo Jóvenes a la E 6), se toma la primera sección de requisitos que aparece.
  - Hay convocatorias dirigidas a grupos de investigación, no a estudiantes (por ejemplo "Retos de Investigación en Salud"). Se conservan en la extracción y se decide su tratamiento en la Fase 3.
  - La regla de `tipo` depende de las palabras del texto: programas de la misma familia (Jóvenes a la E) pueden quedar como "beca" o como "apoyo financiero" según cómo esté redactada cada convocatoria.

### SICORE (fuera del alcance)

- **URL:** https://sicore.agenciaatenea.gov.co/
- Es una aplicación que se arma con JavaScript (sin él solo hay 20 caracteres de texto) y exige usuario y contraseña. No publica un robots.txt real. No se raspa; se documenta como limitación.

## SENA — Betowa

- **Sección de oferta:** https://betowa.sena.edu.co/oferta (490 programas en todo el país).
- **Listado que se recorre:** `https://betowa.sena.edu.co/oferta?location=57011001&page_size=100&page=N`. El código 57011001 es el de Bogotá en el filtro "Ubicación"; se identificó al filtrar en el navegador. Da 231 programas en 3 páginas.
- **robots.txt:** permite `/` y `/api/`. Bloquea `/_next/static/`, imágenes, CSS y JS.
- **Formato:** HTML que arma el servidor (Next.js); los programas ya vienen en la respuesta, sin ejecutar JavaScript. Se lee con requests + BeautifulSoup.
- **Fecha de extracción:** 2026-11-18. 3 páginas de listado y 231 detalles.
- **Qué representa una fila:** un programa con oferta en Bogotá, por modalidad (la URL de detalle lleva `programId` y `modality`). No son becas: es formación gratuita.
- **Cómo se llena cada campo:**
  - `cobertura`: "Formación gratuita del SENA" (el portal se presenta como de formación gratuita) más el tipo de programa, el nivel y la duración.
  - `requisitos`: edad mínima más el texto de "Requisitos para inscribirte en este programa".
  - `fecha_apertura` y `fecha_cierre` quedan en NaN porque Betowa no las publica. `periodos_cursos` guarda los períodos académicos de los cursos cuando aparecen.
- **Problemas conocidos:**
  - Los 231 programas son formación complementaria: 228 con nivel "Complementaria virtual" y 3 con nivel "Curso especial". En la fecha de extracción no hay técnicos ni tecnólogos publicados para Bogotá.
  - Solo 3 de 231 programas publican período académico, y uno de ellos es de 2015 y otro de 2019: hay oferta antigua que sigue publicada.
  - Los cursos virtuales aparecen al filtrar cualquier ciudad; que estén "en Bogotá" significa que se pueden tomar desde Bogotá.
