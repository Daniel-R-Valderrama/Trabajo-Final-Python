"""Funciones auxiliares reutilizables del proyecto.

Hay dos tipos de funciones por fuente:
- descargar_<fuente>(): recorre el sitio (respetando robots.txt y con pausas) y guarda los
  insumos crudos en data/raw/<fuente>/ junto con un manifiesto (qué URL, qué archivo, qué fecha).
  Solo se usa cuando ACTUALIZAR_DATOS = True.
- leer_<fuente>(): lee esos archivos crudos (sin internet) y devuelve un DataFrame con el esquema común.

Al final están las funciones de limpieza (texto y fechas), de estado de las convocatorias y de
validación de enlaces que usa la Fase 3.

Las páginas HTML se guardan comprimidas (.html.gz) para que el .zip del tutorial no pese demasiado.
Todas las rutas son relativas a la raíz del proyecto.
"""

import gzip
import re
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
ATENEA_BASE = "https://www.agenciaatenea.gov.co"
BETOWA_BASE = "https://betowa.sena.edu.co"
# Código de ubicación de Bogotá en el filtro de Betowa (visto en la URL al filtrar por "Bogotá").
BETOWA_BOGOTA = "57011001"

ESQUEMA = ["nombre", "entidad", "tipo", "cobertura", "requisitos", "fecha_apertura",
           "fecha_cierre", "enlace", "fuente_url", "fecha_extraccion"]
# Columnas adicionales que ayudan a validar en la Fase 3:
# - requisitos_origen: de dónde salió el texto de requisitos (html, pdf o NaN).
# - estado_publicado: estado que la propia entidad muestra (solo Atenea lo publica).
# - periodos_cursos: períodos académicos de los cursos (solo Betowa; no publica fecha de cierre).
COLUMNAS_EXTRA = ["requisitos_origen", "estado_publicado", "periodos_cursos"]


def limpiar_texto(texto):
    """Une espacios y saltos de línea repetidos; devuelve NaN si el texto queda vacío."""
    texto = " ".join(str(texto).split()) if texto is not None else ""
    return texto or float("nan")


def texto_de_seccion(titulo, siguiente_clase="uk-panel"):
    """Texto del primer bloque con la clase indicada que sigue a un título (estructura de Joomla/YOOtheme)."""
    bloque = titulo.find_next(class_=siguiente_clase)
    return limpiar_texto(bloque.get_text(" ")) if bloque else float("nan")


def clasificar_tipo(texto):
    """Clasifica un apoyo con una regla explícita sobre su nombre y descripción:
    'formación gratuita' si lo dice el texto; 'beca' si menciona beca; si no, 'apoyo financiero'."""
    texto = str(texto).lower()
    if "formación gratuita" in texto:
        return "formación gratuita"
    if "beca" in texto:
        return "beca"
    return "apoyo financiero"


# --------------------------------------------------------------------------------------
# Descarga y caché
# --------------------------------------------------------------------------------------
class Descargador:
    """Descarga URL de un sitio respetando su robots.txt y guarda cada respuesta en data/raw/<fuente>/.

    Lleva un manifiesto con una fila por archivo: tipo de página, URL, archivo y fecha de extracción.
    """

    def __init__(self, fuente, url_base):
        self.carpeta = CARPETA_RAW / fuente
        self.carpeta.mkdir(parents=True, exist_ok=True)
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
        """Borra archivos de una descarga anterior que ya no están en el manifiesto y guarda el nuevo."""
        vigentes = {fila["archivo"] for fila in self.manifiesto} | {"manifiesto.csv"}
        for archivo in self.carpeta.iterdir():
            if archivo.name not in vigentes:
                archivo.unlink()
        pd.DataFrame(self.manifiesto).to_csv(self.carpeta / "manifiesto.csv", index=False)
        print(f"  {len(self.manifiesto)} archivos guardados en {self.carpeta}")


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
def descargar_uniandes():
    """Baja el sitemap.xml y todas las páginas que lista (cada apoyo tiene su ficha)."""
    print("Uniandes: descargando...")
    descargador = Descargador("uniandes", UNIANDES_BASE)
    sitemap = descargador.obtener(UNIANDES_BASE + "/sitemap.xml", "sitemap")
    for url in re.findall(r"<loc>([^<]+)</loc>", sitemap):
        descargador.obtener(url, "ficha")
    descargador.guardar_manifiesto()


