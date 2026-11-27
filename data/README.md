# Datos del proyecto

`data/raw/` guarda las copias crudas que descargan las funciones `descargar_<fuente>()` de `utils/scrapers.py`, llamadas desde `tutorial.ipynb` o `scripts/02_extraccion.py` cuando `ACTUALIZAR_DATOS = True`. Nunca se editan a mano y aquí no se guarda nada procesado.

- Hay una carpeta por fuente (`uniandes/`, `atenea/`, `javeriana/`). Las páginas HTML se guardan comprimidas (`.html.gz`), los PDF tal cual y los catálogos de Uniandes como `.json`.
- Cada carpeta tiene un `manifiesto.csv` con una fila por archivo: `tipo_pagina`, `url`, `archivo`, `codigo_http` y `fecha_extraccion`.
- Una nueva descarga se escribe primero en `<fuente>_descarga/` y solo reemplaza la carpeta cuando termina: si se interrumpe, la copia anterior queda intacta.
- **Fechas de extracción de la copia actual:** 2026-11-18 para Atenea; 2026-11-22 para Uniandes; 2026-11-27 para la Javeriana. El estado de cada registro se calcula frente a la fecha de su fuente.
- El SENA (Betowa) se revisó en el reconocimiento de fuentes, pero quedó fuera de la pregunta; su caché ya no está en `data/raw/`.

## Esquema común

Las funciones `leer_<fuente>()` convierten los archivos crudos en un DataFrame de pandas con estas columnas. Lo que no se pudo extraer queda como NaN. Las columnas con varios valores los separan con "; ".

| Columna | Contenido |
|---|---|
| `nombre` | Nombre del apoyo o convocatoria. |
| `entidad` | Agencia Atenea, Universidad de los Andes o Pontificia Universidad Javeriana. |
| `nivel_formacion` | Formación para el trabajo y cursos cortos, Técnico y tecnológico, Pregrado universitario, Especialización, Maestría o Doctorado. Uniandes lo publica; en la Javeriana sale de la página (en posgrado, inferido); en Atenea es inferido. |
| `instrumento` | Beca o subsidio de matrícula, Descuento, Crédito, Crédito condonable, Crédito con pago contingente, Apoyo de sostenimiento o Formación sin costo. Uniandes lo publica (agrupado); en la Javeriana y en Atenea es inferido. |
| `area` | Uniandes: facultades del programa (publicadas). Atenea: área o sector que declara la convocatoria (inferido). Javeriana: área que indica el nombre de la beca (inferido). |
| `programas` | Programas a los que aplica (solo Uniandes lo publica). |
| `cobertura` | Qué cubre, tal como lo publica la entidad (texto). |
| `requisitos` | Requisitos o población a la que va dirigido (texto). |
| `fecha_apertura`, `fecha_cierre` | Tal como se publican (texto o ISO); se pasan a fecha en la limpieza. |
| `enlace` | Página del apoyo. |
| `fuente_url` | Sección o listado de donde se tomó. |
| `fecha_extraccion` | Día de la descarga (del manifiesto). |
| `porcentaje_min`, `porcentaje_max`, `forma_porcentaje` | Columnas adicionales: % de la matrícula que cubre, según el texto de cobertura (`extraer_porcentaje_matricula`). Solo cuenta si "matrícula" aparece justo después del número. `forma_porcentaje`: "exacto" ("Cubre 95 %"), "hasta" (tope: `porcentaje_min` queda NaN) o "rango" ("del 25 % hasta el 95 %"). Uniandes lo publica en 45 de 53 apoyos (28 son topes); la Javeriana, en 14 de 19; Atenea, en 3 de 54 (todas 100 %). |
| `n_programas` | Columna adicional: número de programas a los que aplica (Uniandes). |
| `instrumento_publicado` | Columna adicional: tipo de apoyo tal como lo nombra Uniandes, antes de agruparlo. |
| `origen_clasificacion` | Columna adicional: "catálogo de la entidad" (Uniandes), "página de la entidad y reglas de texto (inferido)" (Javeriana) o "reglas de texto (inferido)" (Atenea). |
| `requisitos_origen` | Columna adicional: `api`, `html`, `pdf` o NaN. |
| `estado_publicado` | Columna adicional: estado que muestra Atenea en su listado (las universidades no lo publican). |
| `tipo_estudiante` | Columna adicional: "Estudiante Nuevo", "Estudiante Antiguo" o "Estudiante Nuevo y Antiguo". Uniandes lo publica (`tipoDeEstudiante`); en la Javeriana sale de la página (aspirantes o estudiantes); Atenea no lo publica (NaN). |
| `descripcion` | Columna adicional: texto completo que describe el apoyo. Uniandes: sección "Descripción" de la ficha o, si no la tiene, "Cobertura"; Javeriana: texto del acordeón; Atenea: la cobertura. |
| `area_conocimiento` | Columna adicional (inferido): área de conocimiento del SNIES, común a las tres fuentes (`AREAS_SNIES`). Uniandes: sus facultades traducidas con `AREA_FACULTAD_UNIANDES`; Atenea: el sector declarado traducido con `AREA_SECTOR_ATENEA`; Javeriana: `AREAS_NOMBRE_JAVERIANA`. Los apoyos que no restringen el área quedan como "Cualquier área": sirven para los programas que ofrezca la institución, no para todas las áreas del SNIES. |

