"""Funciones auxiliares reutilizables del proyecto.

Hay dos tipos de funciones por fuente (Universidad de los Andes y Agencia Atenea):
- descargar_<fuente>(): recorre el sitio (respetando robots.txt y con pausas) y guarda los
  insumos crudos en data/raw/<fuente>/ junto con un manifiesto (qué URL, qué archivo, qué fecha).
  Solo se usa cuando ACTUALIZAR_DATOS = True.
- leer_<fuente>(): lee esos archivos crudos (sin internet) y devuelve un DataFrame con el esquema común.

Uniandes publica el nivel de formación, el instrumento y los programas en su catálogo; en Atenea
esas columnas se deducen del texto con reglas explícitas (NIVELES_ATENEA, INSTRUMENTOS_ATENEA,
AREAS_ATENEA). Al final están las funciones de limpieza (texto y fechas), de estado de las
convocatorias y de validación de enlaces.

Las páginas HTML se guardan comprimidas (.html.gz) para que el .zip del tutorial no pese demasiado.
Todas las rutas son relativas a la raíz del proyecto.
"""

import gzip
import json
import re
import shutil
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------------------
# Configuración común
# --------------------------------------------------------------------------------------
CARPETA_RAW = Path("data/raw")
USER_AGENT = "Mozilla/5.0 (compatible; TallerPythonUniandes/1.0; proyecto academico)"
PAUSA_SEGUNDOS = 2

UNIANDES_BASE = "https://apoyofinanciero.uniandes.edu.co"
UNIANDES_API_BASE = "https://segmentador.mundosoft.com.co/api/backend"
UNIANDES_API_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "referer": "https://segmentador.mundosoft.com.co/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36 Edg/158.0.0.0",
    "x-auth-token": "MUzfpQwzzhWVGEG70oxpV4gokrSBaeNFs3PSi8La",
    "x-connection-code": "19"
}
ATENEA_BASE = "https://www.agenciaatenea.gov.co"

# Separador de las columnas que pueden tener varios valores (un apoyo puede servir a varios niveles).
SEPARADOR = "; "

ESQUEMA = ["nombre", "entidad", "nivel_formacion", "instrumento", "area", "programas", "cobertura",
           "requisitos", "fecha_apertura", "fecha_cierre", "enlace", "fuente_url", "fecha_extraccion"]
# Columnas adicionales:
# - n_programas: número de programas a los que aplica (solo Uniandes lo publica).
# - instrumento_publicado: tipo de apoyo tal como lo nombra Uniandes, antes de agruparlo.
# - origen_clasificacion: si nivel, instrumento y área vienen del catálogo de la entidad o de reglas de texto.
# - requisitos_origen: de dónde salió el texto de requisitos (api, html, pdf o NaN).
# - estado_publicado: estado que la propia entidad muestra (solo Atenea lo publica).
# - porcentaje_min, porcentaje_max, forma_porcentaje: % de la matrícula que cubre, según el texto publicado
#   (extraer_porcentaje_matricula).
COLUMNAS_EXTRA = ["porcentaje_min", "porcentaje_max", "forma_porcentaje", "n_programas", "instrumento_publicado",
                  "origen_clasificacion", "requisitos_origen", "estado_publicado"]

# Categorías comunes de instrumento financiero. Uniandes publica su propio tipo de apoyo y se agrupa así:
INSTRUMENTO_UNIANDES = {
    "Beca": "Beca o subsidio de matrícula",
    "Beca con compromiso": "Beca o subsidio de matrícula",
    "Préstamo": "Crédito",
    "Préstamo Condonable": "Crédito condonable",
    "Descuento": "Descuento",
    "Sostenimiento": "Apoyo de sostenimiento",
}
# Uniandes publica "Pregrado"; se nombra igual que en Atenea para poder comparar.
NIVEL_UNIANDES = {"Pregrado": "Pregrado universitario"}

# Reglas para Atenea, que no publica estas categorías en campos aparte. Se buscan en el nombre y en los
# primeros CARACTERES_REGLAS caracteres de la descripción: ahí cada convocatoria dice qué financia.
# Más adelante muchas páginas listan documentos o requisitos de exclusión ("no haber cursado un programa
# técnico, tecnológico o universitario"), que producirían falsos positivos.
CARACTERES_REGLAS = 1000
NIVELES_ATENEA = {
    "Formación para el trabajo y cursos cortos": (
        r"formaci[oó]n para el trabajo|t[eé]cnicos?[- ]laboral|ciclos? cortos?|talento capital|todos a la u"
        r"|cursos? (?:de formaci[oó]n|virtual|gratuit)|el curso es gratuito|ingl[eé]s|habilidades digitales|\betdh\b"),
    "Técnico y tecnológico": r"t[eé]cnic[oa]s?[- ]profesional|tecnol[oó]gic[oa]s?\b|t[eé]cnica y tecnol",
    "Pregrado universitario": r"universitari|pregrado|universidades?:",
    "Especialización": r"especializaci[oó]n",
    "Maestría": r"maestr[ií]a",
    "Doctorado": r"doctorado",
}
INSTRUMENTOS_ATENEA = {
    "Beca o subsidio de matrícula": r"\bbecas?\b|\bsubsidi|cubre[^.]{0,40}matr[ií]cula|valor de la matr[ií]cula",
    "Crédito condonable": r"condonable",
    "Crédito con pago contingente": r"contingente",
    "Apoyo de sostenimiento": r"sostenimiento|apoyo econ[oó]mico|canasta",
    "Formación sin costo": r"\bgratuit",
}
# Área o sector que la convocatoria declara. Las siglas (TI, STEM, BPO) solo cuentan en mayúsculas.
AREAS_ATENEA = {
    "Tecnologías digitales": (r"habilidades digitales|marketing digital|(?-i:\bTI\b)|\bnube\b|software"
                              r"|tecnolog[ií]as de la informaci|inteligencia artificial|creativas digitales"),
    "Idiomas": r"ingl[eé]s|segunda lengua",
    "Ciencia y tecnología (STEM)": r"(?-i:\bSTEM\b)",
    "Construcción": r"\bconstrucci[oó]n\b",
    "Servicios (turismo, belleza, salud y otros)": (r"(?-i:\bBPO\b)|turismo|belleza|gastronom|cosmetolog"
                                                     r"|salud y cuidado|pecuario|sector de servicios"),
}