def leer_uniandes():
    """Lee las fichas guardadas. Una fila por ficha que publica una sección de cobertura
    ("Cobertura" o "Cubre"); las demás páginas del sitemap (menús, contacto, comités) se descartan."""
    manifiesto = leer_manifiesto("uniandes")
    fichas = manifiesto[(manifiesto["tipo_pagina"] == "ficha") & (manifiesto["codigo_http"] == 200)]
    filas, descartadas = [], []
    for _, ficha in fichas.iterrows():
        soup = BeautifulSoup(leer_html("uniandes", ficha["archivo"]), "html.parser")
        # Cada sección es un título (h3 o h4) seguido de un bloque de texto.
        secciones = {limpiar_texto(t.get_text(" ")).rstrip(":"): t for t in soup.select("main h3, main h4")}
        titulo_cobertura = secciones.get("Cobertura") or secciones.get("Cubre")
        if titulo_cobertura is None:
            descartadas.append(ficha["url"])
            continue
        titulo_requisitos = secciones.get("Programas a los que aplica") or secciones.get("Dirigido a")
        titulo_fechas = next((t for nombre, t in secciones.items() if nombre.startswith("Fechas de convocatoria")), None)
        texto_fechas = texto_de_seccion(titulo_fechas) if titulo_fechas else ""
        apertura = re.search(r"Fecha de apertura:\s*(.+?\d{4})", str(texto_fechas))
        cierre = re.search(r"Fecha de cierre:\s*(.+?\d{4})", str(texto_fechas))
        nombre = limpiar_texto(soup.find("title").get_text())
        filas.append({
            "nombre": nombre,
            "entidad": "Universidad de los Andes",
            "tipo": clasificar_tipo(f"{nombre} {ficha['url']}"),  # la URL dice 'beca-' aunque el título no
            "cobertura": texto_de_seccion(titulo_cobertura),
            "requisitos": texto_de_seccion(titulo_requisitos) if titulo_requisitos else float("nan"),
            "fecha_apertura": apertura.group(1) if apertura else float("nan"),
            "fecha_cierre": cierre.group(1) if cierre else float("nan"),
            "enlace": ficha["url"],
            "fuente_url": UNIANDES_BASE + "/sitemap.xml",
            "fecha_extraccion": ficha["fecha_extraccion"],
            "requisitos_origen": "html" if titulo_requisitos else float("nan"),
        })
    print(f"Uniandes: {len(filas)} apoyos; {len(descartadas)} páginas sin sección de cobertura descartadas")
    return pd.DataFrame(filas).reindex(columns=ESQUEMA + COLUMNAS_EXTRA), descartadas


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

        filas.append({
            "nombre": nombre,
            "entidad": "Agencia Atenea",
            "tipo": clasificar_tipo(f"{nombre} {cobertura}"),
            "cobertura": cobertura,
            "requisitos": requisitos,
            "fecha_apertura": fechas[0] if len(fechas) >= 1 else float("nan"),
            "fecha_cierre": fechas[1] if len(fechas) >= 2 else float("nan"),
            "enlace": detalle["url"],
            "fuente_url": ATENEA_BASE + "/convocatorias",
            "fecha_extraccion": detalle["fecha_extraccion"],
            "requisitos_origen": origen,
            "estado_publicado": estado_publicado.get(detalle["url"], float("nan")),
        })
    print(f"Atenea: {len(filas)} convocatorias")
    return pd.DataFrame(filas).reindex(columns=ESQUEMA + COLUMNAS_EXTRA)


# --------------------------------------------------------------------------------------
# SENA Betowa
# --------------------------------------------------------------------------------------
def url_listado_betowa(pagina):
    """URL del listado de Betowa filtrado a Bogotá, con 100 programas por página."""
    return f"{BETOWA_BASE}/oferta?location={BETOWA_BOGOTA}&page_size=100&page={pagina}"


def descargar_betowa():
    """Baja las páginas del listado filtrado a Bogotá y el detalle de cada programa."""
    print("Betowa: descargando...")
    descargador = Descargador("betowa", BETOWA_BASE)
    primera = descargador.obtener(url_listado_betowa(1), "listado")
    total_paginas = int(re.search(r"página \d+ de (\d+)", primera).group(1))
    listados = [primera] + [descargador.obtener(url_listado_betowa(p), "listado")
                            for p in range(2, total_paginas + 1)]

    programas = []
    for html in listados:
        for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            url = urljoin(BETOWA_BASE, a["href"])
            if "programId=" in url and url not in programas:
                programas.append(url)
    print(f"  {len(programas)} programas en {total_paginas} páginas del listado")
    for url in programas:
        descargador.obtener(url, "detalle")
    descargador.guardar_manifiesto()


