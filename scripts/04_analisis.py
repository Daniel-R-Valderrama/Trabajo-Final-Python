"""Fase 4: análisis que responde la pregunta (mismo código que las secciones 5, 8 y 9 del tutorial).

¿En qué se diferencian y en qué se complementan los apoyos de una entidad pública que financia estudios en
varias instituciones (Agencia Atenea) y los de universidades privadas que financian sus propios programas
(Universidad de los Andes y Pontificia Universidad Javeriana)? La comparación se hace según el nivel y el
área que quiere estudiar un joven en Bogotá: el tipo de ayuda que ofrecen y qué parte de la matrícula
cubren (noviembre de 2026).

Entrada: results/becas_apoyos.csv (de scripts/03_limpieza_validacion.py)
Salidas: results/tabla_nivel.csv, results/tabla_instrumento.csv, results/tabla_porcentaje_matricula.csv,
         results/tabla_nivel_instrumento.csv, results/tabla_area.csv, results/tabla_area_nivel.csv,
         results/tabla_alcance_programas.csv, results/tabla_apoyos_por_programa.csv,
         results/tabla_lineas_apoyo.csv, results/tabla_efecto_lineas.csv, results/guia_por_perfil.csv,
         results/hallazgos.csv
         figures/nivel_por_entidad.png, figures/instrumento_por_entidad.png, figures/porcentaje_matricula.png,
         figures/nivel_instrumento.png, figures/area_por_entidad.png, figures/area_nivel.png
Se corre desde la raíz del proyecto:  .venv\\Scripts\\python.exe scripts\\04_analisis.py
"""

# %% Paquetes y datos
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.append(".")  # permite importar utils/ al correr el script desde la raíz del proyecto
from utils import scrapers

becas_apoyos = pd.read_csv("results/becas_apoyos.csv", parse_dates=["fecha_apertura", "fecha_cierre", "fecha_extraccion"])

# %%
# Primero la entidad pública; después las dos universidades privadas.
ENTIDADES = ["Agencia Atenea", "Universidad de los Andes", "Pontificia Universidad Javeriana"]
UNIVERSIDADES = ENTIDADES[1:]
NOMBRE_CORTO = {"Agencia Atenea": "Atenea", "Universidad de los Andes": "Uniandes",
                "Pontificia Universidad Javeriana": "Javeriana"}
# Un color fijo por entidad (paleta Okabe-Ito, apta para daltonismo).
COLOR_ENTIDAD = {"Agencia Atenea": "#E69F00", "Universidad de los Andes": "#0072B2",
                 "Pontificia Universidad Javeriana": "#009E73"}
ORDEN_NIVEL = ["Formación para el trabajo y cursos cortos", "Técnico y tecnológico", "Pregrado universitario",
               "Especialización", "Maestría", "Doctorado"]
ORDEN_INSTRUMENTO = ["Beca o subsidio de matrícula", "Descuento", "Crédito", "Crédito condonable",
                     "Crédito con pago contingente", "Apoyo de sostenimiento", "Formación sin costo"]
SIN_DATO = "Sin dato publicado"
# Cada fuente se extrajo en su propia fecha; el pie de las figuras las indica todas.
FECHAS = becas_apoyos.groupby("entidad")["fecha_extraccion"].max().dt.strftime("%Y-%m-%d")
PIE_FIGURA = ("Fuente: " + ", ".join(f"{NOMBRE_CORTO[e]} (extraído el {FECHAS[e]})" for e in ENTIDADES)
              + ". Atenea y Javeriana: categorías inferidas con reglas de texto. Elaboración: scripts/04_analisis.py")
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888888", "axes.grid": True, "grid.color": "#E5E5E5",
                     "axes.axisbelow": True})


def guardar_figura(figura, nombre):
    """Agrega el pie de fuente, guarda la figura en figures/ y la muestra."""
    figura.tight_layout()
    figura.text(0.01, 0.0, PIE_FIGURA, fontsize=7, color="#666666", va="top")
    figura.savefig(f"figures/{nombre}", dpi=150, bbox_inches="tight")
    plt.close(figura)