def limpiar_texto(texto):
    """Une espacios y saltos de línea repetidos; devuelve NaN si el texto queda vacío."""
    texto = " ".join(str(texto).split()) if texto is not None else ""
    return texto or float("nan")


def clasificar_por_reglas(texto, reglas):
    """Categorías cuya regla (expresión regular) aparece en el texto, unidas con SEPARADOR; NaN si ninguna."""
    categorias = [nombre for nombre, patron in reglas.items() if re.search(patron, texto, flags=re.IGNORECASE)]
    return SEPARADOR.join(categorias) or float("nan")


# Porcentaje de la matrícula: solo cuenta si la palabra "matrícula" aparece en los 60 caracteres siguientes,
# para no confundirlo con "100 % condonables", "1 % de mejores resultados" o "100 % de los intereses".
_CERCA_DE_MATRICULA = r"(?=[^.]{0,60}matr[ií]cula)"
_PATRONES_PORCENTAJE = [
    ("rango", r"(?:del|entre(?: el)?)\s*(\d{1,3})\s?%\s*(?:hasta el|y el|al)\s*(\d{1,3})\s?%" + _CERCA_DE_MATRICULA),
    ("hasta", r"hasta (?:el |un |en un )?(\d{1,3})\s?%" + _CERCA_DE_MATRICULA),
    ("exacto", r"(\d{1,3})\s?%" + _CERCA_DE_MATRICULA),
]


def extraer_porcentaje_matricula(texto):
    """% de la matrícula que cubre un apoyo, según su texto: (mínimo, máximo, forma).

    - 'rango': "del 25 % hasta el 95 %" o "entre el 12 % y el 20 %" → (25, 95).
    - 'hasta': "hasta el 90 %" → (NaN, 90): es un tope; el valor final depende de cada caso.
    - 'exacto': "Cubre 95 % del valor de la matrícula" → (95, 95).
    Si el texto no da un porcentaje de la matrícula ("un porcentaje", "hasta 2 SMLMV"), devuelve NaN.
    """
    for forma, patron in _PATRONES_PORCENTAJE:
        encontrado = re.search(patron, str(texto), flags=re.IGNORECASE)
        if encontrado:
            numeros = [float(n) for n in encontrado.groups()]
            minimo = float("nan") if forma == "hasta" else numeros[0]
            return minimo, numeros[-1], forma
    return float("nan"), float("nan"), float("nan")


# --------------------------------------------------------------------------------------
# Descarga y caché
# --------------------------------------------------------------------------------------
class Descargador:
    """Descarga URL de un sitio respetando su robots.txt y guarda cada respuesta en data/raw/<fuente>/.

    Lleva un manifiesto con una fila por archivo: tipo de página, URL, archivo y fecha de extracción.
    Los archivos se escriben primero en una carpeta temporal (<fuente>_descarga) y solo reemplazan
    a la caché anterior cuando la descarga termina (guardar_manifiesto): si algo falla a mitad de
    camino, la caché anterior queda intacta.
    """

    def __init__(self, fuente, url_base):
        self.destino = CARPETA_RAW / fuente
        self.carpeta = CARPETA_RAW / f"{fuente}_descarga"
        shutil.rmtree(self.carpeta, ignore_errors=True)  # restos de una descarga interrumpida
        self.carpeta.mkdir(parents=True)
        self.sesion = requests.Session()
        self.sesion.headers.update({"User-Agent": USER_AGENT})
        self.robots = RobotFileParser()
        self.robots.parse(self.sesion.get(urljoin(url_base, "/robots.txt"), timeout=30).text.splitlines())
        self.fecha = date.today().isoformat()
        self.manifiesto = []

    def obtener(self, url, tipo_pagina):
        """Descarga una URL permitida, la guarda y devuelve su contenido (texto para HTML, bytes para PDF)."""
        if not self.robots.can_fetch(USER_AGENT, url):
            print(f"  Omitida por robots.txt: {url}")
            return None
        time.sleep(PAUSA_SEGUNDOS)
        respuesta = self.sesion.get(url, timeout=60)
        es_pdf = url.lower().endswith(".pdf")
        # Los catálogos JSON de Uniandes no pasan por aquí (se guardan en descargar_uniandes).
        archivo = self.carpeta / (f"{len(self.manifiesto):04d}_{tipo_pagina}" + (".pdf" if es_pdf else ".html.gz"))
        if es_pdf:
            archivo.write_bytes(respuesta.content)
        else:
            with gzip.open(archivo, "wt", encoding="utf-8") as salida:
                salida.write(respuesta.text)
        self.manifiesto.append({"tipo_pagina": tipo_pagina, "url": url, "archivo": archivo.name,
                                "codigo_http": respuesta.status_code, "fecha_extraccion": self.fecha})
        return respuesta.content if es_pdf else respuesta.text

    def guardar_manifiesto(self):
        """Guarda el manifiesto y reemplaza la caché anterior de la fuente por la descarga nueva."""
        pd.DataFrame(self.manifiesto).to_csv(self.carpeta / "manifiesto.csv", index=False)
        shutil.rmtree(self.destino, ignore_errors=True)
        self.carpeta.rename(self.destino)
        print(f"  {len(self.manifiesto)} archivos guardados en {self.destino.as_posix()}")


