"""Fase 1: reconocimiento de fuentes.

Revisa, para cada entidad, qué permite su robots.txt, si las convocatorias vienen
en el HTML estático, si hay PDF o API/JSON detrás y si algo exige iniciar sesión.
No extrae convocatorias todavía: solo reúne la evidencia para elegir la herramienta.

Entrada: páginas públicas de Uniandes, Agencia Atenea (y SICORE) y SENA Betowa (en línea).
Salida:  results/reconocimiento_fuentes.csv
Se corre desde la raíz del proyecto:  .venv\\Scripts\\python.exe scripts\\01_reconocimiento_fuentes.py
"""

# %% Paquetes
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

# %% Configuración general
# Identificamos el cliente con un nombre genérico y esperamos entre solicitudes.
USER_AGENT = "Mozilla/5.0 (compatible; TallerPythonUniandes/1.0; proyecto academico)"
PAUSA_SEGUNDOS = 2
FECHA_REVISION = date.today().isoformat()
SALIDA = Path("results/reconocimiento_fuentes.csv")

sesion = requests.Session()
sesion.headers.update({"User-Agent": USER_AGENT})


def descargar(url):
    """Descarga una URL con pausa previa y devuelve la respuesta de requests."""
    time.sleep(PAUSA_SEGUNDOS)
    return sesion.get(url, timeout=30)


def leer_robots(url_base):
    """Descarga el robots.txt del sitio. Devuelve el lector, si es un robots.txt real y las rutas 'Disallow'.

    Algunas aplicaciones responden 200 con su propia página HTML en cualquier ruta; por eso
    solo se acepta como robots.txt si el contenido trae reglas 'User-agent'.
    """
    respuesta = descargar(urljoin(url_base, "/robots.txt"))
    es_robots = respuesta.status_code == 200 and "user-agent" in respuesta.text.lower()
    robots = RobotFileParser()
    robots.parse(respuesta.text.splitlines() if es_robots else [])
    disallow = re.findall(r"^Disallow:\s*(\S+)", respuesta.text, flags=re.MULTILINE)
    return robots, es_robots, disallow


def permitido(robots, url):
    """True si el robots.txt deja a nuestro cliente leer la URL."""
    return robots.can_fetch(USER_AGENT, url)