def separar(base, columna):
    """Una fila por registro y categoría: un apoyo con dos niveles aparece dos veces.
    Los registros sin dato quedan con la categoría SIN_DATO, para que se vean en las tablas."""
    largo = base.assign(**{columna: base[columna].fillna(SIN_DATO).str.split(scrapers.SEPARADOR)})
    return largo.explode(columna)


def porcentaje_por_categoria(base, columna, orden):
    """% de registros de cada entidad que incluye cada categoría. La última fila es el número de registros (n)."""
    largo = separar(base, columna)
    conteo = pd.crosstab(largo[columna], largo["entidad"]).reindex(columns=ENTIDADES, fill_value=0)
    tabla = (conteo / base["entidad"].value_counts()[ENTIDADES] * 100).round(1)
    tabla = tabla.reindex([c for c in orden + [SIN_DATO] if c in tabla.index])
    tabla.loc["Registros (n)"] = base["entidad"].value_counts()[ENTIDADES]
    return tabla


def grafico_barras(tabla, titulo, eje_x, nombre):
    """Barras horizontales agrupadas: % de registros de cada entidad por categoría."""
    tabla = tabla.drop(index="Registros (n)")
    figura, eje = plt.subplots(figsize=(8, 0.85 * len(tabla) + 1.4))
    alto = 0.8 / len(ENTIDADES)
    for k, entidad in enumerate(ENTIDADES):
        posiciones = [i + (k - (len(ENTIDADES) - 1) / 2) * alto for i in range(len(tabla))]
        eje.barh(posiciones, tabla[entidad], height=alto, color=COLOR_ENTIDAD[entidad], label=entidad)
        for y, valor in zip(posiciones, tabla[entidad]):
            if valor > 0:
                eje.text(valor + 1, y, f"{valor:.0f} %", va="center", fontsize=7, color="#333333")
    eje.set_yticks(range(len(tabla)), tabla.index)
    eje.invert_yaxis()
    eje.set_xlim(0, 110)
    eje.set_xlabel(eje_x)
    eje.set_title(titulo, loc="left", pad=28)
    eje.grid(axis="y", visible=False)
    eje.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0))
    guardar_figura(figura, nombre)

# %%
nivel = porcentaje_por_categoria(becas_apoyos, "nivel_formacion", ORDEN_NIVEL)
nivel.to_csv("results/tabla_nivel.csv", encoding="utf-8-sig")
print(nivel)

# %%
grafico_barras(nivel, "Niveles de formación a los que se dirigen las becas y apoyos",
               "% de registros de la entidad (un apoyo puede cubrir varios niveles)", "nivel_por_entidad.png")

# %%
instrumento = porcentaje_por_categoria(becas_apoyos, "instrumento", ORDEN_INSTRUMENTO)
instrumento.to_csv("results/tabla_instrumento.csv", encoding="utf-8-sig")
print(instrumento)

# %%
grafico_barras(instrumento, "Instrumentos con los que se financian las becas y apoyos",
               "% de registros de la entidad (un apoyo puede combinar instrumentos)", "instrumento_por_entidad.png")

# %%
resumen_porcentaje = becas_apoyos.groupby("entidad").agg(
    registros=("nombre", "size"),
    publican_porcentaje=("porcentaje_max", "count"),
    mediana_del_maximo=("porcentaje_max", "median"),
    llegan_a_90_o_mas=("porcentaje_max", lambda p: int((p >= 90).sum())),
    llegan_a_100=("porcentaje_max", lambda p: int((p == 100).sum())),
).reindex(ENTIDADES)
resumen_porcentaje.join(pd.crosstab(becas_apoyos["entidad"], becas_apoyos["forma_porcentaje"]))