def leer_manifiesto(fuente):
    """Lee el manifiesto de una fuente (qué archivo corresponde a qué URL y cuándo se bajó)."""
    return pd.read_csv(CARPETA_RAW / fuente / "manifiesto.csv")


def leer_html(fuente, archivo):
    """Devuelve el HTML guardado en data/raw/<fuente>/<archivo> (.html.gz)."""
    with gzip.open(CARPETA_RAW / fuente / archivo, "rt", encoding="utf-8") as entrada:
        return entrada.read()


# --------------------------------------------------------------------------------------
# Universidad de los Andes
# --------------------------------------------------------------------------------------
def extraer_fechas_uniandes(texto_raw):
    """Extrae fecha de apertura y cierre a partir del texto de la sección de fechas de Uniandes."""
    if not texto_raw:
        return float("nan"), float("nan")
    texto = " ".join(str(texto_raw).replace("\xa0", " ").replace("​", "").split())
    if any(p in texto.lower() for p in ["cerrada", "en definición", "fechas definidas", "enviará las fechas"]):
        return float("nan"), float("nan")

    # 1. 'Fecha de apertura: ... Fecha de cierre: ...'
    m_ap = re.search(r"Fecha de apertura:\s*(\d{1,2}\s+de\s+[a-záéíóú]+\s+de(?:l)?\s+\d{4})", texto, re.I)
    m_ci = re.search(r"Fecha de cierre:[^:]*?(\d{1,2}\s+de\s+[a-záéíóú]+\s+de(?:l)?\s+\d{4})", texto, re.I)
    if m_ap and m_ci:
        return m_ap.group(1), m_ci.group(1)

    # 2. 'desde el DD de Mes hasta el DD de Mes de(l) YYYY'
    m_rango = re.search(r"(?:desde\s+el\s+)?(\d{1,2})\s+de\s+([a-záéíóú]+)\s+hasta(?:\s+el)?\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de(?:l)?\s+(\d{4})", texto, re.I)
    if m_rango:
        d1, m1, d2, m2, y = m_rango.groups()
        return f"{d1} de {m1} de {y}", f"{d2} de {m2} de {y}"

    # 3. 'Del DD al DD de Mes de(l) YYYY'
    m_del = re.search(r"(?:del\s+)?(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de(?:l)?\s+(\d{4})", texto, re.I)
    if m_del:
        d1, d2, m, y = m_del.groups()
        return f"{d1} de {m} de {y}", f"{d2} de {m} de {y}"

    # 4. 'DD de Mes al DD de Mes de(l) YYYY'
    m_al = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+al\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de(?:l)?\s+(\d{4})", texto, re.I)
    if m_al:
        d1, m1, d2, m2, y = m_al.groups()
        return f"{d1} de {m1} de {y}", f"{d2} de {m2} de {y}"

    return float("nan"), float("nan")


def _guardar_catalogo_uniandes(descargador, tipo_pagina, ruta_api, clave):
    """Descarga un catálogo JSON del segmentador y lo guarda en la carpeta de la descarga.

    Si el servidor no lo entrega (por ejemplo, HTTP 500 "Error durante la autenticación"), se reutiliza
    el último catálogo bueno de la caché, con su fecha original, para no reemplazarlo por un error.
    Devuelve el JSON guardado."""
    time.sleep(PAUSA_SEGUNDOS)
    respuesta = descargador.sesion.get(f"{UNIANDES_API_BASE}/{ruta_api}", headers=UNIANDES_API_HEADERS, timeout=30)
    archivo = descargador.carpeta / f"{len(descargador.manifiesto):04d}_{tipo_pagina}.json"
    if respuesta.status_code == 200 and clave in respuesta.text:
        archivo.write_text(respuesta.text, encoding="utf-8")
        descargador.manifiesto.append({"tipo_pagina": tipo_pagina, "url": respuesta.url, "archivo": archivo.name,
                                       "codigo_http": respuesta.status_code, "fecha_extraccion": descargador.fecha})
        return json.loads(respuesta.text)

    anterior = pd.read_csv(descargador.destino / "manifiesto.csv") if (descargador.destino / "manifiesto.csv").exists() else None
    fila = None if anterior is None else anterior[(anterior["tipo_pagina"] == tipo_pagina) & (anterior["codigo_http"] == 200)]
    if fila is None or fila.empty:
        raise RuntimeError(f"Uniandes: el catálogo {ruta_api} respondió HTTP {respuesta.status_code} y no hay uno anterior.")
    fila = fila.iloc[0].to_dict()
    shutil.copy(descargador.destino / fila["archivo"], archivo)
    descargador.manifiesto.append({**fila, "archivo": archivo.name})
    print(f"  Catálogo {ruta_api} no disponible (HTTP {respuesta.status_code}); se reutiliza el del {fila['fecha_extraccion']}.")
    return leer_json_ruta(archivo)


