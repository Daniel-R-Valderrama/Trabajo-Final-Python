"""Fase 4: análisis que responde la pregunta.

¿En qué niveles de formación, instrumentos financieros y programas o áreas se concentran las becas y
apoyos educativos publicados por la Agencia Atenea y la Universidad de los Andes a noviembre de 2026?

Entrada: results/becas_apoyos.csv (de scripts/03_limpieza_validacion.py)
Salidas: results/tabla_nivel.csv, results/tabla_instrumento.csv, results/tabla_porcentaje_matricula.csv,
         results/tabla_nivel_instrumento.csv, results/tabla_area.csv, results/tabla_alcance_programas.csv,
         results/tabla_apoyos_por_programa.csv, results/tabla_lineas_apoyo.csv, results/tabla_efecto_lineas.csv,
         results/guia_por_perfil.csv
         figures/nivel_por_entidad.png, figures/instrumento_por_entidad.png, figures/porcentaje_matricula.png,
         figures/nivel_instrumento.png, figures/area_por_entidad.png
Se corre desde la raíz del proyecto:  .venv\\Scripts\\python.exe scripts\\04_analisis.py
"""

# %% Paquetes
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.append(".")  # permite importar utils/ al correr el script desde la raíz del proyecto
from utils import scrapers

# %% Datos y configuración de gráficos
becas_apoyos = pd.read_csv("results/becas_apoyos.csv", parse_dates=["fecha_apertura", "fecha_extraccion"])
ENTIDADES = ["Universidad de los Andes", "Agencia Atenea"]
NOMBRE_CORTO = {"Universidad de los Andes": "Uniandes", "Agencia Atenea": "Atenea"}
# Un color fijo por entidad (paleta Okabe-Ito, apta para daltonismo); se usa igual en todos los gráficos.
COLOR_ENTIDAD = {"Universidad de los Andes": "#0072B2", "Agencia Atenea": "#E69F00"}
ORDEN_NIVEL = ["Formación para el trabajo y cursos cortos", "Técnico y tecnológico", "Pregrado universitario",
               "Especialización", "Maestría", "Doctorado"]
ORDEN_INSTRUMENTO = ["Beca o subsidio de matrícula", "Descuento", "Crédito", "Crédito condonable",
                     "Crédito con pago contingente", "Apoyo de sostenimiento", "Formación sin costo"]
SIN_DATO = "Sin dato publicado"
# Cada fuente se extrajo en su propia fecha; el pie de las figuras las indica todas.
FECHAS = becas_apoyos.groupby("entidad")["fecha_extraccion"].max().dt.strftime("%Y-%m-%d")
PIE_FIGURA = ("Fuente: " + ", ".join(f"{NOMBRE_CORTO[e]} (extraído el {FECHAS[e]})" for e in ENTIDADES)
              + ". Atenea: categorías inferidas con reglas de texto. Elaboración: scripts/04_analisis.py")
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888888", "axes.grid": True, "grid.color": "#E5E5E5",
                     "axes.axisbelow": True})


def guardar_figura(figura, nombre):
    """Agrega el pie de fuente debajo de la figura y la guarda en figures/."""
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
    """% de registros de cada entidad que incluye cada categoría (un registro puede tener varias,
    así que las columnas pueden sumar más de 100 %). La última fila es el número de registros (n)."""
    largo = separar(base, columna)
    conteo = pd.crosstab(largo[columna], largo["entidad"]).reindex(columns=ENTIDADES, fill_value=0)
    tabla = (conteo / base["entidad"].value_counts()[ENTIDADES] * 100).round(1)
    tabla = tabla.reindex([c for c in orden + [SIN_DATO] if c in tabla.index])
    tabla.loc["Registros (n)"] = base["entidad"].value_counts()[ENTIDADES]
    return tabla