# %%
con_porcentaje = becas_apoyos[becas_apoyos["entidad"].isin(UNIVERSIDADES) & becas_apoyos["porcentaje_max"].notna()]
partes = {}
for entidad in UNIVERSIDADES:
    base = con_porcentaje[con_porcentaje["entidad"] == entidad]
    for columna, orden, etiqueta in [("instrumento", ORDEN_INSTRUMENTO, "Instrumento"),
                                     ("nivel_formacion", ORDEN_NIVEL, "Nivel de formación")]:
        largo = separar(base, columna)
        partes[(NOMBRE_CORTO[entidad], etiqueta)] = (
            largo.groupby(columna)["porcentaje_max"].agg(apoyos="count", minimo="min", mediana="median", maximo="max")
            .reindex([c for c in orden if c in set(largo[columna])]))
porcentaje = pd.concat(partes)
porcentaje.to_csv("results/tabla_porcentaje_matricula.csv", encoding="utf-8-sig")

# Un punto por apoyo; relleno = valor fijo o rango publicado, hueco = tope ("hasta"). La raya negra es la mediana.
figura, ejes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
niveles = [n for n in ORDEN_NIVEL if n in set(separar(con_porcentaje, "nivel_formacion")["nivel_formacion"])]
for eje, entidad in zip(ejes, UNIVERSIDADES):
    largo = separar(con_porcentaje[con_porcentaje["entidad"] == entidad], "nivel_formacion")
    color = COLOR_ENTIDAD[entidad]
    for y, nivel_actual in enumerate(niveles):
        valores = largo[largo["nivel_formacion"] == nivel_actual].sort_values("porcentaje_max")
        if valores.empty:
            continue
        desplazamiento = [((k % 5) - 2) * 0.07 for k in range(len(valores))]  # separa puntos iguales (sin azar)
        es_tope = (valores["forma_porcentaje"] == "hasta").to_numpy()
        posiciones = [y + d for d in desplazamiento]
        eje.scatter(valores["porcentaje_max"][~es_tope], [p for p, t in zip(posiciones, es_tope) if not t],
                    color=color, s=28, label="valor fijo o rango" if y == 0 else None)
        eje.scatter(valores["porcentaje_max"][es_tope], [p for p, t in zip(posiciones, es_tope) if t],
                    facecolors="white", edgecolors=color, s=28, label="tope (\"hasta\")" if y == 0 else None)
        eje.plot([valores["porcentaje_max"].median()] * 2, [y - 0.3, y + 0.3], color="black", linewidth=2)
    eje.set_yticks(range(len(niveles)), niveles)
    eje.set_xlim(0, 105)
    eje.set_xlabel("% máximo de la matrícula que puede cubrir")
    eje.set_title(f"{NOMBRE_CORTO[entidad]} (n={int((con_porcentaje['entidad'] == entidad).sum())} que publican porcentaje)",
                  loc="left")
    eje.grid(axis="y", visible=False)
ejes[0].invert_yaxis()
ejes[0].legend(frameon=False, loc="lower left", fontsize=8)
figura.suptitle("Qué parte de la matrícula cubren los apoyos de las universidades, por nivel de formación",
                x=0.01, ha="left")
guardar_figura(figura, "porcentaje_matricula.png")
print(porcentaje)

# %%
cruce = separar(separar(becas_apoyos, "nivel_formacion"), "instrumento")
cruce = cruce[(cruce["nivel_formacion"] != SIN_DATO) & (cruce["instrumento"] != SIN_DATO)]
nivel_instrumento = pd.crosstab([cruce["entidad"], cruce["nivel_formacion"]], cruce["instrumento"])
nivel_instrumento.to_csv("results/tabla_nivel_instrumento.csv", encoding="utf-8-sig")