def leer_json_ruta(ruta):
    """Devuelve el JSON guardado en una ruta."""
    with open(ruta, encoding="utf-8") as entrada:
        return json.load(entrada)


def descargar_uniandes():
    """Descarga los catálogos de apoyos y programas del segmentador de Uniandes y la ficha HTML de cada
    apoyo (respetando robots.txt y con pausas). Si un catálogo no está disponible, se reutiliza el último
    bueno y se vuelven a bajar las fichas que lista, que son páginas públicas."""
    print("Uniandes: descargando catálogo desde la API y fichas de apoyos...")
    descargador = Descargador("uniandes", UNIANDES_BASE)
    apoyos = _guardar_catalogo_uniandes(descargador, "api_supports", "supports", '"supports"')
    _guardar_catalogo_uniandes(descargador, "api_programs", "programs", '"programs"')

    urls_visitadas = set()
    for apoyo in apoyos.get("supports", []):
        url = apoyo.get("url")
        if url and url not in urls_visitadas:
            urls_visitadas.add(url)
            descargador.obtener(url, "ficha")
    descargador.guardar_manifiesto()


def leer_json(fuente, archivo):
    """Devuelve el JSON guardado en data/raw/<fuente>/<archivo>."""
    return leer_json_ruta(CARPETA_RAW / fuente / archivo)


def catalogo_programas_uniandes():
    """Programas de Uniandes con su facultad y nivel, tal como los publica el catálogo (api_programs)."""
    manifiesto = leer_manifiesto("uniandes")
    catalogo = leer_json("uniandes", manifiesto.loc[manifiesto["tipo_pagina"] == "api_programs", "archivo"].iloc[0])
    filas = [{"facultad": f["nombre_facultad"], "programa": p["nombre_programa"],
              "nivel": NIVEL_UNIANDES.get(p["nivel_academico"], p["nivel_academico"])}
             for f in catalogo["programs"] for p in f["programas"]]
    return pd.DataFrame(filas).drop_duplicates("programa")


def leer_uniandes():
    """Lee el catálogo de apoyos de Uniandes (guardado en raw) y complementa con las fechas
    de convocatoria extraídas del HTML de la ficha correspondiente.

    Nivel de formación, instrumento, facultades y programas vienen del catálogo; los códigos de
    facultad y de programa se traducen a nombres con el catálogo de programas (api_programs).
    Devuelve un DataFrame alineado con el esquema común."""
    manifiesto = leer_manifiesto("uniandes")
    fila_supports = manifiesto[manifiesto["tipo_pagina"] == "api_supports"]
    if fila_supports.empty:
        raise FileNotFoundError("No se encontró el archivo api_supports en data/raw/uniandes/manifiesto.csv")
    data = leer_json("uniandes", fila_supports.iloc[0]["archivo"])

    # Nombres de facultades y programas a partir de sus códigos.
    catalogo = leer_json("uniandes", manifiesto.loc[manifiesto["tipo_pagina"] == "api_programs", "archivo"].iloc[0])
    nombre_facultad = {f["cod_facultad"]: f["nombre_facultad"] for f in catalogo["programs"]}
    nombre_programa = {p["cod_programa"]: p["nombre_programa"] for f in catalogo["programs"] for p in f["programas"]}

    fichas_html = dict(zip(
        manifiesto.loc[manifiesto["tipo_pagina"] == "ficha", "url"],
        manifiesto.loc[manifiesto["tipo_pagina"] == "ficha", "archivo"]
    ))

    # Fecha de extracción de cada apoyo: la de su ficha (de ahí salen las fechas de la convocatoria);
    # si no tiene ficha, la del catálogo. Así el estado se calcula contra el día en que se leyó la ficha.
    fecha_ficha = dict(zip(manifiesto.loc[manifiesto["tipo_pagina"] == "ficha", "url"],
                           manifiesto.loc[manifiesto["tipo_pagina"] == "ficha", "fecha_extraccion"]))
    filas = []
    for apoyo in data.get("supports", []):
        url = apoyo.get("url", "")
        fecha_ext = fecha_ficha.get(url, fila_supports.iloc[0]["fecha_extraccion"])
        apertura, cierre = float("nan"), float("nan")
        archivo_html = fichas_html.get(url)

        if archivo_html and Path(CARPETA_RAW / "uniandes" / archivo_html).exists():
            soup = BeautifulSoup(leer_html("uniandes", archivo_html), "html.parser")
            secciones = {limpiar_texto(t.get_text(" ")).rstrip(":"): t for t in soup.select("main h3, main h4")}
            titulo_fechas = next((t for k, t in secciones.items() if k.lower().startswith("fechas de convocatoria")), None)
            bloque_fechas = titulo_fechas.find_next(class_="uk-panel") if titulo_fechas else None
            texto_fechas = bloque_fechas.get_text(" ").strip() if bloque_fechas else ""
            apertura, cierre = extraer_fechas_uniandes(texto_fechas)

        niveles = [NIVEL_UNIANDES.get(n, n) for n in apoyo.get("nivelAcadémico") or []]
        programas = sorted({nombre_programa.get(c, c) for c in apoyo.get("programas") or []})
        facultades = sorted(nombre_facultad.get(c, c) for c in apoyo.get("facultades") or [])
        tipo_apoyo = apoyo.get("tipoDeApoyo")
        porcentaje_min, porcentaje_max, forma_porcentaje = extraer_porcentaje_matricula(apoyo.get("cubre"))

        filas.append({
            "nombre": limpiar_texto(apoyo.get("nombreDelApoyo")),
            "entidad": "Universidad de los Andes",
            "nivel_formacion": SEPARADOR.join(niveles) or float("nan"),
            "instrumento": INSTRUMENTO_UNIANDES.get(tipo_apoyo, float("nan")),
            "area": SEPARADOR.join(facultades) or float("nan"),
            "programas": SEPARADOR.join(programas) or float("nan"),
            "cobertura": limpiar_texto(apoyo.get("cubre")),
            "requisitos": limpiar_texto(apoyo.get("dirigidoA")),
            "fecha_apertura": apertura,
            "fecha_cierre": cierre,
            "enlace": url,
            "fuente_url": "https://apoyofinanciero.uniandes.edu.co/explora-apoyos-financieros",
            "fecha_extraccion": fecha_ext,
            "porcentaje_min": porcentaje_min,
            "porcentaje_max": porcentaje_max,
            "forma_porcentaje": forma_porcentaje,
            "n_programas": len(programas),
            "instrumento_publicado": tipo_apoyo,
            "origen_clasificacion": "catálogo de la entidad",
            "requisitos_origen": "api",
        })

    print(f"Uniandes: {len(filas)} apoyos procesados desde el segmentador y fichas web")
    return pd.DataFrame(filas).reindex(columns=ESQUEMA + COLUMNAS_EXTRA)


