"""App de Streamlit: guía de becas y apoyos educativos de la Agencia Atenea, la Universidad de los Andes y la
Pontificia Universidad Javeriana.

Muestra exactamente lo que produce el tutorial (results/); no raspa nada:
- results/becas_apoyos.csv: becas y apoyos (sección 4). Las convocatorias vencidas ("cerrada") no se muestran.
- results/hallazgos.csv: hallazgos principales del tutorial (sección 9), para la portada.
- results/tabla_lineas_apoyo.csv: líneas de apoyo de Atenea que se repiten (sección 8, inferido).
Para ver datos más recientes: en tutorial.ipynb poner ACTUALIZAR_DATOS = True, dar Run All y volver a
cargar la app. Se corre desde la raíz del proyecto:  .venv\\Scripts\\streamlit.exe run app.py
"""

import html
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import scrapers

RUTA_DATOS = Path("results/becas_apoyos.csv")  # tabla final del tutorial (sección 4)
RUTA_HALLAZGOS = Path("results/hallazgos.csv")  # hallazgos del tutorial (sección 9)
RUTA_LINEAS = Path("results/tabla_lineas_apoyo.csv")  # ficha por línea de apoyo (sección 8)
SIN_DATO = "Sin dato publicado"
POR_PAGINA = 12
ORDEN_NIVEL = ["Formación para el trabajo y cursos cortos", "Técnico y tecnológico", "Pregrado universitario",
               "Especialización", "Maestría", "Doctorado"]
NIVEL_CORTO = {"Formación para el trabajo y cursos cortos": "Curso para el trabajo",
               "Técnico y tecnológico": "Técnico o tecnólogo", "Pregrado universitario": "Universidad (pregrado)",
               "Especialización": "Especialización", "Maestría": "Maestría", "Doctorado": "Doctorado"}
NOMBRE_CORTO = {"Agencia Atenea": "Atenea", "Universidad de los Andes": "Uniandes",
                "Pontificia Universidad Javeriana": "Javeriana"}
CLASE_ENTIDAD = {"Agencia Atenea": "atenea", "Universidad de los Andes": "uniandes",
                 "Pontificia Universidad Javeriana": "javeriana"}
# Qué significa cada instrumento, en palabras de un estudiante.
EN_PALABRAS = {"Beca o subsidio de matrícula": "Beca: paga parte de la matrícula y no se devuelve",
               "Descuento": "Descuento en la matrícula",
               "Crédito": "Crédito: se devuelve después",
               "Crédito condonable": "Crédito condonable: se perdona si cumples las condiciones",
               "Crédito con pago contingente": "Crédito que pagas según tus ingresos al graduarte",
               "Apoyo de sostenimiento": "Dinero para tus gastos mientras estudias",
               "Formación sin costo": "Curso gratuito"}
TODOS = "Todos"
ORDENES = ["Cierran primero", "Cubren más de la matrícula", "Tipo de ayuda"]

st.set_page_config(page_title="Becas y apoyos educativos · Bogotá", page_icon="🎓", layout="centered")