figura, ejes = plt.subplots(1, len(ENTIDADES), figsize=(15, 4.4), sharey=True)
filas = [n for n in ORDEN_NIVEL if n in set(cruce["nivel_formacion"])]
columnas = [i for i in ORDEN_INSTRUMENTO if i in set(cruce["instrumento"])]
maximo = nivel_instrumento.to_numpy().max()
for eje, entidad in zip(ejes, ENTIDADES):
    matriz = nivel_instrumento.loc[entidad].reindex(index=filas, columns=columnas, fill_value=0)
    eje.imshow(matriz, cmap="Blues", vmin=0, vmax=maximo, aspect="auto")
    for i in range(len(filas)):
        for j in range(len(columnas)):
            valor = matriz.iloc[i, j]
            if valor > 0:
                eje.text(j, i, str(valor), ha="center", va="center", fontsize=9,
                         color="white" if valor > maximo / 2 else "#333333")
    eje.set_xticks(range(len(columnas)), columnas, rotation=40, ha="right")
    eje.set_yticks(range(len(filas)), filas)
    eje.set_title(f"{NOMBRE_CORTO[entidad]} (n={int((becas_apoyos['entidad'] == entidad).sum())})", loc="left")
    eje.grid(False)
figura.suptitle("Número de becas y apoyos por nivel de formación e instrumento", x=0.01, ha="left")
guardar_figura(figura, "nivel_instrumento.png")

# %%
# "Cualquier área" es una categoría aparte: el apoyo no restringe el área y sirve para los programas
# que ofrezca la institución (no sabemos si la Javeriana o las aliadas de Atenea tienen programas en todas
# las áreas del SNIES, así que no se reparte entre ellas).
ORDEN_AREA = scrapers.AREAS_SNIES + ["Servicios (turismo, belleza y otros)", scrapers.CUALQUIER_AREA]
largo_area = separar(becas_apoyos, "area_conocimiento")
area = porcentaje_por_categoria(becas_apoyos, "area_conocimiento", ORDEN_AREA)
area.to_csv("results/tabla_area.csv", encoding="utf-8-sig")
print(area)
grafico_barras(area, "Áreas de conocimiento (SNIES) a las que se dirigen las becas y apoyos",
               "% de registros de la entidad (un apoyo puede servir a varias áreas)", "area_por_entidad.png")

# %%
# Área × nivel: cuántos registros de cada entidad sirven para cada combinación. Es la vista que
# responde "quiero estudiar tal área a tal nivel: ¿dónde busco?".
area_nivel_largo = separar(largo_area[largo_area["area_conocimiento"] != SIN_DATO], "nivel_formacion")
area_nivel_largo = area_nivel_largo[area_nivel_largo["nivel_formacion"] != SIN_DATO]
area_nivel = pd.crosstab([area_nivel_largo["entidad"], area_nivel_largo["area_conocimiento"]],
                         area_nivel_largo["nivel_formacion"])
area_nivel.to_csv("results/tabla_area_nivel.csv", encoding="utf-8-sig")

filas = [a for a in ORDEN_AREA if a in set(area_nivel_largo["area_conocimiento"])]
columnas = [n for n in ORDEN_NIVEL if n in set(area_nivel_largo["nivel_formacion"])]
maximo = area_nivel.to_numpy().max()
figura, ejes = plt.subplots(1, len(ENTIDADES), figsize=(15, 5.2), sharey=True)
for eje, entidad in zip(ejes, ENTIDADES):
    matriz = area_nivel.loc[entidad].reindex(index=filas, columns=columnas, fill_value=0)
    eje.imshow(matriz, cmap="Blues", vmin=0, vmax=maximo, aspect="auto")
    for i in range(len(filas)):
        for j in range(len(columnas)):
            valor = matriz.iloc[i, j]
            if valor > 0:
                eje.text(j, i, str(valor), ha="center", va="center", fontsize=8,
                         color="white" if valor > maximo / 2 else "#333333")
    eje.set_xticks(range(len(columnas)), columnas, rotation=40, ha="right")
    eje.set_yticks(range(len(filas)), filas)
    eje.set_title(f"{NOMBRE_CORTO[entidad]} (n={int((becas_apoyos['entidad'] == entidad).sum())})", loc="left")
    eje.grid(False)
figura.suptitle("Número de becas y apoyos que sirven para cada área de conocimiento y nivel de formación",
                x=0.01, ha="left")
guardar_figura(figura, "area_nivel.png")