# --------------------------------------------------------------------------------------
# Agencia Atenea
# --------------------------------------------------------------------------------------
def descargar_atenea():
    """Baja las páginas del listado de convocatorias, el detalle de cada una y, para las que
    no están finalizadas, los PDF de 'lineamiento operativo' (donde se publican los requisitos)."""
    print("Atenea: descargando...")
    descargador = Descargador("atenea", ATENEA_BASE)
    pagina, detalles = 0, {}
    while True:
        listado = BeautifulSoup(descargador.obtener(f"{ATENEA_BASE}/convocatorias?page={pagina}", "listado"),
                                "html.parser")
        tarjetas = [a for a in listado.find_all("a", href=True)
                    if a["href"].startswith("/convocatorias/") and a.find("h2")]
        if not tarjetas:
            break
        for tarjeta in tarjetas:
            pildora = tarjeta.find(class_=re.compile(r"^pill_"))
            detalles[urljoin(ATENEA_BASE, tarjeta["href"])] = pildora.get_text(strip=True) if pildora else ""
        pagina += 1

    for url, estado_publicado in detalles.items():
        html = descargador.obtener(url, "detalle")
        if estado_publicado == "Finalizada" or html is None:
            continue
        enlaces = {urljoin(url, a["href"]) for a in BeautifulSoup(html, "html.parser").find_all("a", href=True)}
        for pdf in sorted(e for e in enlaces if e.lower().endswith(".pdf") and "lineamiento" in e.lower()):
            descargador.obtener(pdf, "lineamiento")
    descargador.guardar_manifiesto()


def extraer_requisitos_pdf(ruta_pdf, max_caracteres=3000):
    """Busca en un PDF de lineamiento la sección 'Requisitos (mínimos) de participación' y devuelve su texto.

    Regla: el título es una línea corta que empieza (con o sin numeración, p. ej. '5.2.1.2.1.') por
    'Requisitos' o 'REQUISITOS' con mayúscula, menciona 'participación' y no sigue con una frase
    después de un punto (así se descartan definiciones de glosario y frases dentro de un párrafo).
    Tampoco puede ser del índice (no tiene '....'). La sección termina en el siguiente título
    numerado que no sea un subnumeral suyo, o a los max_caracteres.
    """
    with pdfplumber.open(ruta_pdf) as pdf:
        lineas = "\n".join(pagina.extract_text() or "" for pagina in pdf.pages).split("\n")
    patron_titulo = re.compile(r"^\s*((\d+\.)+\d*\.?)?\s*(Requisitos|REQUISITOS)\b[^.]{0,60}?participación[^.]*$")
    for i, linea in enumerate(lineas):
        if patron_titulo.match(linea) and "...." not in linea and len(linea) < 120:
            numero = (patron_titulo.match(linea).group(1) or "").rstrip(".")
            seccion = []
            for siguiente in lineas[i + 1:]:
                otro_numero = re.match(r"^\s*((\d+\.)+\d*)\.?\s+\S", siguiente)
                if otro_numero and not (numero and otro_numero.group(1).rstrip(".").startswith(numero)):
                    break
                seccion.append(siguiente)
            texto = limpiar_texto(" ".join(seccion))
            if isinstance(texto, str):  # si la sección quedó vacía, se sigue buscando otro título
                return texto[:max_caracteres]
    return float("nan")