## Limpieza y validación (`tutorial.ipynb`, sección 4, o `scripts/03_limpieza_validacion.py`)

El resultado es `results/becas_apoyos.csv` (126 filas: 54 de Atenea, 53 de Uniandes y 19 de la Javeriana). Decisiones:

- **Duplicados:** no hay filas idénticas. Un registro está duplicado si repite enlace y nombre: solo hay uno, un apoyo de Uniandes que el catálogo repite. Varios apoyos distintos pueden compartir página (las becas de la Javeriana, o dos becas de maestrías virtuales de Uniandes) y se conservan. Los nombres repetidos con enlace distinto son aperturas distintas del mismo programa y se conservan.
- **Texto:** se quitan caracteres invisibles y espacios sobrantes, sin cambiar el contenido.
- **Fechas:** pasan a datetime en hora de Bogotá. Ninguna fecha publicada quedó sin convertir y no hay cierres anteriores a la apertura. Las fechas no se analizan: solo sirven para saber qué convocatorias siguen vigentes.
- **Alcance:** se excluyen 14 convocatorias de Atenea que financian proyectos de investigación, empresas (Mipymes) o prácticas laborales. No son apoyos educativos para personas (regla `PATRON_NO_ESTUDIANTES` en `utils/scrapers.py`).
- **`estado`:** abierta, cerrada (vencida), próxima o sin fecha, a la fecha de extracción de cada fuente; `criterio_estado` dice qué regla se usó.
  - En Atenea, el estado calculado con las fechas coincide con el que publica la entidad en las 52 convocatorias donde se pueden comparar. Uniandes no publica un estado propio, así que no se puede validar así.
  - Las cerradas siguen en el análisis, pero la app no las muestra.
- **`enlace_valido`:** True si el enlace respondió HTTP 200 al validarlo: 126 de 126 (los de Atenea el 2026-11-18; los de Uniandes, el 2026-11-18 o el 2026-11-26 los que no estaban en la validación guardada; los de la Javeriana, el 2026-11-27). El resultado queda en `results/validacion_enlaces.csv` (que también conserva los enlaces del SENA validados antes). Con `ACTUALIZAR_DATOS = False` se reutiliza y solo se visitan los enlaces que falten; un enlace sin validar nunca se marca como no válido.
- **`alertas`:** sin requisitos, sin fecha de cierre, enlace no válido y cierre antes de apertura. En las convocatorias cerradas de Atenea, "sin requisitos" es esperado porque sus PDF no se descargan.

## Universidad de los Andes — Apoyo Financiero