def leer_betowa():
    """Lee el detalle de cada programa ofrecido en Bogotá; una fila por programa y modalidad.

    Betowa no publica fecha de apertura ni de cierre de inscripciones: esas columnas quedan en NaN
    y se guardan aparte los períodos académicos de los cursos (cuando el curso los publica).
    """
    manifiesto = leer_manifiesto("betowa")
    filas = []
    for _, detalle in manifiesto[manifiesto["tipo_pagina"] == "detalle"].iterrows():
        soup = BeautifulSoup(leer_html("betowa", detalle["archivo"]), "html.parser")
        for etiqueta in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            etiqueta.decompose()
        texto = limpiar_texto(soup.body.get_text(" "))
        # Datos de la ficha: van entre etiquetas fijas ("Tipo de programa ... Duración ...").
        tipo_programa = re.search(r"Tipo de programa (.+?) Duración", texto)
        duracion = re.search(r"Duración (.+?) Nivel de formación", texto)
        nivel = re.search(r"Nivel de formación (.+?) (\d+) \+ Edad mínima", texto)
        bloque_requisitos = re.search(r"Requisitos para inscribirte en este programa (.+?) Proceso de admisión", texto)
        requisitos = bloque_requisitos.group(1) if bloque_requisitos else ""
        requisitos = re.sub(r"^Antes de comenzar, asegúrate de cumplir con los siguientes requisitos\..*?programa:\s*",
                            "", requisitos)
        if nivel:
            requisitos = f"Edad mínima: {nivel.group(2)} años. {requisitos}"
        periodos = re.findall(r"Período académico\s*:\s*desde el (.+?\d{4}) hasta el (.+?\d{4})", texto)

        filas.append({
            "nombre": limpiar_texto(soup.find("h1").get_text(" ")),
            "entidad": "SENA",
            "tipo": "formación gratuita",
            "cobertura": limpiar_texto(
                "Formación gratuita del SENA. "
                + ", ".join(m.group(1) for m in [tipo_programa, nivel, duracion] if m)),
            "requisitos": limpiar_texto(requisitos),
            "fecha_apertura": float("nan"),
            "fecha_cierre": float("nan"),
            "enlace": detalle["url"],
            "fuente_url": url_listado_betowa(1),
            "fecha_extraccion": detalle["fecha_extraccion"],
            "requisitos_origen": "html" if bloque_requisitos else float("nan"),
            "periodos_cursos": "; ".join(f"desde {a} hasta {b}" for a, b in periodos) or float("nan"),
        })
    print(f"Betowa: {len(filas)} programas en Bogotá")
    return pd.DataFrame(filas).reindex(columns=ESQUEMA + COLUMNAS_EXTRA)


# --------------------------------------------------------------------------------------
# Limpieza
# --------------------------------------------------------------------------------------
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

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
    partes = re.search(r"(\d{1,2}) de ([a-záéíóú]+) de (\d{4})", texto.lower())
    if partes and partes.group(2) in MESES:
        return pd.Timestamp(int(partes.group(3)), MESES[partes.group(2)], int(partes.group(1)))
    return pd.NaT


def fin_ultimo_periodo(periodos):
    """Última fecha 'hasta el ...' de los períodos académicos de un programa del SENA (o NaT)."""
    if not isinstance(periodos, str):
        return pd.NaT
    return max(texto_a_fecha(fin) for fin in re.findall(r"hasta (.+?\d{4})", periodos))


def dirigido_a_personas(nombre, cobertura):
    """False si la convocatoria financia proyectos, empresas o prácticas (reglas PATRON_NO_ESTUDIANTES*)."""
    return not (re.search(PATRON_NO_ESTUDIANTES, f"{nombre} {cobertura}", flags=re.IGNORECASE)
                or re.search(PATRON_NO_ESTUDIANTES_NOMBRE, str(nombre), flags=re.IGNORECASE))


def calcular_estado(fila):
    """Estado de la convocatoria a la fecha de extracción y la regla que lo definió.

    1. Con fecha de cierre: 'próxima' si aún no abre; 'abierta' si cierra hoy o después; si no, 'cerrada'.
    2. Sin fecha de cierre, si la entidad publica un estado (Atenea), se usa ese estado.
    3. SENA: si el período académico de todos sus cursos ya terminó, 'cerrada' (inferido).
    4. En otro caso, 'sin fecha'.
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
    if pd.notna(fila["fin_periodo"]) and fila["fin_periodo"] < hoy:
        return "cerrada", "período académico terminado (inferido)"
    return "sin fecha", "sin fecha de cierre publicada"


# --------------------------------------------------------------------------------------
# Validación de enlaces
# --------------------------------------------------------------------------------------
def validar_enlaces(enlaces, actualizar, ruta_cache=Path("results/validacion_enlaces.csv")):
    """Código HTTP de cada enlace.

    Si actualizar es True, visita cada enlace (respetando robots.txt y con pausas) y guarda el
    resultado en ruta_cache. Si es False, lee el resultado guardado (así el tutorial corre sin internet).
    """
    if not actualizar:
        return pd.read_csv(ruta_cache)
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
    validacion = pd.DataFrame(filas)
    validacion.to_csv(ruta_cache, index=False)
    return validacion