def leer_atenea():
    """Lee el listado (estado publicado) y el detalle de cada convocatoria; una fila por convocatoria."""
    manifiesto = leer_manifiesto("atenea")
    archivo_de = dict(zip(manifiesto["url"], manifiesto["archivo"]))

    # Estado que muestra Atenea en cada tarjeta del listado.
    estado_publicado = {}
    for archivo in manifiesto.loc[manifiesto["tipo_pagina"] == "listado", "archivo"]:
        listado = BeautifulSoup(leer_html("atenea", archivo), "html.parser")
        for tarjeta in listado.find_all("a", href=True):
            pildora = tarjeta.find(class_=re.compile(r"^pill_"))
            if tarjeta["href"].startswith("/convocatorias/") and tarjeta.find("h2") and pildora:
                estado_publicado[urljoin(ATENEA_BASE, tarjeta["href"])] = pildora.get_text(strip=True)

    filas = []
    for _, detalle in manifiesto[manifiesto["tipo_pagina"] == "detalle"].iterrows():
        soup = BeautifulSoup(leer_html("atenea", detalle["archivo"]), "html.parser")
        # Nombre: campo de título de Drupal; si viene vacío, el <title> de la página antes de " | Atenea".
        nombre = limpiar_texto(soup.select_one(".field--name-node-title").get_text(" "))
        if not isinstance(nombre, str):
            nombre = limpiar_texto(soup.find("title").get_text().split("|")[0])

        # Descripción del beneficio: bloques de texto principal, sin el botón de SICORE ni el pie de
        # página institucional (que contiene el NIT). Se elige el primero que dice qué se cubre;
        # si ninguno lo dice, el primero de ellos (algunas páginas antiguas abren con avisos de resultados).
        cuerpos = [c for c in (limpiar_texto(b.get_text(" ")) for b in soup.select(".field--name-body"))
                   if isinstance(c, str) and len(c) > 60 and "NIT:" not in c]
        palabras_cobertura = r"cubre|financia|matrícula|subsidi|gratuit|beneficio|apoyo económico"
        cobertura = next((c for c in cuerpos if re.search(palabras_cobertura, c, flags=re.IGNORECASE)),
                         cuerpos[0] if cuerpos else float("nan"))
        # Respaldo: páginas que ponen la descripción dentro del acordeón ("Descripción", "Propósito", "Objetivos").
        if not isinstance(cobertura, str):
            for boton in soup.select("a.ckeditor-accordion-toggler"):
                if re.search(r"descripci|propósito|objetivo", boton.get_text(" "), flags=re.IGNORECASE):
                    cobertura = limpiar_texto(boton.find_parent("dt").find_next_sibling("dd").get_text(" "))
                    break

        # Fechas: el campo 'fechas de apertura y cierre' trae dos <time datetime> (apertura y cierre).
        campo_fechas = soup.select_one(".field--name-field-fechas-apertura-y-cierre")
        fechas = [t["datetime"] for t in campo_fechas.find_all("time", attrs={"datetime": True})] if campo_fechas else []

        # Requisitos: 1) sección del acordeón cuyo título habla de requisitos o a quién va dirigido;
        # 2) si no hay, la sección de requisitos del PDF de lineamiento descargado; 3) si no, NaN.
        requisitos, origen = float("nan"), float("nan")
        for boton in soup.select("a.ckeditor-accordion-toggler"):
            if re.search(r"requisito|dirigido a", boton.get_text(" "), flags=re.IGNORECASE):
                contenido = boton.find_parent("dt").find_next_sibling("dd")
                requisitos, origen = limpiar_texto(contenido.get_text(" ")), "html"
                break
        if origen != "html":
            pdfs = [urljoin(detalle["url"], a["href"]) for a in soup.find_all("a", href=True)
                    if "lineamiento" in a["href"].lower() and a["href"].lower().endswith(".pdf")]
            for pdf in pdfs:
                if pdf in archivo_de:
                    requisitos = extraer_requisitos_pdf(CARPETA_RAW / "atenea" / archivo_de[pdf])
                    if isinstance(requisitos, str):
                        origen = "pdf"
                        break

        # Nivel, instrumento y área (inferidos): reglas sobre el nombre y el inicio de la descripción.
        # "beca-crédito" (FEST) es un crédito, no una beca.
        texto_reglas = re.sub(r"beca-cr[eé]dito", "crédito", f"{nombre}. {str(cobertura)[:CARACTERES_REGLAS]}",
                              flags=re.IGNORECASE)
        porcentaje_min, porcentaje_max, forma_porcentaje = extraer_porcentaje_matricula(texto_reglas)

        filas.append({
            "nombre": nombre,
            "entidad": "Agencia Atenea",
            "nivel_formacion": clasificar_por_reglas(texto_reglas, NIVELES_ATENEA),
            "instrumento": clasificar_por_reglas(texto_reglas, INSTRUMENTOS_ATENEA),
            "area": clasificar_por_reglas(texto_reglas, AREAS_ATENEA),
            "cobertura": cobertura,
            "requisitos": requisitos,
            "fecha_apertura": fechas[0] if len(fechas) >= 1 else float("nan"),
            "fecha_cierre": fechas[1] if len(fechas) >= 2 else float("nan"),
            "enlace": detalle["url"],
            "fuente_url": ATENEA_BASE + "/convocatorias",
            "fecha_extraccion": detalle["fecha_extraccion"],
            "porcentaje_min": porcentaje_min,
            "porcentaje_max": porcentaje_max,
            "forma_porcentaje": forma_porcentaje,
            "origen_clasificacion": "reglas de texto (inferido)",
            "requisitos_origen": origen,
            "estado_publicado": estado_publicado.get(detalle["url"], float("nan")),
        })
    print(f"Atenea: {len(filas)} convocatorias")
    return pd.DataFrame(filas).reindex(columns=ESQUEMA + COLUMNAS_EXTRA)


# --------------------------------------------------------------------------------------
# Limpieza
# --------------------------------------------------------------------------------------
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "agostro": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