def grafico_barras(tabla, titulo, eje_x, nombre):
    """Barras horizontales agrupadas: % de registros de cada entidad por categoría."""
    tabla = tabla.drop(index="Registros (n)")
    figura, eje = plt.subplots(figsize=(8, 0.7 * len(tabla) + 1.4))
    alto = 0.38
    for k, entidad in enumerate(ENTIDADES):
        posiciones = [i + (k - 0.5) * alto for i in range(len(tabla))]
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
    eje.legend(frameon=False, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
    guardar_figura(figura, nombre)


# %% 1. Nivel de formación
nivel = porcentaje_por_categoria(becas_apoyos, "nivel_formacion", ORDEN_NIVEL)
nivel.to_csv("results/tabla_nivel.csv", encoding="utf-8-sig")
print("Nivel de formación (% de registros de cada entidad):")
print(nivel.to_string())
grafico_barras(nivel, "Niveles de formación a los que se dirigen las becas y apoyos",
               "% de registros de la entidad (un apoyo puede cubrir varios niveles)", "nivel_por_entidad.png")

# %% 2. Instrumento financiero
instrumento = porcentaje_por_categoria(becas_apoyos, "instrumento", ORDEN_INSTRUMENTO)
instrumento.to_csv("results/tabla_instrumento.csv", encoding="utf-8-sig")
print("\nInstrumento financiero (% de registros de cada entidad):")
print(instrumento.to_string())
grafico_barras(instrumento, "Instrumentos con los que se financian las becas y apoyos",
               "% de registros de la entidad (un apoyo puede combinar instrumentos)", "instrumento_por_entidad.png")

# %% 2b. Qué parte de la matrícula cubren (porcentaje publicado)
resumen_porcentaje = becas_apoyos.groupby("entidad").agg(
    registros=("nombre", "size"),
    publican_porcentaje=("porcentaje_max", "count"),
    mediana_del_maximo=("porcentaje_max", "median"),
    llegan_a_90_o_mas=("porcentaje_max", lambda p: int((p >= 90).sum())),
    llegan_a_100=("porcentaje_max", lambda p: int((p == 100).sum())),
).reindex(ENTIDADES)
print("\nPorcentaje de la matrícula publicado:")
print(resumen_porcentaje.join(pd.crosstab(becas_apoyos["entidad"], becas_apoyos["forma_porcentaje"])).to_string())

# Detalle en Uniandes (Atenea casi nunca publica porcentaje): máximo por instrumento y por nivel.
uniandes_pct = becas_apoyos[(becas_apoyos["entidad"] == "Universidad de los Andes") & becas_apoyos["porcentaje_max"].notna()]
resumir = {"apoyos": "count", "minimo": "min", "mediana": "median", "maximo": "max"}
porcentaje = pd.concat({
    "Instrumento": uniandes_pct.groupby("instrumento")["porcentaje_max"].agg(list(resumir.values()))
                   .set_axis(list(resumir), axis=1).reindex([i for i in ORDEN_INSTRUMENTO if i in set(uniandes_pct["instrumento"])]),
    "Nivel de formación": separar(uniandes_pct, "nivel_formacion").groupby("nivel_formacion")["porcentaje_max"]
                          .agg(list(resumir.values())).set_axis(list(resumir), axis=1)
                          .reindex([n for n in ORDEN_NIVEL if n in set(separar(uniandes_pct, "nivel_formacion")["nivel_formacion"])]),
})
porcentaje.to_csv("results/tabla_porcentaje_matricula.csv", encoding="utf-8-sig")
print(porcentaje.to_string())

# Un punto por apoyo; relleno = valor fijo o rango publicado, hueco = tope ("hasta"). La raya negra es la mediana.
figura, ejes = plt.subplots(1, 2, figsize=(11, 4.2))
for eje, (columna, orden, titulo) in zip(ejes, [("instrumento", ORDEN_INSTRUMENTO, "Por instrumento"),
                                                 ("nivel_formacion", ORDEN_NIVEL, "Por nivel de formación")]):
    largo = separar(uniandes_pct, columna)
    grupos = [g for g in orden if g in set(largo[columna])]
    for y, grupo in enumerate(grupos):
        valores = largo[largo[columna] == grupo].sort_values("porcentaje_max")
        desplazamiento = [((k % 5) - 2) * 0.07 for k in range(len(valores))]  # separa puntos iguales (sin azar)
        es_tope = (valores["forma_porcentaje"] == "hasta").to_numpy()
        posiciones = [y + d for d in desplazamiento]
        eje.scatter(valores["porcentaje_max"][~es_tope], [p for p, t in zip(posiciones, es_tope) if not t],
                    color=COLOR_ENTIDAD["Universidad de los Andes"], s=28, label="valor fijo o rango" if y == 0 else None)
        eje.scatter(valores["porcentaje_max"][es_tope], [p for p, t in zip(posiciones, es_tope) if t],
                    facecolors="white", edgecolors=COLOR_ENTIDAD["Universidad de los Andes"], s=28,
                    label="tope (\"hasta\")" if y == 0 else None)
        eje.plot([valores["porcentaje_max"].median()] * 2, [y - 0.3, y + 0.3], color="black", linewidth=2)
    eje.set_yticks(range(len(grupos)), grupos)
    eje.invert_yaxis()
    eje.set_xlim(0, 105)
    eje.set_xlabel("% máximo de la matrícula que puede cubrir")
    eje.set_title(titulo, loc="left")
    eje.grid(axis="y", visible=False)
ejes[0].legend(frameon=False, loc="lower left", fontsize=8)
figura.suptitle(f"Universidad de los Andes: qué parte de la matrícula cubren sus apoyos (n={len(uniandes_pct)} que publican porcentaje)",
                x=0.01, ha="left")
guardar_figura(figura, "porcentaje_matricula.png")

# %% 3. Cruce de nivel e instrumento: qué instrumento usa cada entidad en cada nivel
cruce = separar(separar(becas_apoyos, "nivel_formacion"), "instrumento")
cruce = cruce[(cruce["nivel_formacion"] != SIN_DATO) & (cruce["instrumento"] != SIN_DATO)]
nivel_instrumento = pd.crosstab([cruce["entidad"], cruce["nivel_formacion"]], cruce["instrumento"])
nivel_instrumento.to_csv("results/tabla_nivel_instrumento.csv", encoding="utf-8-sig")
print("\nRegistros por nivel e instrumento (solo los que publican ambos):")
print(nivel_instrumento.to_string())

figura, ejes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
filas = [n for n in ORDEN_NIVEL if n in set(cruce["nivel_formacion"])]
columnas = [i for i in ORDEN_INSTRUMENTO if i in set(cruce["instrumento"])]
for eje, entidad in zip(ejes, ENTIDADES):
    matriz = nivel_instrumento.loc[entidad].reindex(index=filas, columns=columnas, fill_value=0)
    eje.imshow(matriz, cmap="Blues", vmin=0, vmax=nivel_instrumento.to_numpy().max(), aspect="auto")
    for i in range(len(filas)):
        for j in range(len(columnas)):
            valor = matriz.iloc[i, j]
            if valor > 0:
                eje.text(j, i, str(valor), ha="center", va="center", fontsize=9,
                         color="white" if valor > nivel_instrumento.to_numpy().max() / 2 else "#333333")
    eje.set_xticks(range(len(columnas)), columnas, rotation=40, ha="right")
    eje.set_yticks(range(len(filas)), filas)
    eje.set_title(f"{entidad} (n={int((becas_apoyos['entidad'] == entidad).sum())})", loc="left")
    eje.grid(False)
figura.suptitle("Número de becas y apoyos por nivel de formación e instrumento", x=0.01, ha="left")
guardar_figura(figura, "nivel_instrumento.png")

# %% 4. Programa, facultad o área
# Uniandes publica las facultades y programas de cada apoyo; Atenea solo declara a veces un área o sector.
largo_area = separar(becas_apoyos, "area")
area = (largo_area.groupby(["entidad", "area"]).size().rename("registros").reset_index()
        .assign(porcentaje=lambda t: (t["registros"] / t["entidad"].map(becas_apoyos["entidad"].value_counts()) * 100).round(1))
        .sort_values(["entidad", "registros"], ascending=[False, False]))
area.to_csv("results/tabla_area.csv", index=False, encoding="utf-8-sig")
print("\nFacultad (Uniandes) o área declarada (Atenea):")
print(area.to_string(index=False))

# Alcance de cada apoyo de Uniandes: ¿sirve a un programa o a toda la universidad?
uniandes = becas_apoyos[becas_apoyos["entidad"] == "Universidad de los Andes"]
alcance = pd.cut(uniandes["n_programas"], bins=[0, 1, 10, 50, 1000],
                 labels=["1 programa", "2 a 10 programas", "11 a 50 programas", "Más de 50 programas"])
alcance = alcance.value_counts().sort_index().rename("apoyos").to_frame()
alcance.to_csv("results/tabla_alcance_programas.csv", encoding="utf-8-sig")
print("\nUniandes: número de programas a los que aplica cada apoyo:")
print(alcance.to_string())

# Cuántos apoyos tiene disponibles cada programa, resumido por el nivel del programa (según el catálogo).
apoyos_por_programa = separar(uniandes, "programas")["programas"].value_counts().rename("apoyos")
programas = scrapers.catalogo_programas_uniandes().set_index("programa").join(apoyos_por_programa).fillna({"apoyos": 0})
programas = (programas.groupby("nivel")["apoyos"].agg(programas="count", minimo="min", mediana="median", maximo="max")
             .reindex([n for n in ORDEN_NIVEL if n in set(programas["nivel"])]))
programas.to_csv("results/tabla_apoyos_por_programa.csv", encoding="utf-8-sig")
print("\nUniandes: apoyos disponibles por programa, según el nivel del programa:")
print(programas.to_string())

figura, ejes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.2, 1]})
for eje, entidad in zip(ejes, ENTIDADES):
    datos = area[area["entidad"] == entidad].set_index("area")["porcentaje"].sort_values()
    eje.barh(datos.index, datos, color=[("#BBBBBB" if a == SIN_DATO else COLOR_ENTIDAD[entidad]) for a in datos.index])
    for y, valor in enumerate(datos):
        eje.text(valor + 1, y, f"{valor:.0f} %", va="center", fontsize=7, color="#333333")
    eje.set_xlim(0, 110)
    eje.set_xlabel("% de registros de la entidad")
    eje.set_title({"Universidad de los Andes": "Uniandes: facultad (publicada)",
                   "Agencia Atenea": "Atenea: área declarada (inferida)"}[entidad], loc="left")
    eje.grid(axis="y", visible=False)
