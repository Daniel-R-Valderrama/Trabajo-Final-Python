"""App de Streamlit: buscador de becas y apoyos educativos de la Universidad de los Andes y la Agencia Atenea.

Muestra exactamente las tablas que produce el tutorial (results/); no raspa nada:
- results/becas_apoyos.csv: becas y apoyos (sección 4). Las convocatorias vencidas ("cerrada") no se muestran.
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
RUTA_LINEAS = Path("results/tabla_lineas_apoyo.csv")  # ficha por línea de apoyo (sección 8)
SIN_DATO = "Sin dato publicado"
ORDEN_NIVEL = ["Formación para el trabajo y cursos cortos", "Técnico y tecnológico", "Pregrado universitario",
               "Especialización", "Maestría", "Doctorado"]
NIVEL_CORTO = {"Formación para el trabajo y cursos cortos": "Curso para el trabajo",
               "Técnico y tecnológico": "Técnico o tecnólogo", "Pregrado universitario": "Universidad",
               "Especialización": "Especialización", "Maestría": "Maestría", "Doctorado": "Doctorado"}
NOMBRE_CORTO = {"Universidad de los Andes": "Uniandes", "Agencia Atenea": "Atenea"}
TODOS = "Todos los niveles"

st.set_page_config(page_title="Becas y apoyos educativos · Bogotá", page_icon="🎓", layout="centered")

# --- Estilo: barra superior, tarjetas blancas, cifras grandes y notas con borde morado ---
st.markdown("""
<style>
#MainMenu, header[data-testid="stHeader"], footer {visibility: hidden;}
.block-container {padding-top: 4.5rem; max-width: 820px;}
.barra {position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: #5046E5; color: white;
        padding: 0.75rem 1.5rem; font-weight: 600; font-size: 0.95rem;}
.portada {background: #E9E7FB; border-radius: 18px; padding: 2rem 1.5rem 1.4rem; text-align: center;
          margin-bottom: 1rem;}