# Convocatorias que financian proyectos, empresas o prácticas laborales (no la educación de una persona).
# Se buscan en el nombre y la descripción; "prácticas laborales" solo en el nombre, porque algunos
# programas de formación las mencionan como un beneficio más (p. ej. Todos a la U).
PATRON_NO_ESTUDIANTES = (r"proyectos de investigación|banco[\w ]* de (propuestas|proyectos)|financiar proyectos"
                         r"|mipymes|grupos de investigación")
PATRON_NO_ESTUDIANTES_NOMBRE = r"prácticas laborales"


def limpiar_cadena(texto):
    """Quita espacios invisibles (ancho cero, no separables), espacios repetidos y espacios antes de signos."""
    if not isinstance(texto, str):
        return texto
    texto = texto.replace("​", "").replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"\s+([,;:])", r"\1", texto)
    return texto or float("nan")


def texto_a_fecha(texto):
    """Convierte una fecha publicada a datetime (hora de Bogotá, sin zona horaria).

    Acepta ISO ('2026-11-24T23:59:00-05:00' o '2026-06-15') y español ('26 de noviembre de 2026').
    Si no reconoce el formato devuelve NaT (no se inventa la fecha).
    """
    if not isinstance(texto, str):
        return pd.NaT
    if re.match(r"^\d{4}-\d{2}-\d{2}", texto):
        fecha = pd.Timestamp(texto)
        return fecha.tz_convert("America/Bogota").tz_localize(None) if fecha.tzinfo else fecha
    partes = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de(?:l)?\s+(\d{4})", texto.lower())
    if partes and partes.group(2) in MESES:
        return pd.Timestamp(int(partes.group(3)), MESES[partes.group(2)], int(partes.group(1)))
    return pd.NaT


def dirigido_a_personas(nombre, cobertura):
    """False si la convocatoria financia proyectos, empresas o prácticas (reglas PATRON_NO_ESTUDIANTES*)."""
    return not (re.search(PATRON_NO_ESTUDIANTES, f"{nombre} {cobertura}", flags=re.IGNORECASE)
                or re.search(PATRON_NO_ESTUDIANTES_NOMBRE, str(nombre), flags=re.IGNORECASE))


def calcular_estado(fila):
    """Estado de la convocatoria a la fecha de extracción y la regla que lo definió.

    1. Con fecha de cierre: 'próxima' si aún no abre; 'abierta' si cierra hoy o después; si no, 'cerrada'.
    2. Sin fecha de cierre, si la entidad publica un estado (Atenea), se usa ese estado.
    3. En otro caso, 'sin fecha'.
    """
    hoy = fila["fecha_extraccion"]
    if pd.notna(fila["fecha_cierre"]):
        if pd.notna(fila["fecha_apertura"]) and fila["fecha_apertura"].normalize() > hoy:
            return "próxima", "fechas publicadas"
        return ("abierta" if fila["fecha_cierre"].normalize() >= hoy else "cerrada"), "fechas publicadas"
    publicado = fila["estado_publicado"]
    if isinstance(publicado, str):
        if publicado == "Finalizada":
            return "cerrada", "estado publicado por la entidad"
        if publicado == "Inscripciones abiertas":
            return "abierta", "estado publicado por la entidad"
        if publicado.startswith("Apertura"):
            return "próxima", "estado publicado por la entidad"
    return "sin fecha", "sin fecha de cierre publicada"


# --------------------------------------------------------------------------------------
# Validación de enlaces
# --------------------------------------------------------------------------------------
def validar_enlaces(enlaces, actualizar, ruta_cache=Path("results/validacion_enlaces.csv")):
    """Código HTTP de cada enlace.

    Si actualizar es True, visita cada enlace (respetando robots.txt y con pausas) y guarda el
    resultado en ruta_cache. Si es False, lee el resultado guardado (así el tutorial corre sin internet)
    y solo visita los enlaces que aún no estén en él; un enlace sin validar nunca se da por no válido.
    """
    if actualizar:
        validacion = _visitar_enlaces(enlaces)
    else:
        guardada = pd.read_csv(ruta_cache)
        faltantes = [e for e in pd.unique(pd.Series(enlaces)) if e not in set(guardada["enlace"])]
        if not faltantes:
            return guardada
        print(f"Validando {len(faltantes)} enlaces que no están en {ruta_cache.as_posix()}...")
        validacion = pd.concat([guardada, _visitar_enlaces(faltantes)], ignore_index=True)
    validacion.to_csv(ruta_cache, index=False)
    return validacion


def _visitar_enlaces(enlaces):
    """Visita cada enlace (respetando robots.txt y con pausas) y devuelve su código HTTP."""
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": USER_AGENT})
    robots_por_sitio, filas = {}, []
    for enlace in enlaces:
        sitio = urljoin(enlace, "/")
        if sitio not in robots_por_sitio:
            robots_por_sitio[sitio] = RobotFileParser()
            robots_por_sitio[sitio].parse(sesion.get(sitio + "robots.txt", timeout=30).text.splitlines())
        codigo, error = float("nan"), float("nan")
        if robots_por_sitio[sitio].can_fetch(USER_AGENT, enlace):
            time.sleep(PAUSA_SEGUNDOS)
            try:
                with sesion.get(enlace, timeout=30, stream=True) as respuesta:  # stream: no baja el cuerpo
                    codigo = respuesta.status_code
            except requests.RequestException as excepcion:
                error = type(excepcion).__name__
        else:
            error = "bloqueado por robots.txt"
        filas.append({"enlace": enlace, "codigo_http": codigo, "error": error,
                      "fecha_validacion": date.today().isoformat()})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------------------