figura.suptitle("Facultades y áreas a las que se dirigen las becas y apoyos", x=0.01, ha="left")
guardar_figura(figura, "area_por_entidad.png")

# %% Mejora sugerida por la IA (sección 8 del tutorial): ficha por línea de apoyo y guía por perfil
# Cada convocatoria de Atenea se asigna a su línea con scrapers.LINEAS_ATENEA (inferido); en Uniandes
# cada apoyo del catálogo es su propia línea.
lineas = scrapers.ficha_por_linea(becas_apoyos, ORDEN_NIVEL, ORDEN_INSTRUMENTO)
lineas.to_csv("results/tabla_lineas_apoyo.csv", index=False, encoding="utf-8-sig")
print("\nLíneas de apoyo por entidad y situación en la foto:")
print(lineas.groupby(["entidad", "situacion"]).size().to_string())


def porcentaje_atenea(base, columna, orden):
    """% de registros de Atenea que incluye cada categoría (un registro puede tener varias)."""
    conteo = separar(base, columna)[columna].value_counts()
    return (conteo / len(base) * 100).round(1).reindex([c for c in orden + [SIN_DATO] if c in conteo.index])


# Efecto de cambiar la unidad: porcentajes de Atenea por convocatoria, por línea y por línea no terminada
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
print("\nAtenea: % por convocatoria y por línea de apoyo:")
print(efecto.to_string())

