"""App de Streamlit: buscador unificado de becas y apoyos educativos en Bogotá.

Solo lee results/becas_apoyos.csv (generado por scripts/03_limpieza_validacion.py); no raspa nada.
Se corre desde la raíz del proyecto:  .venv\\Scripts\\streamlit.exe run app.py
"""

import unicodedata

import pandas as pd
import streamlit as st

RUTA_DATOS = "results/becas_apoyos.csv"
st.set_page_config(page_title="Becas y apoyos educativos en Bogotá", layout="wide")


@st.cache_data
def cargar_datos():
    """Lee la tabla limpia con las fechas como datetime."""
    return pd.read_csv(RUTA_DATOS, parse_dates=["fecha_apertura", "fecha_cierre", "fecha_extraccion"])


def sin_tildes(texto):
    """Minúsculas y sin tildes, para que 'matricula' encuentre 'matrícula'."""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")


becas_apoyos = cargar_datos()
fecha_extraccion = becas_apoyos["fecha_extraccion"].max().strftime("%d/%m/%Y")

# --- Encabezado ---
st.title("Becas y apoyos educativos en Bogotá")
st.caption(
    f"Universidad de los Andes, Agencia Atenea y SENA (Betowa). Datos extraídos el {fecha_extraccion}: "
    "la información puede haber cambiado; confirma siempre en el enlace oficial antes de postularte.")

# --- Filtros (barra lateral) ---
st.sidebar.header("Filtros")
texto_busqueda = st.sidebar.text_input("Buscar en nombre, cobertura o requisitos")
entidades = st.sidebar.multiselect("Entidad", sorted(becas_apoyos["entidad"].unique()),
                                   default=sorted(becas_apoyos["entidad"].unique()))
tipos = st.sidebar.multiselect("Tipo", sorted(becas_apoyos["tipo"].unique()),
                               default=sorted(becas_apoyos["tipo"].unique()))
solo_abiertas = st.sidebar.checkbox("Solo abiertas", value=True)
estados = st.sidebar.multiselect("Estado", ["abierta", "próxima", "cerrada", "sin fecha"],
                                 default=["abierta", "próxima", "cerrada", "sin fecha"],
                                 disabled=solo_abiertas,
                                 help="Desactiva 'Solo abiertas' para elegir otros estados.")

# --- Aplicación de los filtros ---
filtro = becas_apoyos["entidad"].isin(entidades) & becas_apoyos["tipo"].isin(tipos)
filtro &= becas_apoyos["estado"].eq("abierta") if solo_abiertas else becas_apoyos["estado"].isin(estados)
if texto_busqueda:
    texto_completo = (becas_apoyos["nombre"].fillna("") + " " + becas_apoyos["cobertura"].fillna("") + " "
                      + becas_apoyos["requisitos"].fillna("")).map(sin_tildes)
    filtro &= texto_completo.str.contains(sin_tildes(texto_busqueda), regex=False)
resultado = becas_apoyos[filtro].sort_values(["fecha_cierre", "entidad", "nombre"], na_position="last")

# --- Resumen ---
columnas_resumen = st.columns(3)
columnas_resumen[0].metric("Resultados", len(resultado))
columnas_resumen[1].metric("Abiertas en los resultados", int((resultado["estado"] == "abierta").sum()))
columnas_resumen[2].metric("Enlaces verificados", f"{int(resultado['enlace_valido'].sum())} de {len(resultado)}")

# --- Tabla ---
if resultado.empty:
    st.info("No hay resultados con estos filtros. Prueba desactivar 'Solo abiertas' o borrar la búsqueda.")
else:
    st.dataframe(
        resultado[["nombre", "entidad", "tipo", "estado", "fecha_apertura", "fecha_cierre", "cobertura",
                   "requisitos", "alertas", "enlace"]],
        hide_index=True,
        width="stretch",
        column_config={
            "nombre": st.column_config.TextColumn("Nombre", width="medium"),
            "entidad": "Entidad",
            "tipo": "Tipo",
            "estado": "Estado",
            "fecha_apertura": st.column_config.DateColumn("Apertura", format="DD/MM/YYYY"),
            "fecha_cierre": st.column_config.DateColumn("Cierre", format="DD/MM/YYYY"),
            "cobertura": st.column_config.TextColumn("Qué cubre", width="large"),
            "requisitos": st.column_config.TextColumn("Requisitos", width="large"),
            "alertas": st.column_config.TextColumn("Verificar", help="Datos que la fuente no publica o que conviene confirmar"),
            "enlace": st.column_config.LinkColumn("Enlace oficial", display_text="Abrir"),
        },
    )

st.caption("El SENA no publica fechas de inscripción en Betowa: sus programas aparecen como 'sin fecha'. "
           "Atenea pide inscribirse en SICORE, que exige usuario y contraseña. "
           "Fuente: results/becas_apoyos.csv (scripts/03_limpieza_validacion.py).")