# %%
uniandes = becas_apoyos[becas_apoyos["entidad"] == "Universidad de los Andes"]
alcance = pd.cut(uniandes["n_programas"], bins=[0, 1, 10, 50, 1000],
                 labels=["1 programa", "2 a 10 programas", "11 a 50 programas", "Más de 50 programas"])
alcance = alcance.value_counts().sort_index().rename("apoyos").to_frame()
alcance.to_csv("results/tabla_alcance_programas.csv", encoding="utf-8-sig")
print(alcance)

apoyos_por_programa = separar(uniandes, "programas")["programas"].value_counts().rename("apoyos")
programas = scrapers.catalogo_programas_uniandes().set_index("programa").join(apoyos_por_programa).fillna({"apoyos": 0})
programas = (programas.groupby("nivel")["apoyos"].agg(programas="count", minimo="min", mediana="median", maximo="max")
             .reindex([n for n in ORDEN_NIVEL if n in set(programas["nivel"])]))
programas.to_csv("results/tabla_apoyos_por_programa.csv", encoding="utf-8-sig")
print(programas)

# %%
lineas = scrapers.ficha_por_linea(becas_apoyos, ORDEN_NIVEL, ORDEN_INSTRUMENTO)
lineas.to_csv("results/tabla_lineas_apoyo.csv", index=False, encoding="utf-8-sig")

print("Registros por entidad:", becas_apoyos["entidad"].value_counts().to_dict())
print("Líneas de apoyo por entidad:", lineas["entidad"].value_counts().to_dict())
print(lineas.groupby(["entidad", "situacion"]).size().rename("líneas").to_frame())

# Las líneas de Atenea, de la más reciente a la más antigua
(lineas[lineas["entidad"] == "Agencia Atenea"]
 .sort_values("ultima_apertura", ascending=False)
 [["linea", "ediciones", "nivel_formacion", "instrumento", "primera_apertura", "ultima_apertura", "situacion"]])

# %%
def porcentaje_atenea(base, columna, orden):
    """% de registros de Atenea que incluye cada categoría (un registro puede tener varias)."""
    conteo = separar(base, columna)[columna].value_counts()
    return (conteo / len(base) * 100).round(1).reindex([c for c in orden + [SIN_DATO] if c in conteo.index])


atenea_convocatorias = becas_apoyos[becas_apoyos["entidad"] == "Agencia Atenea"]
atenea_lineas = lineas[lineas["entidad"] == "Agencia Atenea"]
atenea_no_terminadas = atenea_lineas[~atenea_lineas["situacion"].str.contains("terminada")]
unidades = {f"Por convocatoria (n={len(atenea_convocatorias)})": atenea_convocatorias,
            f"Por línea (n={len(atenea_lineas)})": atenea_lineas,
            f"Líneas no terminadas (n={len(atenea_no_terminadas)})": atenea_no_terminadas}
efecto = pd.concat({
    "Nivel de formación": pd.DataFrame({u: porcentaje_atenea(b, "nivel_formacion", ORDEN_NIVEL) for u, b in unidades.items()}),
    "Instrumento": pd.DataFrame({u: porcentaje_atenea(b, "instrumento", ORDEN_INSTRUMENTO) for u, b in unidades.items()}),
})
efecto.to_csv("results/tabla_efecto_lineas.csv", encoding="utf-8-sig")
print(efecto)

# %%
DONDE_CONSULTAR = {"Agencia Atenea": f"{scrapers.ATENEA_BASE}/convocatorias (inscripción en SICORE)",
                   "Universidad de los Andes": scrapers.UNIANDES_BASE,
                   "Pontificia Universidad Javeriana": f"{scrapers.JAVERIANA_BASE}/apoyo-financiero/becas-y-descuentos"}