.portada h1 {font-size: 2rem; margin: 0 0 0.4rem; color: #1F2133;}
.portada p {color: #555770; margin: 0.2rem 0;}
.marca {display: inline-block; border-radius: 6px; padding: 0 0.35rem; font-size: 0.85rem;}
.publicado {background: #E3F4E8; color: #1E7A3C;}
.inferido {background: #FFF1D6; color: #8A5A00;}
div[data-testid="stVerticalBlockBorderWrapper"] {background: white; border-radius: 16px !important;
        border: 1px solid #E4E3F0 !important; box-shadow: 0 1px 3px rgba(31, 33, 51, 0.06);}
.paso {display: inline-flex; width: 1.6rem; height: 1.6rem; border-radius: 50%; background: #5046E5;
       color: white; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 600;}
.titulo-tarjeta {font-size: 1.3rem; font-weight: 700; margin: 0.5rem 0 0.1rem; color: #1F2133;}
.fuente {color: #7A7C93; font-size: 0.78rem; margin-bottom: 0.6rem;}
.cifras {display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.6rem;}
.cifra {background: #F4F3FC; border-radius: 12px; padding: 0.8rem 0.9rem;}
.cifra .etiqueta {color: #555770; font-size: 0.85rem;}
.cifra .valor {font-size: 1.9rem; font-weight: 600; color: #1F2133; line-height: 1.3;}
.cifra .nota {color: #7A7C93; font-size: 0.75rem;}
.nota-morada {border-left: 4px solid #5046E5; background: #F4F3FC; padding: 0.7rem 1rem;
              border-radius: 0 10px 10px 0; margin: 0.8rem 0 0.3rem; color: #1F2133;}
.chip {display: inline-block; border-radius: 999px; padding: 0.1rem 0.6rem; margin: 0 0.25rem 0.25rem 0;
       font-size: 0.78rem; background: #F0EFF8; color: #3B3D55;}
.chip.uniandes {background: #E1EEFA; color: #0B5394;}
.chip.atenea {background: #FFF0D9; color: #8A5A00;}
.chip.abierta {background: #E3F4E8; color: #1E7A3C;}
.chip.proxima {background: #E9E7FB; color: #3F36C9;}
.nombre {font-weight: 600; font-size: 1.02rem; color: #1F2133; margin-bottom: 0.25rem;}
.detalle {color: #555770; font-size: 0.85rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar_datos(ruta, modificado):
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
    """Lista de categorías de una columna con varios valores por registro (incluye 'Sin dato publicado')."""
    return sorted(set(columna.fillna(SIN_DATO).str.split(scrapers.SEPARADOR).explode()))


def tiene_alguna(columna, elegidas):
    """True en los registros que tienen al menos una de las categorías elegidas."""
    return columna.fillna(SIN_DATO).str.split(scrapers.SEPARADOR).map(lambda valores: bool(set(valores) & set(elegidas)))


def texto_porcentaje(fila):
    """Porcentaje de la matrícula como se publica: '95 %', 'hasta 90 %' o '25 a 95 %'."""
    if pd.isna(fila["porcentaje_max"]):
        return ""
    if fila["forma_porcentaje"] == "hasta":
        return f"hasta {fila['porcentaje_max']:.0f} %"
    if fila["forma_porcentaje"] == "rango":
        return f"{fila['porcentaje_min']:.0f} a {fila['porcentaje_max']:.0f} %"
    return f"{fila['porcentaje_max']:.0f} %"


def cifra(etiqueta, valor, nota):
    """Recuadro con una cifra grande, como en las tarjetas de resumen."""
    return (f'<div class="cifra"><div class="etiqueta">{etiqueta}</div><div class="valor">{valor}</div>'
            f'<div class="nota">{nota}</div></div>')


def encabezado_tarjeta(numero, titulo, fuente):
    """Número en círculo, título en forma de pregunta y línea de fuente."""
    st.markdown(f'<span class="paso">{numero}</span><div class="titulo-tarjeta">{titulo}</div>'
                f'<div class="fuente">{fuente}</div>', unsafe_allow_html=True)


def fecha_corta(fecha):
    """Fecha como DD/MM/AAAA, o un aviso si la entidad no la publica."""
    return fecha.strftime("%d/%m/%Y") if pd.notna(fecha) else "sin fecha publicada"


# --- Datos ---
datos = cargar_datos(RUTA_DATOS, RUTA_DATOS.stat().st_mtime)
lineas = cargar_datos(RUTA_LINEAS, RUTA_LINEAS.stat().st_mtime)
becas_apoyos = datos[datos["estado"] != "cerrada"].reset_index(drop=True)
becas_apoyos["porcentaje"] = becas_apoyos.apply(texto_porcentaje, axis=1)
fechas = datos.groupby("entidad")["fecha_extraccion"].max().dt.strftime("%d/%m/%Y")
texto_fechas = " y ".join(f"{fecha} ({NOMBRE_CORTO[entidad]})" for entidad, fecha in fechas.items())

# --- Barra superior y portada ---
st.markdown('<div class="barra">Becas y apoyos educativos · Bogotá</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="portada">
  <h1>¿Cómo pago mis estudios?</h1>
  <p>Becas, créditos y apoyos de la Agencia Atenea y la Universidad de los Andes.</p>
  <p style="font-size:0.85rem;">Datos extraídos el {texto_fechas}.
  Junto a cada apoyo: <span class="marca publicado">publicado</span> por la entidad ·
  <span class="marca inferido">inferido</span> del texto de la convocatoria.</p>
</div>
""", unsafe_allow_html=True)

nivel_elegido = st.pills("¿Qué quieres estudiar?", [TODOS] + ORDEN_NIVEL, default=TODOS,
                         format_func=lambda n: NIVEL_CORTO.get(n, n)) or TODOS
texto_busqueda = st.text_input("Busca por palabra", placeholder="Ejemplo: ingeniería, sostenimiento, víctimas")

with st.expander("Más filtros"):
    columna_1, columna_2 = st.columns(2)
    entidades = columna_1.multiselect("Entidad", sorted(becas_apoyos["entidad"].unique()),
                                      default=sorted(becas_apoyos["entidad"].unique()))
    estados = columna_2.multiselect("Estado", ["abierta", "próxima", "sin fecha"], default=["abierta", "próxima"],
                                    help="'sin fecha': la entidad no publica fechas; confirma en el enlace si "
                                         "recibe solicitudes.")
    instrumentos = columna_1.multiselect("Tipo de ayuda", categorias(becas_apoyos["instrumento"]),
                                         default=categorias(becas_apoyos["instrumento"]))
    areas = columna_2.multiselect("Facultad o área", categorias(becas_apoyos["area"]),
                                  default=categorias(becas_apoyos["area"]),
                                  help="Uniandes: facultades del programa. Atenea: área que declara la convocatoria.")
    minimo = st.slider("Cubre al menos este % de la matrícula", 0, 100, 0, step=5,
                       help="Según el máximo publicado: 'hasta 90 %' cuenta como 90 %.")
    incluir_sin_porcentaje = st.checkbox("Incluir los que no publican porcentaje", value=True)

# --- Aplicación de los filtros ---
niveles = ORDEN_NIVEL + [SIN_DATO] if nivel_elegido == TODOS else [nivel_elegido]
filtro = (becas_apoyos["entidad"].isin(entidades) & becas_apoyos["estado"].isin(estados)
          & tiene_alguna(becas_apoyos["nivel_formacion"], niveles)
          & tiene_alguna(becas_apoyos["instrumento"], instrumentos)
          & tiene_alguna(becas_apoyos["area"], areas))
filtro &= (becas_apoyos["porcentaje_max"] >= minimo) | (incluir_sin_porcentaje & becas_apoyos["porcentaje_max"].isna())
if texto_busqueda:
    texto_completo = (becas_apoyos["nombre"].fillna("") + " " + becas_apoyos["cobertura"].fillna("") + " "
                      + becas_apoyos["requisitos"].fillna("")).map(sin_tildes)
    filtro &= texto_completo.str.contains(sin_tildes(texto_busqueda), regex=False)
resultado = becas_apoyos[filtro].sort_values(["fecha_cierre", "entidad", "nombre"], na_position="last")

# --- Tarjeta 1: resumen ---
with st.container(border=True):
    para_quien = "para ti" if nivel_elegido == TODOS else f"para {NIVEL_CORTO[nivel_elegido].lower()}"
    encabezado_tarjeta(1, f"Esto es lo que hay {para_quien}", f"Becas y apoyos no vencidos con los filtros elegidos · "
                       f"datos del {texto_fechas}")
    porcentajes = resultado["porcentaje_max"].dropna()
    st.markdown('<div class="cifras">'
                + cifra("Abiertas", int((resultado["estado"] == "abierta").sum()), "puedes postularte ya")
                + cifra("Próximas", int((resultado["estado"] == "próxima").sum()), "abren pronto")
                + cifra("Sin fecha", int((resultado["estado"] == "sin fecha").sum()),
                        "agrega el estado en «Más filtros»")
                + cifra("Cubren de la matrícula", f"{porcentajes.median():.0f} %" if len(porcentajes) else "—",
                        f"mediana del máximo publicado ({len(porcentajes)} apoyos)")
                + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="nota-morada">El estado es el de la fecha de extracción. Confirma siempre las fechas '
                'y los requisitos en el enlace oficial antes de postularte.</div>', unsafe_allow_html=True)

# --- Tarjeta 2: líneas de Atenea que se repiten (sirve aunque las convocatorias cierren) ---
lineas_atenea = lineas[(lineas["entidad"] == "Agencia Atenea") & ~lineas["situacion"].str.contains("terminada")]
if nivel_elegido != TODOS:
    lineas_atenea = lineas_atenea[tiene_alguna(lineas_atenea["nivel_formacion"], [nivel_elegido])]
with st.container(border=True):
    encabezado_tarjeta(2, "¿Y si ya cerró? Estas líneas de Atenea vuelven a abrir",
                       "Líneas con convocatorias que se repiten · agrupación inferida del nombre · "
                       "tutorial, sección 8")
    if lineas_atenea.empty:
        st.markdown("Atenea no tiene líneas para este nivel. Revisa los apoyos de Uniandes en "
                    f"[{scrapers.UNIANDES_BASE}]({scrapers.UNIANDES_BASE}).")
    else:
        for _, linea in lineas_atenea.sort_values("ultima_apertura", ascending=False).iterrows():
            ediciones = "1 edición" if linea["ediciones"] == 1 else f'{linea["ediciones"]} ediciones'
            st.markdown(f'<div class="detalle"><b>{html.escape(linea["linea"])}</b> · {ediciones} · '
                        f'última apertura: {fecha_corta(linea["ultima_apertura"])}<br>'
                        f'<span class="chip">{linea["situacion"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="nota-morada">Las nuevas convocatorias se publican en '
                    f'<a href="{scrapers.ATENEA_BASE}/convocatorias">{scrapers.ATENEA_BASE}/convocatorias</a> '
                    f'y la inscripción es en SICORE, que pide usuario y contraseña.</div>', unsafe_allow_html=True)

# --- Tarjeta 3: lista de becas y apoyos ---
with st.container(border=True):
    encabezado_tarjeta(3,f"{len(resultado)} becas y apoyos para revisar",
                       "Ordenados por fecha de cierre · los que cierran primero van arriba")
    if resultado.empty:
        st.info("No hay resultados con estos filtros. Prueba con otro nivel, agrega el estado «sin fecha» en "
                "«Más filtros», baja el porcentaje mínimo o borra la búsqueda.")
    for _, fila in resultado.iterrows():
        with st.container(border=True):
            clase_entidad = "uniandes" if fila["entidad"] == "Universidad de los Andes" else "atenea"
            clase_estado = {"abierta": "abierta", "próxima": "proxima"}.get(fila["estado"], "")
            origen = ('<span class="marca publicado">publicado</span>' if clase_entidad == "uniandes"
                      else '<span class="marca inferido">inferido</span>')
            chips = (f'<span class="chip {clase_entidad}">{NOMBRE_CORTO[fila["entidad"]]}</span>'
                     f'<span class="chip {clase_estado}">{fila["estado"]}</span>'
                     + "".join(f'<span class="chip">{html.escape(i)}</span>'
                               for i in str(fila["instrumento"]).split(scrapers.SEPARADOR) if i != "nan"))
            porcentaje = f" · cubre <b>{fila['porcentaje']}</b> de la matrícula" if fila["porcentaje"] else ""
            nivel = html.escape(fila["nivel_formacion"]) if pd.notna(fila["nivel_formacion"]) else SIN_DATO
            st.markdown(f'<div class="nombre">{html.escape(fila["nombre"])}</div>{chips}'
                        f'<div class="detalle">Nivel: {nivel} {origen}{porcentaje}<br>'
                        f'Abre: {fecha_corta(fila["fecha_apertura"])} · Cierra: <b>{fecha_corta(fila["fecha_cierre"])}</b>'
                        f'</div>', unsafe_allow_html=True)
            columna_texto, columna_boton = st.columns([3, 1], vertical_alignment="center")
            with columna_texto.expander("Qué cubre y requisitos"):
                st.markdown(f"**Qué cubre:** {fila['cobertura'] if pd.notna(fila['cobertura']) else SIN_DATO}")
                st.markdown(f"**Requisitos:** {fila['requisitos'] if pd.notna(fila['requisitos']) else SIN_DATO}")
                if pd.notna(fila["area"]):
                    st.markdown(f"**Facultad o área:** {fila['area']}")
            columna_boton.link_button("Ver oficial →", fila["enlace"], width="stretch")

st.caption("Fuente: results/becas_apoyos.csv y results/tabla_lineas_apoyo.csv (tutorial.ipynb). En Atenea, nivel, "
           "tipo de ayuda y área se deducen del texto de la convocatoria (inferido); en Uniandes los publica la "
           "universidad. Para datos más recientes, ejecuta el tutorial con ACTUALIZAR_DATOS = True y vuelve a "
           "cargar esta página.")