- **Sección de apoyos:** https://apoyofinanciero.uniandes.edu.co/explora-apoyos-financieros
- **Origen de datos:** el catálogo completo se obtiene del backend del segmentador (`https://segmentador.mundosoft.com.co/api/backend/supports` y `/programs`), que alimenta el buscador interactivo de la universidad. La consulta envía los encabezados que usa el propio buscador.
- **robots.txt:** el de `segmentador.mundosoft.com.co` no tiene reglas que prohíban la consulta (revisado el 2026-11-26). El de `apoyofinanciero.uniandes.edu.co` permite las fichas y bloquea `/apoyos/index.html` y `/api/`, que no se usan.
- **Fichas individuales:** cada apoyo tiene una ficha en `apoyofinanciero.uniandes.edu.co`, que se descarga respetando `robots.txt` y con pausas.
- **Formato:** JSON para el catálogo de apoyos y de programas; HTML estático (`.html.gz`) para las fichas.
- **Fecha de extracción:** 2026-11-22. Se bajaron los 2 JSON del catálogo y 52 fichas (una por enlace distinto).
- **Qué representa una fila:** un apoyo del catálogo (54 en total; 53 tras quitar un apoyo repetido). Un apoyo puede abrir convocatorias cada periodo. El método anterior (recorrer el `sitemap.xml`) solo encontraba 18 apoyos con ficha completa.
- **Cómo se llena cada campo:**
  - `nombre`: nombre oficial del apoyo (`nombreDelApoyo`).
  - `nivel_formacion`: `nivelAcadémico` ("Pregrado" pasa a "Pregrado universitario").
  - `instrumento`: `tipoDeApoyo` agrupado (`INSTRUMENTO_UNIANDES`): Beca y Beca con compromiso → Beca o subsidio de matrícula; Préstamo → Crédito; Préstamo Condonable → Crédito condonable; Descuento; Sostenimiento → Apoyo de sostenimiento. El original queda en `instrumento_publicado`.
  - `area` y `programas`: códigos de facultad y de programa traducidos a nombres con el catálogo de programas (`api_programs`, 12 facultades y 194 programas con nombre distinto).
  - `cobertura`: qué cubre (`cubre`); `requisitos`: población objetivo (`dirigidoA`); `tipo_estudiante`: `tipoDeEstudiante`; `descripcion`: sección "Descripción" de la ficha (22 fichas) o, si no la tiene, "Cobertura".
  - `fecha_apertura` y `fecha_cierre`: del bloque "Fechas de convocatoria" de cada ficha (función `extraer_fechas_uniandes`). 34 de los 54 apoyos publican fechas reconocibles (33 de los 52 tras deduplicar).
- **Problemas conocidos:**
  - Las fichas que dicen "Cerrada" o "En definición" quedan "sin fecha", no como cerradas.
  - Una ficha escribe "agostro" en lugar de "agosto"; `MESES` en `utils/scrapers.py` acepta esa variante para no perder la fecha.
  - "Decanatura de Estudiantes" aparece como facultad porque así la publica el catálogo, aunque es una unidad administrativa.
  - El servicio JSON no tiene documentación pública conocida y depende de una clave de acceso fija del buscador (`x-auth-token` en `UNIANDES_API_HEADERS`). El 2026-11-26 dejó de responder (HTTP 500, "Error durante la autenticación"). Si un catálogo no está disponible, `descargar_uniandes` reutiliza el último bueno (con su fecha original) y vuelve a bajar las fichas públicas que lista: la caché nunca se reemplaza por un error, pero un apoyo nuevo no se detectaría.
  - La fecha de extracción de cada apoyo es la de su ficha (de ahí salen las fechas de convocatoria).

## Agencia Atenea

- **Sección de convocatorias:** https://www.agenciaatenea.gov.co/convocatorias (7 páginas: `?page=0` a `?page=6`).
- **robots.txt:** permite `/convocatorias` y los PDF en `/sites/default/files/`. Bloquea `/admin/`, `/search/`, `/user/*` y carpetas de Drupal.
- **Formato:** HTML estático (Drupal) para el listado y el detalle; PDF para el lineamiento operativo. HTML con requests + BeautifulSoup; PDF con pdfplumber.
- **Fecha de extracción:** 2026-11-18. Se bajaron 8 páginas de listado (la última, vacía, marca el final), 68 detalles y 4 PDF de lineamiento.
- **Qué representa una fila:** una convocatoria publicada en el listado (68 filas, incluidas las finalizadas; 54 tras excluir las que no son apoyos para personas).
- **Cómo se llena cada campo:**
  - `nombre`: título de la convocatoria (si viene vacío, el `<title>` de la página).
  - `cobertura`: primer bloque de texto principal que dice qué se cubre ("cubre", "financia", "matrícula", "subsidio", "gratuito", "beneficio", "apoyo económico"). Si no hay, el primer bloque largo; si tampoco, la sección "Descripción", "Propósito" u "Objetivos" del acordeón.
  - `nivel_formacion`, `instrumento` y `area` (inferido): reglas de palabras clave (`NIVELES_ATENEA`, `INSTRUMENTOS_ATENEA`, `AREAS_ATENEA`) sobre el nombre y los primeros 1.000 caracteres de `cobertura`. Más adelante muchas páginas listan documentos o requisitos de exclusión que darían falsos positivos. "Beca-crédito" se lee como crédito. Si ninguna regla aplica, el campo queda en NaN.
  - Fechas: las dos etiquetas `<time datetime>` del campo de apertura y cierre (ISO con zona horaria).
  - `requisitos`: sección del acordeón sobre requisitos o a quién va dirigido. Si no existe, la sección "Requisitos … de participación" del PDF de lineamiento (función `extraer_requisitos_pdf`, recortada a 3.000 caracteres).
  - `estado_publicado`: píldora de estado de la tarjeta en el listado.