no_terminadas = lineas[~lineas["situacion"].str.contains("terminada")]
filas = []
for nivel in ORDEN_NIVEL:
    del_nivel = no_terminadas[no_terminadas["nivel_formacion"].fillna("").str.split(scrapers.SEPARADOR)
                              .map(lambda niveles: nivel in niveles)]
    por_entidad = {e: del_nivel[del_nivel["entidad"] == e] for e in ENTIDADES}
    filas.append({
        "Quiere estudiar": nivel,
        "Líneas de Atenea": scrapers.SEPARADOR.join(por_entidad["Agencia Atenea"]["linea"]) or "Ninguna",
        "Apoyos de Uniandes": len(por_entidad["Universidad de los Andes"]),
        "Becas de la Javeriana": len(por_entidad["Pontificia Universidad Javeriana"]),
        "Instrumentos": scrapers.unir_categorias(del_nivel["instrumento"], ORDEN_INSTRUMENTO),
        "% máximo de la matrícula (mediana, Uniandes)": por_entidad["Universidad de los Andes"]["porcentaje_max"].median(),
        "% máximo de la matrícula (mediana, Javeriana)": por_entidad["Pontificia Universidad Javeriana"]["porcentaje_max"].median(),
        "Dónde consultar": " | ".join(DONDE_CONSULTAR[e] for e in ENTIDADES if not por_entidad[e].empty),
    })
guia = pd.DataFrame(filas)
guia.to_csv("results/guia_por_perfil.csv", index=False, encoding="utf-8-sig")
print(guia.to_string(index=False))

# %%
# Hallazgos para la portada de la app: se calculan con las tablas de este notebook, así la app y el
# tutorial dicen lo mismo.
fila_nivel = porcentaje_por_categoria(becas_apoyos, "nivel_formacion", ORDEN_NIVEL)
pregrado = guia.set_index("Quiere estudiar").loc["Pregrado universitario"]
maestria = guia.set_index("Quiere estudiar").loc["Maestría"]
medianas = becas_apoyos.groupby("entidad")["porcentaje_max"].median()
sin_restriccion = porcentaje_por_categoria(becas_apoyos, "area_conocimiento", ORDEN_AREA).loc[scrapers.CUALQUIER_AREA]
hallazgos = pd.DataFrame([
    ("Para un curso, un técnico o una tecnología: Atenea",
     f"Solo Atenea apoya la formación para el trabajo ({fila_nivel.loc['Formación para el trabajo y cursos cortos', 'Agencia Atenea']:.0f} % "
     f"de sus convocatorias) y los estudios técnicos y tecnológicos ({fila_nivel.loc['Técnico y tecnológico', 'Agencia Atenea']:.0f} %). "
     "Las universidades solo financian sus propios pregrados y posgrados."),
    ("En pregrado coinciden las tres",
     f"Es el nivel donde las tres tienen más opciones: {len(pregrado['Líneas de Atenea'].split(scrapers.SEPARADOR))} líneas de Atenea, "
     f"{pregrado['Apoyos de Uniandes']} apoyos de Uniandes y {pregrado['Becas de la Javeriana']} becas de la Javeriana."),
    ("Cuánto cubren: depende de la universidad",
     f"Uniandes suele cubrir casi toda la matrícula (mediana del máximo de {medianas['Universidad de los Andes']:.0f} %) y la "
     f"Javeriana menos ({medianas['Pontificia Universidad Javeriana']:.0f} %). Atenea casi nunca publica el porcentaje, "
     "pero es la única que también paga el sostenimiento."),
    ("Para un posgrado: las universidades",
     f"Uniandes tiene {maestria['Apoyos de Uniandes']} apoyos de maestría y la Javeriana {maestria['Becas de la Javeriana']}; "
     "Atenea solo tiene una línea de doctorado."),
    ("El área casi nunca te excluye",
     f"El {sin_restriccion['Agencia Atenea']:.0f} % de las convocatorias de Atenea y el "
     f"{sin_restriccion['Pontificia Universidad Javeriana']:.0f} % de las becas de la Javeriana sirven para cualquier programa; "
     "Uniandes reparte sus apoyos entre todas sus facultades."),
], columns=["titulo", "texto"])
hallazgos.to_csv("results/hallazgos.csv", index=False, encoding="utf-8-sig")
with pd.option_context("display.max_colwidth", None):
    print(hallazgos)
