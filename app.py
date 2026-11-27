"""App de Streamlit: buscador de becas y apoyos educativos de la Universidad de los Andes y la Agencia Atenea.

Muestra exactamente la tabla que produce el tutorial (results/becas_apoyos.csv); no raspa nada.
Para ver datos más recientes: en tutorial.ipynb poner ACTUALIZAR_DATOS = True, dar Run All y volver a
cargar la app. Las convocatorias vencidas (estado "cerrada") no se muestran.
Se corre desde la raíz del proyecto:  .venv\\Scripts\\streamlit.exe run app.py
"""

import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import scrapers

RUTA_DATOS = Path("results/becas_apoyos.csv")  # tabla final del tutorial (sección 4)
SIN_DATO = "Sin dato publicado"
st.set_page_config(page_title="Becas y apoyos educativos: Uniandes y Atenea", layout="wide")


@st.cache_data
def cargar_datos(modificado):
    """Lee la tabla del tutorial (modificado = fecha del archivo, para volver a leerla si el tutorial la cambia)."""
    return pd.read_csv(RUTA_DATOS, parse_dates=["fecha_apertura", "fecha_cierre", "fecha_extraccion"])


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
        return float("nan")
    if fila["forma_porcentaje"] == "hasta":
        return f"hasta {fila['porcentaje_max']:.0f} %"
    if fila["forma_porcentaje"] == "rango":
        return f"{fila['porcentaje_min']:.0f} a {fila['porcentaje_max']:.0f} %"
    return f"{fila['porcentaje_max']:.0f} %"


# --- Datos ---
datos = cargar_datos(RUTA_DATOS.stat().st_mtime)

becas_apoyos = datos[datos["estado"] != "cerrada"].reset_index(drop=True)
becas_apoyos["porcentaje"] = becas_apoyos.apply(texto_porcentaje, axis=1)
fechas = datos.groupby("entidad")["fecha_extraccion"].max().dt.strftime("%d/%m/%Y")

# --- Encabezado ---
st.title("Becas y apoyos educativos: Universidad de los Andes y Agencia Atenea")
st.caption(
    "Datos extraídos el " + " y ".join(f"{fecha} ({entidad})" for entidad, fecha in fechas.items())
    + ". El estado (abierta, próxima o sin fecha) es el de esa fecha; las vencidas se ocultan. "
    "Confirma siempre en el enlace oficial antes de postularte.")

# --- Filtros (barra lateral) ---
st.sidebar.header("Filtros")
texto_busqueda = st.sidebar.text_input("Buscar en nombre, cobertura o requisitos")
entidades = st.sidebar.multiselect("Entidad", sorted(becas_apoyos["entidad"].unique()),
                                   default=sorted(becas_apoyos["entidad"].unique()))
niveles = st.sidebar.multiselect("Nivel de formación", categorias(becas_apoyos["nivel_formacion"]),
                                 default=categorias(becas_apoyos["nivel_formacion"]))
instrumentos = st.sidebar.multiselect("Instrumento financiero", categorias(becas_apoyos["instrumento"]),
                                      default=categorias(becas_apoyos["instrumento"]))
areas = st.sidebar.multiselect("Facultad o área", categorias(becas_apoyos["area"]),
                               default=categorias(becas_apoyos["area"]),
                               help="Uniandes: facultades del programa. Atenea: área que declara la convocatoria.")
minimo = st.sidebar.slider("Cubre al menos este % de la matrícula", 0, 100, 0, step=5,
                           help="Según el máximo publicado: 'hasta 90 %' cuenta como 90 %.")
incluir_sin_porcentaje = st.sidebar.checkbox("Incluir los que no publican porcentaje", value=True)
estados = st.sidebar.multiselect("Estado", ["abierta", "próxima", "sin fecha"], default=["abierta", "próxima"],
                                 help="'sin fecha': la entidad no publica fechas; confirma en el enlace si recibe solicitudes.")

# --- Aplicación de los filtros ---
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

# --- Resumen ---
columnas_resumen = st.columns(3)
columnas_resumen[0].metric("Resultados", len(resultado))
columnas_resumen[1].metric("Abiertas", int((resultado["estado"] == "abierta").sum()))
columnas_resumen[2].metric("Próximas", int((resultado["estado"] == "próxima").sum()))

# --- Tabla ---
if resultado.empty:
    st.info("No hay resultados con estos filtros. Prueba agregar el estado 'sin fecha', bajar el porcentaje "
            "mínimo o borrar la búsqueda.")
else:
    st.dataframe(
        resultado[["nombre", "entidad", "nivel_formacion", "instrumento", "porcentaje", "area", "estado",
                   "fecha_apertura", "fecha_cierre", "cobertura", "requisitos", "enlace"]],
        hide_index=True,
        width="stretch",
        column_config={
            "nombre": st.column_config.TextColumn("Nombre", width="medium"),
            "entidad": "Entidad",
            "nivel_formacion": st.column_config.TextColumn("Nivel de formación", width="medium"),
            "instrumento": st.column_config.TextColumn("Instrumento", width="medium"),
            "porcentaje": st.column_config.TextColumn("% de la matrícula", help="Tal como lo publica la entidad"),
            "area": st.column_config.TextColumn("Facultad o área", width="medium"),
            "estado": "Estado",
            "fecha_apertura": st.column_config.DateColumn("Apertura", format="DD/MM/YYYY"),
            "fecha_cierre": st.column_config.DateColumn("Cierre", format="DD/MM/YYYY"),
            "cobertura": st.column_config.TextColumn("Qué cubre", width="large"),
            "requisitos": st.column_config.TextColumn("Requisitos", width="large"),
            "enlace": st.column_config.LinkColumn("Enlace oficial", display_text="Abrir"),
        },
    )

st.caption("En Atenea, nivel, instrumento y área se deducen del texto de la convocatoria (inferido); en Uniandes "
           "los publica la universidad. Atenea pide inscribirse en SICORE, que exige usuario y contraseña. "
           "Fuente: results/becas_apoyos.csv (tutorial.ipynb). Para datos más recientes, ejecuta el tutorial con "
           "ACTUALIZAR_DATOS = True y vuelve a cargar esta página.")