# --- Estilo: barra superior, tarjetas blancas, cifras grandes y notas con borde morado ---
st.markdown("""
<style>
#MainMenu, header[data-testid="stHeader"], footer {visibility: hidden;}
.block-container {padding-top: 4.5rem; max-width: 860px;}
.barra {position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: #5046E5; color: white;
        padding: 0.75rem 1.5rem; font-weight: 600; font-size: 0.95rem;}
.portada {background: #E9E7FB; border-radius: 18px; padding: 1.8rem 1.5rem 1.3rem; text-align: center;
          margin-bottom: 1rem;}
.portada h1 {font-size: 2rem; margin: 0 0 0.4rem; color: #1F2133;}
.portada p {color: #555770; margin: 0.2rem 0;}
div[data-testid="stVerticalBlockBorderWrapper"] {background: white; border-radius: 16px !important;
        border: 1px solid #E4E3F0 !important; box-shadow: 0 1px 3px rgba(31, 33, 51, 0.06);}
.paso {display: inline-flex; width: 1.6rem; height: 1.6rem; border-radius: 50%; background: #5046E5;
       color: white; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 600;}
.titulo-tarjeta {font-size: 1.3rem; font-weight: 700; margin: 0.5rem 0 0.1rem; color: #1F2133;}
.fuente {color: #7A7C93; font-size: 0.78rem; margin-bottom: 0.6rem;}
.hallazgo {border-left: 4px solid #5046E5; background: #F4F3FC; padding: 0.6rem 0.9rem;
           border-radius: 0 10px 10px 0; margin: 0.45rem 0; color: #1F2133; font-size: 0.92rem;}
.hallazgo b {display: block; margin-bottom: 0.1rem;}
.nota-morada {border-left: 4px solid #5046E5; background: #F4F3FC; padding: 0.7rem 1rem;
              border-radius: 0 10px 10px 0; margin: 0.6rem 0 0.3rem; color: #1F2133; font-size: 0.9rem;}
.chip {display: inline-block; border-radius: 999px; padding: 0.1rem 0.6rem; margin: 0 0.25rem 0.25rem 0;
       font-size: 0.78rem; background: #F0EFF8; color: #3B3D55;}
.chip.uniandes {background: #E1EEFA; color: #0B5394;}
.chip.atenea {background: #FFF0D9; color: #8A5A00;}
.chip.javeriana {background: #DDF3EA; color: #0B6B4C;}
.chip.abierta {background: #E3F4E8; color: #1E7A3C;}
.chip.proxima {background: #E9E7FB; color: #3F36C9;}
.encabezado-apoyo {display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start;}
.nombre {font-weight: 600; font-size: 1.05rem; color: #1F2133; margin-bottom: 0.3rem;}
.cubre {text-align: right; min-width: 105px;}
.cubre .valor {font-size: 1.6rem; font-weight: 700; color: #3F36C9; line-height: 1.1;}
.cubre .nota {font-size: 0.72rem; color: #7A7C93;}
.dato {color: #3B3D55; font-size: 0.9rem; margin: 0.35rem 0;}
.dato b {color: #1F2133;}
.aviso {background: #FFF6E5; color: #7A5200; border-radius: 8px; padding: 0.35rem 0.7rem; font-size: 0.82rem;
        margin: 0.4rem 0;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar_tabla(ruta, modificado):
    """Lee una tabla del tutorial (modificado = fecha del archivo, para volver a leerla si el tutorial la cambia)."""
    tabla = pd.read_csv(ruta)
    for columna in ["fecha_apertura", "fecha_cierre", "fecha_extraccion", "ultima_apertura"]:
        if columna in tabla.columns:
            tabla[columna] = pd.to_datetime(tabla[columna])
    return tabla


def sin_tildes(texto):
    """Minúsculas y sin tildes, para que 'matricula' encuentre 'matrícula'."""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")


def categorias(columna):
    """Lista de categorías de una columna con varios valores por registro (sin 'Sin dato publicado')."""
    return sorted(set(columna.dropna().str.split(scrapers.SEPARADOR).explode()))


def tiene_alguna(columna, elegidas):
    """True en los registros que tienen al menos una de las categorías elegidas."""
    return columna.fillna(SIN_DATO).str.split(scrapers.SEPARADOR).map(lambda valores: bool(set(valores) & set(elegidas)))


def texto_porcentaje(fila):
    """Porcentaje de la matrícula como se publica: '95 %', 'hasta 90 %' o '25 a 95 %' (vacío si no lo publica)."""
    if pd.isna(fila["porcentaje_max"]):
        return ""
    if fila["forma_porcentaje"] == "hasta":
        return f"hasta {fila['porcentaje_max']:.0f} %"
    if fila["forma_porcentaje"] == "rango":
        return f"{fila['porcentaje_min']:.0f} a {fila['porcentaje_max']:.0f} %"
    return f"{fila['porcentaje_max']:.0f} %"


def fecha_corta(fecha):
    """Fecha como DD/MM/AAAA, o un aviso si la entidad no la publica."""
    return fecha.strftime("%d/%m/%Y") if pd.notna(fecha) else "sin fecha publicada"


def encabezado_tarjeta(numero, titulo, fuente):
    """Número en círculo, título en forma de pregunta y línea de fuente."""
    st.markdown(f'<span class="paso">{numero}</span><div class="titulo-tarjeta">{titulo}</div>'
                f'<div class="fuente">{fuente}</div>', unsafe_allow_html=True)


def texto_o_vacio(valor):
    """Texto escapado para HTML, o 'Sin dato publicado'."""
    return html.escape(str(valor)) if pd.notna(valor) and str(valor).strip() else SIN_DATO


def recortar(texto, largo):
    """Recorta un texto largo en la última palabra completa y agrega '…' (el texto completo está en el desplegable)."""
    return texto if len(texto) <= largo else texto[:largo].rsplit(" ", 1)[0] + "…"


def mostrar_apoyo(fila):
    """Tarjeta de un apoyo: a quién va dirigido, qué cubre, fechas, descripción completa y enlace oficial."""
    with st.container(border=True):
        entidad = fila["entidad"]
        clase_estado = {"abierta": "abierta", "próxima": "proxima"}.get(fila["estado"], "")
        chips = (f'<span class="chip {CLASE_ENTIDAD[entidad]}">{NOMBRE_CORTO[entidad]}</span>'
                 f'<span class="chip {clase_estado}">{fila["estado"]}</span>')
        if pd.notna(fila["tipo_estudiante"]):
            chips += f'<span class="chip">{html.escape(fila["tipo_estudiante"])}</span>'
        cubre = (f'<div class="valor">{fila["porcentaje"]}</div><div class="nota">de la matrícula</div>'
                 if fila["porcentaje"] else '<div class="nota">no publica<br>porcentaje</div>')
        instrumentos = [EN_PALABRAS.get(i, i) for i in str(fila["instrumento"]).split(scrapers.SEPARADOR) if i != "nan"]
        niveles = ", ".join(NIVEL_CORTO.get(n, n) for n in str(fila["nivel_formacion"]).split(scrapers.SEPARADOR)
                            if n != "nan") or SIN_DATO
        area = ("Cualquier programa" if fila["area_conocimiento"] == scrapers.CUALQUIER_AREA
                else texto_o_vacio(fila["area_conocimiento"]).replace(scrapers.SEPARADOR, ", "))
        st.markdown(f"""
<div class="encabezado-apoyo"><div><div class="nombre">{html.escape(fila["nombre"])}</div>{chips}</div>
<div class="cubre">{cubre}</div></div>
<div class="dato"><b>Qué te da:</b> {html.escape("; ".join(instrumentos)) or SIN_DATO}</div>
<div class="dato"><b>Para quién:</b> {recortar(texto_o_vacio(fila["requisitos"]), 320)}</div>
<div class="dato"><b>Nivel:</b> {html.escape(niveles)} · <b>Área:</b> {area}</div>
<div class="dato"><b>Fechas:</b> abre {fecha_corta(fila["fecha_apertura"])} · cierra <b>{fecha_corta(fila["fecha_cierre"])}</b></div>
""", unsafe_allow_html=True)
        if entidad == "Agencia Atenea":
            st.markdown('<div class="aviso">Atenea financia estudios solo en sus instituciones aliadas: revisa la lista '
                        'en la convocatoria. Nivel, ayuda y área se deducen del texto (inferido).</div>',
                        unsafe_allow_html=True)
        columna_texto, columna_boton = st.columns([3, 1], vertical_alignment="center")
        with columna_texto.expander("Ver la descripción completa"):
            st.markdown(f"**Qué cubre:** {texto_o_vacio(fila['cobertura'])}")
            st.markdown(texto_o_vacio(fila["descripcion"]))
            if pd.notna(fila["programas"]):
                st.markdown(f"**Programas ({int(fila['n_programas'])}):** {fila['programas']}")
        columna_boton.link_button("Ver oficial →", fila["enlace"], width="stretch")


# --- Datos ---
datos = cargar_tabla(RUTA_DATOS, RUTA_DATOS.stat().st_mtime)
hallazgos = cargar_tabla(RUTA_HALLAZGOS, RUTA_HALLAZGOS.stat().st_mtime)
lineas = cargar_tabla(RUTA_LINEAS, RUTA_LINEAS.stat().st_mtime)
becas_apoyos = datos[datos["estado"] != "cerrada"].reset_index(drop=True)
becas_apoyos["porcentaje"] = becas_apoyos.apply(texto_porcentaje, axis=1)
fechas = datos.groupby("entidad")["fecha_extraccion"].max().dt.strftime("%d/%m/%Y")
texto_fechas = ", ".join(f"{fecha} ({NOMBRE_CORTO[entidad]})" for entidad, fecha in fechas.items())

# --- Barra superior y portada con los hallazgos del tutorial ---
st.markdown('<div class="barra">Becas y apoyos educativos · Bogotá</div>', unsafe_allow_html=True)
st.markdown("""
<div class="portada">
  <h1>¿Dónde busco apoyo para estudiar?</h1>
  <p>Becas, créditos y apoyos de una entidad pública (Agencia Atenea) y dos universidades privadas
  (Universidad de los Andes y Pontificia Universidad Javeriana).</p>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    encabezado_tarjeta(1, "Lo que debes saber antes de buscar",
                       f"Hallazgos del tutorial (sección 9) · datos extraídos el {texto_fechas}")
    st.markdown("".join(f'<div class="hallazgo"><b>{html.escape(h["titulo"])}</b>{html.escape(h["texto"])}</div>'
                        for _, h in hallazgos.iterrows()), unsafe_allow_html=True)

# --- Tarjeta 2: búsqueda guiada ---
with st.container(border=True):
    encabezado_tarjeta(2, "Cuéntanos qué quieres estudiar", "Te mostramos las opciones que no han vencido")
    nivel_elegido = st.pills("Nivel", [TODOS] + ORDEN_NIVEL, default=TODOS,
                             format_func=lambda n: NIVEL_CORTO.get(n, n)) or TODOS
    areas = [a for a in scrapers.AREAS_SNIES if a in set(categorias(becas_apoyos["area_conocimiento"]))]
    area_elegida = st.selectbox("Área de conocimiento", [TODOS] + areas,
                                help="Incluye los apoyos que sirven para cualquier programa de la institución.")
    columna_1, columna_2 = st.columns([2, 1])
    texto_busqueda = columna_1.text_input("Busca por palabra", placeholder="Ejemplo: medicina, Saber 11, víctimas")
    orden = columna_2.selectbox("Ordenar por", ORDENES)
    with st.expander("Más filtros"):
        filtro_1, filtro_2 = st.columns(2)
        entidades = filtro_1.multiselect("Entidad", list(NOMBRE_CORTO), default=list(NOMBRE_CORTO),
                                         format_func=lambda e: NOMBRE_CORTO[e])
        estados = filtro_2.multiselect("Estado", ["abierta", "próxima", "sin fecha"],
                                       default=["abierta", "próxima", "sin fecha"],
                                       help="'sin fecha': apoyos permanentes cuya fecha no se publica; confírmala en "
                                            "el enlace.")
        instrumentos = filtro_1.multiselect("Tipo de ayuda", categorias(becas_apoyos["instrumento"]),
                                            default=categorias(becas_apoyos["instrumento"]))
        tipos = filtro_2.multiselect("Tipo de estudiante", categorias(becas_apoyos["tipo_estudiante"]),
                                     default=categorias(becas_apoyos["tipo_estudiante"]),
                                     help="Atenea no publica este dato: sus convocatorias siempre se muestran.")
        minimo = st.slider("Cubre al menos este % de la matrícula", 0, 100, 0, step=5,
                           help="Según el máximo publicado: 'hasta 90 %' cuenta como 90 %.")
        incluir_sin_porcentaje = st.checkbox("Incluir los que no publican porcentaje", value=True)

# --- Aplicación de los filtros ---
filtro = becas_apoyos["entidad"].isin(entidades) & becas_apoyos["estado"].isin(estados)
if nivel_elegido != TODOS:
    filtro &= tiene_alguna(becas_apoyos["nivel_formacion"], [nivel_elegido])
if area_elegida != TODOS:
    filtro &= tiene_alguna(becas_apoyos["area_conocimiento"], [area_elegida, scrapers.CUALQUIER_AREA])
filtro &= tiene_alguna(becas_apoyos["instrumento"], instrumentos + [SIN_DATO])
filtro &= tiene_alguna(becas_apoyos["tipo_estudiante"], tipos + [SIN_DATO])
filtro &= (becas_apoyos["porcentaje_max"] >= minimo) | (incluir_sin_porcentaje & becas_apoyos["porcentaje_max"].isna())
if texto_busqueda:
    texto_completo = (becas_apoyos["nombre"].fillna("") + " " + becas_apoyos["descripcion"].fillna("") + " "
                      + becas_apoyos["requisitos"].fillna("") + " " + becas_apoyos["programas"].fillna("")).map(sin_tildes)
    filtro &= texto_completo.str.contains(sin_tildes(texto_busqueda), regex=False)
resultado = becas_apoyos[filtro]
columnas_orden = {"Cierran primero": (["fecha_cierre", "porcentaje_max"], [True, False]),
                  "Cubren más de la matrícula": (["porcentaje_max", "fecha_cierre"], [False, True]),
                  "Tipo de ayuda": (["instrumento", "porcentaje_max"], [True, False])}[orden]
resultado = resultado.sort_values(columnas_orden[0], ascending=columnas_orden[1], na_position="last")

# --- Tarjeta 3: resultados, de a POR_PAGINA ---
with st.container(border=True):
    conteo = resultado["entidad"].value_counts()
    encabezado_tarjeta(3, f"{len(resultado)} opciones para ti",
                       " · ".join(f"{NOMBRE_CORTO[e]}: {conteo.get(e, 0)}" for e in NOMBRE_CORTO)
                       + " · confirma siempre fechas y requisitos en el enlace oficial")
    if resultado.empty:
        st.info("No hay opciones con estos filtros. Prueba con otro nivel o área, baja el porcentaje mínimo o borra "
                "la búsqueda.")
    clave = (nivel_elegido, area_elegida, texto_busqueda, orden, tuple(entidades), tuple(estados),
             tuple(instrumentos), tuple(tipos), minimo, incluir_sin_porcentaje)
    if st.session_state.get("clave_filtros") != clave:  # filtros nuevos: se vuelve a la primera página
        st.session_state["clave_filtros"], st.session_state["mostrados"] = clave, POR_PAGINA
    for _, fila in resultado.head(st.session_state["mostrados"]).iterrows():
        mostrar_apoyo(fila)
    if len(resultado) > st.session_state["mostrados"]:
        if st.button(f"Mostrar más ({len(resultado) - st.session_state['mostrados']} restantes)", width="stretch"):
            st.session_state["mostrados"] += POR_PAGINA
            st.rerun()

# --- Tarjeta 4: líneas de Atenea que se repiten (sirve aunque las convocatorias cierren) ---
lineas_atenea = lineas[(lineas["entidad"] == "Agencia Atenea") & ~lineas["situacion"].str.contains("terminada")]
if nivel_elegido != TODOS:
    lineas_atenea = lineas_atenea[tiene_alguna(lineas_atenea["nivel_formacion"], [nivel_elegido])]
with st.container(border=True):
    encabezado_tarjeta(4, "¿Y si ya cerró? Estas líneas de Atenea vuelven a abrir",
                       "Líneas con convocatorias que se repiten · agrupación inferida del nombre · tutorial, sección 8")
    if lineas_atenea.empty:
        st.markdown("Atenea no tiene líneas para este nivel: busca en las universidades.")
    for _, linea in lineas_atenea.sort_values("ultima_apertura", ascending=False).iterrows():
        ediciones = "1 edición" if linea["ediciones"] == 1 else f'{linea["ediciones"]} ediciones'
        st.markdown(f'<div class="dato"><b>{html.escape(linea["linea"])}</b> · {ediciones} · '
                    f'última apertura: {fecha_corta(linea["ultima_apertura"])}<br>'
                    f'<span class="chip">{linea["situacion"]}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="nota-morada">Las nuevas convocatorias se publican en '
                f'<a href="{scrapers.ATENEA_BASE}/convocatorias">{scrapers.ATENEA_BASE}/convocatorias</a> '
                f'y la inscripción es en SICORE, que pide usuario y contraseña.</div>', unsafe_allow_html=True)

st.caption("Fuente: results/becas_apoyos.csv, results/hallazgos.csv y results/tabla_lineas_apoyo.csv (tutorial.ipynb). "
           "En Atenea y la Javeriana, parte de la clasificación se deduce del texto (inferido); el área usa las áreas de "
           "conocimiento del SNIES. Para datos más recientes, ejecuta el tutorial con ACTUALIZAR_DATOS = True y "
           "vuelve a cargar esta página.")