# Guía por perfil: qué líneas no terminadas cubren cada nivel de formación y dónde consultarlas
DONDE_CONSULTAR = {"Agencia Atenea": f"{scrapers.ATENEA_BASE}/convocatorias (inscripción en SICORE)",
                   "Universidad de los Andes": scrapers.UNIANDES_BASE}
no_terminadas = lineas[~lineas["situacion"].str.contains("terminada")]
filas = []
for nivel in ORDEN_NIVEL:
    del_nivel = no_terminadas[no_terminadas["nivel_formacion"].fillna("").str.split(scrapers.SEPARADOR)
                              .map(lambda niveles: nivel in niveles)]
    atenea = del_nivel[del_nivel["entidad"] == "Agencia Atenea"]
    uniandes_nivel = del_nivel[del_nivel["entidad"] == "Universidad de los Andes"]
    filas.append({
        "Quiere estudiar": nivel,
        "Líneas de Atenea": scrapers.SEPARADOR.join(atenea["linea"]) or "Ninguna",
        "Apoyos de Uniandes": len(uniandes_nivel),
        "Instrumentos": scrapers.unir_categorias(del_nivel["instrumento"], ORDEN_INSTRUMENTO),
        "% máximo de la matrícula (mediana, Uniandes)": uniandes_nivel["porcentaje_max"].median(),
        "Dónde consultar": " | ".join(DONDE_CONSULTAR[e] for e in ["Agencia Atenea", "Universidad de los Andes"]
                                      if e in set(del_nivel["entidad"])),
    })
guia = pd.DataFrame(filas)
guia.to_csv("results/guia_por_perfil.csv", index=False, encoding="utf-8-sig")
print("\nGuía por perfil:")
print(guia[["Quiere estudiar", "Apoyos de Uniandes", "% máximo de la matrícula (mediana, Uniandes)"]].to_string(index=False))