# Tabla final
# --------------------------------------------------------------------------------------
# Líneas de apoyo de Atenea (inferido): cada convocatoria es una edición de una línea que se repite.
# Se asignan por el nombre, en este orden (gana la primera regla que coincide). Las convocatorias de
# "Jóvenes a la E" sin subtítulo (primera, segunda y tercera) se asignan a la línea de instituciones
# privadas, porque la cuarta, la quinta y la sexta siguen esa numeración. La "línea de fortalecimiento
# ... en instituciones oficiales" es la línea de instituciones públicas.
LINEAS_ATENEA = {
    "Talento Capital": r"talento capital",
    "Todos a la U": r"todos a la u\b",
    "Jóvenes a la U": r"j[oó]venes a la u\b",
    "Jóvenes a la E: talentos excepcionales": r"talentos excepcionales",
    "Jóvenes a la E: formación para el trabajo": r"j[oó]venes a la e.*formaci[oó]n para el trabajo",
    "Jóvenes a la E: instituciones públicas": r"j[oó]venes a la e.*p[uú]blica|instituciones oficiales",
    "Jóvenes a la E: instituciones privadas": r"j[oó]venes a la e\b",
    "Fondo Técnica y Tecnológica": r"t[eé]cnica y tecnol[oó]gica",
    "Fondo Alianza Ciudad Educadora": r"alianza",
    "FEST (crédito con pago contingente)": r"\bfest\b",
    "Fondo para Víctimas del Conflicto": r"v[ií]ctimas",
}


def linea_atenea(nombre):
    """Línea de apoyo de una convocatoria de Atenea (inferido). Si ninguna regla coincide, es una
    convocatoria única y su línea es su propio nombre."""
    for linea, patron in LINEAS_ATENEA.items():
        if re.search(patron, nombre, flags=re.IGNORECASE):
            return linea
    return nombre


def unir_categorias(columna, orden=()):
    """Une las categorías de varios registros sin repetir, en el orden dado (NaN si ninguno tiene dato)."""
    valores = set(columna.dropna().str.split(SEPARADOR).explode())
    ordenados = [v for v in orden if v in valores] + sorted(valores - set(orden))
    return SEPARADOR.join(ordenados) if ordenados else float("nan")


def situacion_linea(entidad, ediciones):
    """Situación de una línea de apoyo en la fecha de la foto, según sus ediciones (inferido en Atenea).
    Una línea de Atenea sin convocatorias en los 12 meses anteriores a la foto se marca como posiblemente
    terminada; los apoyos de Uniandes son permanentes mientras sigan en el catálogo."""
    if ediciones["estado"].isin(["abierta", "próxima"]).any():
        return "abierta o próxima en la foto"
    if entidad == "Universidad de los Andes":
        return "en el catálogo, sin convocatoria abierta"
    ultima = ediciones["fecha_apertura"].max()
    if pd.isna(ultima):
        return "sin fecha publicada"
    if ultima >= ediciones["fecha_extraccion"].max() - pd.DateOffset(months=12):
        return "abrió en los últimos 12 meses"
    return f"sin convocatorias desde {ultima.year} (posiblemente terminada)"


def ficha_por_linea(base, orden_nivel=(), orden_instrumento=()):
    """Una fila por línea de apoyo: en Atenea reúne todas las ediciones (convocatorias) de la línea; en
    Uniandes cada apoyo del catálogo es su propia línea. El enlace es el de la edición más reciente."""
    es_uniandes = base["entidad"] == "Universidad de los Andes"
    base = base.assign(linea=base["nombre"].where(es_uniandes, base["nombre"].map(linea_atenea)),
                       # En Uniandes se agrupa por enlace: dos apoyos distintos pueden tener el mismo nombre.
                       clave=base["enlace"].where(es_uniandes, base["nombre"].map(linea_atenea)))
    filas = []
    for (entidad, _), ediciones in base.sort_values("fecha_apertura").groupby(["entidad", "clave"]):
        linea = ediciones["linea"].iloc[0]
        filas.append({
            "entidad": entidad,
            "linea": linea,
            "ediciones": len(ediciones),
            "nivel_formacion": unir_categorias(ediciones["nivel_formacion"], orden_nivel),
            "instrumento": unir_categorias(ediciones["instrumento"], orden_instrumento),
            "area": unir_categorias(ediciones["area"]),
            "porcentaje_max": ediciones["porcentaje_max"].max(),
            "primera_apertura": ediciones["fecha_apertura"].min(),
            "ultima_apertura": ediciones["fecha_apertura"].max(),
            "situacion": situacion_linea(entidad, ediciones),
            "enlace": ediciones["enlace"].iloc[-1],
        })
    return pd.DataFrame(filas)


COLUMNAS_FINALES = ESQUEMA +["estado", "criterio_estado", "enlace_valido", "codigo_http", "fecha_validacion",
                              "alertas", "dias_ventana"] + COLUMNAS_EXTRA


def alertas_de(fila):
    """Lista de problemas de calidad de un registro (NaN si no tiene ninguno)."""
    alertas = []
    if pd.isna(fila["requisitos"]):
        alertas.append("sin requisitos")
    if pd.isna(fila["fecha_cierre"]):
        alertas.append("sin fecha de cierre")
    if not fila["enlace_valido"]:
        alertas.append("enlace no válido")
    if fila["dias_ventana"] < 0:
        alertas.append("cierre antes de apertura")
    return "; ".join(alertas) or float("nan")