- **Líneas de apoyo (inferido; tutorial, sección 8):** cada convocatoria se asigna a la línea que la repite con reglas sobre el nombre (`LINEAS_ATENEA`; gana la primera que coincide). Las 54 convocatorias quedan en 14 líneas: 11 que se repiten y 3 convocatorias únicas, cuya línea es su propio nombre. Las de "Jóvenes a la E" sin subtítulo (primera, segunda y tercera) se asignan a instituciones privadas porque la cuarta, la quinta y la sexta siguen esa numeración. Una línea sin convocatorias en los 12 meses anteriores a la foto se marca como "posiblemente terminada". `ficha_por_linea` genera `results/tabla_lineas_apoyo.csv`; en Uniandes, cada apoyo es su propia línea.
- **Problemas conocidos:**
  - De las 54 convocatorias del análisis, 7 quedan sin nivel y 23 sin instrumento. 15 de esas 23 son cursos de Talento Capital o Todos a la U, que no dicen en su descripción cómo se financian. 41 no declaran área: financian cualquier programa de sus instituciones aliadas.
  - Las reglas pueden equivocarse con redacciones inesperadas (por ejemplo, el nombre de una institución, "Universitaria Agustiniana", cuenta como pregrado universitario).
  - Los PDF de lineamiento solo se descargan para las convocatorias no finalizadas, así que las finalizadas quedan sin requisitos.

## Pontificia Universidad Javeriana — Apoyo Financiero

- **Sección de becas:** https://www.javeriana.edu.co/apoyo-financiero/becas-y-descuentos
- **Páginas que se descargan** (`PAGINAS_JAVERIANA`): becas para aspirantes de pregrado, para aspirantes de posgrado y para estudiantes de pregrado. Cada beca es un acordeón con su título y su texto completo.
- **robots.txt:** permite las tres páginas (revisado el 2026-11-27).
- **Formato:** HTML estático (`.html.gz`). Herramientas: `requests` y `BeautifulSoup`.
- **Fecha de extracción:** 2026-11-27.
- **Qué representa una fila:** una beca (acordeón). Hay 31 acordeones; quedan 19 becas al excluir los apoyos de movilidad (sección "movilidad" o nombre con "exterior" o "intercambio": financian estancias fuera de la universidad) y unir las becas que aparecen en dos páginas.
- **Cómo se llena cada campo:**
  - `nivel_formacion` y `tipo_estudiante`: de la página (pregrado o posgrado; aspirantes = "Estudiante Nuevo", estudiantes = "Estudiante Antiguo"). En posgrado, el nivel se busca en el nombre y el texto; si no lo dice, se asumen los tres niveles de posgrado (inferido).
  - `instrumento`: "Crédito condonable" si el nombre o la sección lo dicen; si no, "Beca o subsidio de matrícula" (inferido). La sección queda en `instrumento_publicado`.
  - `cobertura`: primera oración con un porcentaje o con "matrícula"; `requisitos`: primera oración sobre requisitos, a quién va dirigida o admitidos; `descripcion`: texto completo del acordeón.
  - `area` y `area_conocimiento`: solo tres becas indican un área en su nombre (música, licenciaturas y maestrías de la Facultad de Ciencias); las demás quedan como "Cualquier área" (inferido).
  - `enlace`: la página de la beca (con el ancla del acordeón cuando la tiene).
- **Problemas conocidos:**
  - No publica fechas de convocatoria en estas páginas: todas las becas quedan "sin fecha".
  - No se incluyen los descuentos ni las becas de posgrado para estudiantes, que están en páginas sin acordeones (la segunda en el dominio `intranet.javeriana.edu.co`).

### SICORE (fuera del alcance)

- **URL:** https://sicore.agenciaatenea.gov.co/
- Es una aplicación que se arma con JavaScript (sin él solo hay 20 caracteres de texto) y exige usuario y contraseña. No publica un robots.txt real. No se raspa; se documenta como limitación.