def texto_visible(html):
    """Texto que ve una persona: quita scripts y estilos antes de leer el HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for etiqueta in soup(["script", "style", "noscript"]):
        etiqueta.decompose()
    return " ".join(soup.get_text(" ").split())


# %% 1. Universidad de los Andes: robots.txt y página "Explora apoyos financieros"
UNIANDES_BASE = "https://apoyofinanciero.uniandes.edu.co"
UNIANDES_EXPLORA = UNIANDES_BASE + "/explora-apoyos-financieros"

robots_uniandes, _, disallow_uniandes = leer_robots(UNIANDES_BASE)
print("Uniandes | Disallow:", disallow_uniandes)

# El buscador de "Explora" está dentro de un iframe; vemos a dónde apunta.
soup_explora = BeautifulSoup(descargar(UNIANDES_EXPLORA).text, "html.parser")
iframes_explora = [marco["src"] for marco in soup_explora.find_all("iframe", src=True)]
iframe_buscador = next((src for src in iframes_explora if "/apoyos/" in src), None)
print("Uniandes | iframe del buscador:", iframe_buscador,
      "| robots bloquea /apoyos/index.html:", "/apoyos/index.html" in disallow_uniandes)

# %% 2. Uniandes: el sitemap.xml lista una página propia por cada apoyo
urls_sitemap = re.findall(r"<loc>([^<]+)</loc>", descargar(UNIANDES_BASE + "/sitemap.xml").text)
print("Uniandes | URLs en sitemap.xml:", len(urls_sitemap))

# Tres fichas de muestra: ¿traen cobertura, fechas y documentos en el HTML?
FICHAS_MUESTRA = ["/beca-avanza", "/jovenes-a-la-u", "/descuento-por-hermanos"]
muestra_uniandes = []
for ruta in FICHAS_MUESTRA:
    url = UNIANDES_BASE + ruta
    html = descargar(url).text
    ficha = BeautifulSoup(html, "html.parser")
    titulos = [h.get_text(" ", strip=True) for h in ficha.find_all(["h1", "h2", "h3", "h4"])]
    texto = texto_visible(html)
    muestra_uniandes.append({
        "ruta": ruta,
        "permitido": permitido(robots_uniandes, url),
        "cobertura": "Cobertura" in titulos,
        "fecha_cierre": "Fecha de cierre" in texto,
        "pdf": sum(a["href"].lower().endswith(".pdf") for a in ficha.find_all("a", href=True)),
    })
muestra_uniandes = pd.DataFrame(muestra_uniandes)
print(muestra_uniandes.to_string(index=False))

# %% 3. Agencia Atenea: robots.txt y listado de convocatorias
ATENEA_BASE = "https://www.agenciaatenea.gov.co"
ATENEA_CONVOCATORIAS = ATENEA_BASE + "/convocatorias"

robots_atenea, _, disallow_atenea = leer_robots(ATENEA_BASE)
print("Atenea | Disallow:", disallow_atenea)

listado = BeautifulSoup(descargar(ATENEA_CONVOCATORIAS).text, "html.parser")
# Cada tarjeta es un enlace a /convocatorias/<nombre> con un título h2 y una "píldora" de estado.
tarjetas = [a for a in listado.find_all("a", href=True)
            if a["href"].startswith("/convocatorias/") and a.find("h2")]
estados_atenea = pd.Series([t.find(class_=re.compile(r"^pill_")).get_text(strip=True)
                            for t in tarjetas if t.find(class_=re.compile(r"^pill_"))]).value_counts()
paginas_atenea = max(int(n) for n in re.findall(r"\?page=(\d+)", str(listado))) + 1
print("Atenea | tarjetas en la página 1:", len(tarjetas), "| páginas del listado:", paginas_atenea)
print("Atenea | estados en la página 1:", estados_atenea.to_dict())

# %% 4. Atenea: detalle de cada convocatoria de la página 1 (fechas, requisitos, PDF, SICORE)
detalles_atenea = []
for tarjeta in tarjetas:
    url = urljoin(ATENEA_BASE, tarjeta["href"])
    html = descargar(url).text
    detalle = BeautifulSoup(html, "html.parser")
    enlaces = [urljoin(url, a["href"]) for a in detalle.find_all("a", href=True)]
    texto = texto_visible(html)
    detalles_atenea.append({
        "convocatoria": tarjeta["href"].removeprefix("/convocatorias/"),
        # Las fechas de apertura y cierre vienen en etiquetas <time datetime="..."> (formato ISO).
        "fechas_time": len(detalle.find_all("time", attrs={"datetime": True})),
        "requisitos_html": "equisito" in texto,
        "pdf": len({e for e in enlaces if e.lower().endswith(".pdf")}),
        "lineamiento_pdf": any("lineamiento" in e.lower() and e.lower().endswith(".pdf") for e in enlaces),
        "enlace_sicore": any("sicore" in e for e in enlaces),
        "menciona_contrasena": "contraseña" in texto,
        "pdfs": sorted({e for e in enlaces if e.lower().endswith(".pdf")}),
    })
detalles_atenea = pd.DataFrame(detalles_atenea)
print(detalles_atenea.drop(columns="pdfs").to_string(index=False))

# %% 5. Atenea: ¿los PDF se pueden descargar? (solo encabezados HTTP, sin bajar el archivo)
pdfs_atenea = sorted({pdf for lista in detalles_atenea["pdfs"] for pdf in lista})
pdf_prueba = next(pdf for pdf in pdfs_atenea if "lineamiento" in pdf.lower())
time.sleep(PAUSA_SEGUNDOS)
cabecera_pdf = sesion.head(pdf_prueba, timeout=30, allow_redirects=True)
print("Atenea | PDF distintos en la página 1:", len(pdfs_atenea))
print("Atenea | prueba:", pdf_prueba, "|", cabecera_pdf.status_code, cabecera_pdf.headers.get("Content-Type"),
      "| permitido:", permitido(robots_atenea, pdf_prueba))

# %% 6. SICORE: ¿se puede leer sin iniciar sesión?
SICORE = "https://sicore.agenciaatenea.gov.co/"
_, sicore_tiene_robots, disallow_sicore = leer_robots(SICORE)
html_sicore = descargar(SICORE).text
caracteres_sicore = len(texto_visible(html_sicore))
print("SICORE | ¿robots.txt real?:", sicore_tiene_robots, "| Disallow:", disallow_sicore,
      "| caracteres de texto visible sin JavaScript:", caracteres_sicore,
      "| convocatorias de Atenea que piden usuario y contraseña:", int(detalles_atenea["menciona_contrasena"].sum()))

# %% 7. SENA Betowa: robots.txt y página de ofertas (Next.js renderizado en el servidor)
BETOWA_BASE = "https://betowa.sena.edu.co"
BETOWA_OFERTA = BETOWA_BASE + "/oferta"

robots_betowa, _, disallow_betowa = leer_robots(BETOWA_BASE)
print("Betowa | Disallow:", disallow_betowa)

html_oferta = descargar(BETOWA_OFERTA).text
soup_oferta = BeautifulSoup(html_oferta, "html.parser")
texto_oferta = texto_visible(html_oferta)
total_betowa = re.search(r"Se encontraron (\d+) programas.*?página \d+ de (\d+)", texto_oferta)
enlaces_programas = [a["href"] for a in soup_oferta.find_all("a", href=True) if "programId=" in a["href"]]
print("Betowa | /oferta permitido:", permitido(robots_betowa, BETOWA_OFERTA),
      "| programas:", total_betowa.group(1), "| páginas:", total_betowa.group(2),
      "| programas en el HTML de la página 1:", len(enlaces_programas))
print("Betowa | ¿hay llamadas a /api/ en el HTML?:", bool(re.search(r"/api/[A-Za-z]", html_oferta)))

# La paginación es por URL (?page=2) y también llega armada desde el servidor.
html_pagina_2 = descargar(BETOWA_OFERTA + "?page=2").text
programas_pagina_2 = html_pagina_2.count("programId=")
print("Betowa | ?page=2 permitido:", permitido(robots_betowa, BETOWA_OFERTA + "?page=2"),
      "| enlaces a programas:", programas_pagina_2)

# %% 8. Betowa: página de detalle de un programa (requisitos, cursos, período académico)
url_detalle = urljoin(BETOWA_BASE, enlaces_programas[0])
texto_detalle = texto_visible(descargar(url_detalle).text)
periodo = re.search(r"Período académico\s*:\s*desde el (.+?) hasta el (.+?\d{4})", texto_detalle)
print("Betowa | detalle:", url_detalle, "| permitido:", permitido(robots_betowa, url_detalle))
print("Betowa | requisitos en HTML:", "Requisitos para inscribirte" in texto_detalle,
      "| 'Cursos disponibles':", "Cursos disponibles" in texto_detalle,
      "| período académico:", periodo.groups() if periodo else None,
      "| palabra 'cierre':", "cierre" in texto_detalle)

# %% 9. Tabla de reconocimiento
uniandes_con_cierre = int(muestra_uniandes["fecha_cierre"].sum())
tabla = pd.DataFrame([
    {
        "fuente": "Universidad de los Andes (Apoyo Financiero)",
        "url_convocatorias": UNIANDES_EXPLORA,
        "robots_txt": "Permite las fichas y el sitemap. Bloquea /apoyos/index.html (buscador del iframe), /api/ y carpetas internas de Joomla.",
        "contenido_en_html": f"Parcial. El buscador de 'Explora' es un iframe ({iframe_buscador}) que no se recorre por robots.txt. "
                             f"Cada apoyo tiene una ficha estática listada en sitemap.xml ({len(urls_sitemap)} URL, incluye páginas que no son apoyos). "
                             f"En la muestra, {int(muestra_uniandes['cobertura'].sum())} de {len(muestra_uniandes)} fichas traen 'Cobertura' y "
                             f"{uniandes_con_cierre} de {len(muestra_uniandes)} traen 'Fecha de cierre'.",
        "api_json": "No se usa: /api/ está bloqueado por robots.txt.",
        "pdf": "Sí, reglamentos en PDF; no hacen falta para el esquema (cobertura y fechas están en la ficha).",
        "requiere_login": "No",
        "herramienta": "requests + BeautifulSoup",
        "justificacion": "Las fichas son HTML estático; el sitemap da la lista de URL sin ejecutar JavaScript.",
    },
    {
        "fuente": "Agencia Atenea (portal de convocatorias)",
        "url_convocatorias": ATENEA_CONVOCATORIAS,
        "robots_txt": "Permite /convocatorias y /sites/default/files (PDF). Bloquea /admin/, /search/, /user/* y carpetas de Drupal.",
        "contenido_en_html": f"Sí. {paginas_atenea} páginas (?page=0 a {paginas_atenea - 1}), {len(tarjetas)} tarjetas en la primera, "
                             f"cada una con su estado. {int((detalles_atenea['fechas_time'] >= 2).sum())} de {len(detalles_atenea)} detalles traen "
                             f"fechas en <time datetime>; {int(detalles_atenea['requisitos_html'].sum())} traen requisitos en el HTML.",
        "api_json": "No se buscó: el HTML ya trae listado, estados, fechas y enlaces.",
        "pdf": f"Sí. {int((detalles_atenea['pdf'] > 0).sum())} de {len(detalles_atenea)} convocatorias enlazan PDF y "
               f"{int(detalles_atenea['lineamiento_pdf'].sum())} publican un 'lineamiento operativo' con los requisitos. "
               f"Descarga directa (HTTP {cabecera_pdf.status_code}, {cabecera_pdf.headers.get('Content-Type')}).",
        "requiere_login": "No para consultar; la inscripción se hace en SICORE.",
        "herramienta": "requests + BeautifulSoup; pdfplumber para los PDF",
        "justificacion": "El listado y los detalles son HTML estático; los requisitos que no están en el HTML se leen del lineamiento operativo en PDF.",
    },
    {
        "fuente": "Agencia Atenea (SICORE)",
        "url_convocatorias": SICORE,
        "robots_txt": (f"Disallow: {', '.join(disallow_sicore) or 'ninguno'}." if sicore_tiene_robots
                       else "No publica un robots.txt real (la ruta devuelve la página de la aplicación)."),
        "contenido_en_html": f"No. Sin JavaScript la página solo tiene {caracteres_sicore} caracteres de texto (aplicación que se arma en el navegador).",
        "api_json": "No revisada: está detrás del inicio de sesión.",
        "pdf": "No",
        "requiere_login": f"Sí. {int(detalles_atenea['menciona_contrasena'].sum())} convocatorias de Atenea indican ingresar con usuario y contraseña.",
        "herramienta": "Fuera del alcance",
        "justificacion": "Exige cuenta; raspar datos detrás de un inicio de sesión no es público. Se documenta como limitación.",
    },
    {
        "fuente": "SENA (Betowa)",
        "url_convocatorias": BETOWA_OFERTA,
        "robots_txt": "Permite / y /api/. Bloquea /_next/static/, imágenes, CSS y JS.",
        "contenido_en_html": f"Sí. El servidor arma la página (Next.js): {total_betowa.group(1)} programas en {total_betowa.group(2)} páginas "
                             f"de {len(enlaces_programas)} (?page=N). Cada programa tiene una página de detalle con requisitos y cursos "
                             f"(ciudad, centro y período académico).",
        "api_json": "No hay llamadas a /api/ en la página; los datos llegan dentro del HTML.",
        "pdf": "No",
        "requiere_login": "No para consultar; para inscribirse sí (inferido por los botones 'Ingresar' y 'Registrarme').",
        "herramienta": "requests + BeautifulSoup",
        "justificacion": "Aunque es un sitio con JavaScript, el HTML del servidor ya trae los programas y la paginación es por URL. "
                         "No publica fecha de cierre de inscripción: la vigencia se aproxima con el período académico (inferido).",
    },
])
tabla["fecha_revision"] = FECHA_REVISION
tabla["generado_por"] = "scripts/01_reconocimiento_fuentes.py (consulta en línea a las URL de la tabla)"

SALIDA.parent.mkdir(exist_ok=True)
tabla.to_csv(SALIDA, index=False, encoding="utf-8-sig")
print(f"Tabla guardada en {SALIDA} ({len(tabla)} filas)")
