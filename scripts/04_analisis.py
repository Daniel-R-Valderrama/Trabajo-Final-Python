"""Fase 4: análisis que responde la pregunta.

¿Cómo se comparan las becas y apoyos educativos publicados por la Universidad de los Andes,
la Agencia Atenea y el SENA, a la fecha de extracción, en cobertura, requisitos y vigencia?

Entrada: results/becas_apoyos.csv (de scripts/03_limpieza_validacion.py)
Salidas: results/tabla_vigencia.csv, results/tabla_convocatorias_vigentes.csv,
         results/tabla_cobertura.csv, results/tabla_requisitos.csv
         figures/estado_por_entidad.png, figures/dias_para_cierre.png,
         figures/cobertura_por_entidad.png, figures/requisitos_por_entidad.png
Se corre desde la raíz del proyecto:  .venv\\Scripts\\python.exe scripts\\04_analisis.py
"""

# %% Paquetes
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

# %% Datos y configuración de gráficos
becas_apoyos = pd.read_csv("results/becas_apoyos.csv",
                           parse_dates=["fecha_apertura", "fecha_cierre", "fecha_extraccion"])
FECHA = becas_apoyos["fecha_extraccion"].max().strftime("%Y-%m-%d")
ENTIDADES = ["Universidad de los Andes", "Agencia Atenea", "SENA"]
# Un color fijo por entidad (paleta Okabe-Ito, apta para daltonismo); se usa igual en todos los gráficos.
COLOR_ENTIDAD = {"Universidad de los Andes": "#0072B2", "Agencia Atenea": "#E69F00", "SENA": "#009E73"}
PIE_FIGURA = f"Fuente: páginas de Uniandes, Atenea y SENA Betowa, extraídas el {FECHA}. Elaboración: scripts/04_analisis.py"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888888", "axes.grid": True, "grid.color": "#E5E5E5",
                     "axes.axisbelow": True})


def guardar_figura(figura, nombre):
    """Agrega el pie de fuente debajo de la figura y la guarda en figures/."""
    figura.tight_layout()
    figura.text(0.01, 0.0, PIE_FIGURA, fontsize=7, color="#666666", va="top")
    figura.savefig(f"figures/{nombre}", dpi=150, bbox_inches="tight")
    plt.close(figura)


def porcentaje_por_entidad(indicadores, base):
    """% de registros de cada entidad que cumple cada indicador (texto que coincide con la regla)."""
    tabla = pd.DataFrame({nombre: base.groupby("entidad")[columna].apply(
        lambda textos, patron=patron: textos.str.contains(patron, case=False, regex=True).mean() * 100)
        for nombre, (columna, patron) in indicadores.items()}).T
    return tabla[ENTIDADES].round(1)


# %% 1. Vigencia: estado de las convocatorias a la fecha de extracción
ESTADOS = ["abierta", "próxima", "cerrada", "sin fecha"]
vigencia = pd.crosstab(becas_apoyos["entidad"], becas_apoyos["estado"]).reindex(index=ENTIDADES, columns=ESTADOS, fill_value=0)
vigencia["total"] = vigencia.sum(axis=1)
vigencia["% con fecha de cierre publicada"] = (
    becas_apoyos.groupby("entidad")["fecha_cierre"].apply(lambda f: f.notna().mean() * 100).round(1))
vigencia["mediana de días de inscripción"] = becas_apoyos.groupby("entidad")["dias_ventana"].median()
vigencia.to_csv("results/tabla_vigencia.csv", encoding="utf-8-sig")
print("Vigencia por entidad:")
print(vigencia.to_string())

# Gráfico: barras 100 % apiladas del estado por entidad (una tonalidad: más oscuro = más vigente).
COLOR_ESTADO = {"abierta": "#08519C", "próxima": "#4292C6", "cerrada": "#9ECAE1", "sin fecha": "#E5E5E5"}
proporcion = vigencia[ESTADOS].div(vigencia["total"], axis=0) * 100
figura, eje = plt.subplots(figsize=(8, 3))
izquierda = pd.Series(0.0, index=ENTIDADES)
for estado in ESTADOS:
    eje.barh(ENTIDADES, proporcion[estado], left=izquierda, color=COLOR_ESTADO[estado],
             edgecolor="white", linewidth=2, label=estado, height=0.6)
    for entidad in ENTIDADES:
        if proporcion.loc[entidad, estado] >= 4:  # etiqueta solo en segmentos con espacio para el número
            eje.text(izquierda[entidad] + proporcion.loc[entidad, estado] / 2, entidad,
                     str(vigencia.loc[entidad, estado]), ha="center", va="center",
                     color="white" if estado in ("abierta", "próxima") else "#333333", fontsize=9)
    izquierda += proporcion[estado]
eje.invert_yaxis()
eje.set_xlim(0, 100)
eje.set_xlabel("% de registros publicados (el número es la cantidad)")
eje.set_title(f"Estado de las becas y apoyos publicados al {FECHA}", loc="left", pad=28)
eje.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False)
eje.grid(axis="y", visible=False)
guardar_figura(figura, "estado_por_entidad.png")

# %% Interpretación (cifras de la extracción del 2026-11-18)
# Las tres entidades informan la vigencia de forma muy distinta:
# - Atenea trabaja por convocatorias cortas: publica fecha de cierre en el 90,7 % de sus registros y la
#   mediana de la ventana de inscripción es de 14 días. A la fecha hay 3 abiertas y 3 próximas.
# - Uniandes publica fechas solo en 2 de sus 18 apoyos (11,1 %), las 2 abiertas. Los otros 16 son
#   líneas permanentes sin ventana publicada en la ficha: no se puede saber desde la página si hoy reciben solicitudes.
# - El SENA no publica fechas de inscripción en Betowa (0 %). Además, 2 programas siguen publicados con
#   períodos académicos que terminaron en 2015 y 2019: oferta vencida que la página no distingue.

# %% 2. Vigencia: convocatorias abiertas y próximas, y días que faltan para el cierre
vigentes = becas_apoyos[becas_apoyos["estado"].isin(["abierta", "próxima"])].copy()
vigentes["dias_para_cierre"] = (vigentes["fecha_cierre"].dt.normalize() - vigentes["fecha_extraccion"]).dt.days
vigentes = vigentes.sort_values("dias_para_cierre")
columnas_vigentes = ["entidad", "nombre", "tipo", "estado", "fecha_apertura", "fecha_cierre", "dias_para_cierre",
                     "requisitos_origen", "enlace"]
vigentes[columnas_vigentes].to_csv("results/tabla_convocatorias_vigentes.csv", index=False, encoding="utf-8-sig")
print("\nConvocatorias abiertas y próximas:")
print(vigentes[["entidad", "nombre", "estado", "dias_para_cierre"]].to_string(index=False))

figura, eje = plt.subplots(figsize=(8, 0.45 * len(vigentes) + 1.2))
etiquetas = [n if len(n) <= 55 else n[:52] + "..." for n in vigentes["nombre"]]
eje.barh(etiquetas, vigentes["dias_para_cierre"], color=vigentes["entidad"].map(COLOR_ENTIDAD), height=0.6)
for posicion, (dias, estado) in enumerate(zip(vigentes["dias_para_cierre"], vigentes["estado"])):
    texto = "cierra hoy" if dias == 0 else f"{dias} días"
    eje.text(dias + 0.5, posicion, texto + (" (aún no abre)" if estado == "próxima" else ""),
             va="center", fontsize=8, color="#333333")
eje.invert_yaxis()
eje.set_xlabel(f"Días que faltan para el cierre, contados desde el {FECHA}")
eje.set_title("Becas y apoyos con inscripciones abiertas o próximas", loc="left", pad=28)
eje.grid(axis="y", visible=False)
eje.legend(handles=[Patch(color=COLOR_ENTIDAD[e], label=e) for e in ENTIDADES if e in set(vigentes["entidad"])],
           frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0))
guardar_figura(figura, "dias_para_cierre.png")

# %% Interpretación
# Quien busque hoy tiene poco margen: de las 5 convocatorias abiertas, 3 cierran en 6 días o menos
# (todas de Atenea, una cierra el mismo día de la extracción). Las de Uniandes tienen más plazo
# (8 y 18 días) pero son para posgrado. Las 3 próximas de Atenea abren en diciembre de 2026.

# %% 3. Cobertura: qué cubre cada apoyo, según el texto publicado
# Regla explícita: un registro tiene el componente si su texto de cobertura contiene el patrón.
INDICADORES_COBERTURA = {
    "Matrícula": ("cobertura", r"matr[ií]cula"),
    "Hasta el 100 %": ("cobertura", r"100\s?%"),
    "Apoyo de sostenimiento": ("cobertura", r"sostenimiento|apoyo económico|manutenci|transporte"),
    "Crédito (condonable o no)": ("cobertura", r"cr[eé]dito|condonable|pr[eé]stamo"),
    "Descuento": ("cobertura", r"descuento"),
    "Formación sin costo": ("cobertura", r"gratuit"),
}
cobertura = porcentaje_por_entidad(INDICADORES_COBERTURA, becas_apoyos)
cobertura.loc["Registros (n)"] = becas_apoyos["entidad"].value_counts()[ENTIDADES]
cobertura.to_csv("results/tabla_cobertura.csv", encoding="utf-8-sig")
print("\nCobertura (% de registros cuyo texto menciona cada componente):")
print(cobertura.to_string())


def grafico_indicadores(tabla, titulo, eje_x, nombre):
    """Barras horizontales agrupadas: % por entidad para cada indicador."""
    tabla = tabla.drop(index=[i for i in tabla.index if i.endswith("(n)")])
    figura, eje = plt.subplots(figsize=(8, 0.75 * len(tabla) + 1.2))
    alto = 0.25
    for k, entidad in enumerate(ENTIDADES):
        posiciones = [i + (k - 1) * alto for i in range(len(tabla))]
        eje.barh(posiciones, tabla[entidad], height=alto, color=COLOR_ENTIDAD[entidad],
                 edgecolor="white", linewidth=1, label=entidad)
        for y, valor in zip(posiciones, tabla[entidad]):
            if valor > 0:
                etiqueta = "<1 %" if valor < 0.5 else f"{valor:.0f} %"
                eje.text(valor + 1, y, etiqueta, va="center", fontsize=7, color="#333333")
    eje.set_yticks(range(len(tabla)), tabla.index)
    eje.invert_yaxis()
    eje.set_xlim(0, 110)
    eje.set_xlabel(eje_x)
    eje.set_title(titulo, loc="left", pad=28)
    eje.grid(axis="y", visible=False)
    eje.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0))
    guardar_figura(figura, nombre)


grafico_indicadores(cobertura, "Qué cubren las becas y apoyos publicados",
                    "% de registros de la entidad cuyo texto de cobertura lo menciona", "cobertura_por_entidad.png")

# %% Interpretación
# La cobertura distingue con claridad a las tres entidades:
# - Uniandes concentra sus apoyos en la matrícula (94,4 %), a veces hasta el 100 %, con descuentos y
#   créditos; ninguno menciona apoyo de sostenimiento.
# - Atenea combina matrícula (57,4 %) con apoyo de sostenimiento (53,7 %); además ofrece créditos
#   condonables (22,2 %) y formación gratuita (25,9 %). Es la oferta más amplia en tipos de apoyo.
# - El SENA ofrece formación gratuita (100 %), no becas: en Bogotá son cursos complementarios cortos
#   (227 de 231 duran 40 horas).
# Advertencia: los porcentajes cuentan menciones en el texto publicado; no miden montos ni cupos.

# %% 4. Requisitos: qué se pide, entre los registros que publican requisitos
INDICADORES_REQUISITOS = {
    "Vivir o haber estudiado en Bogotá": ("requisitos", r"bogot[aá]"),
    "Edad mínima o máxima": ("requisitos", r"edad|\d+\)?\s+años"),
    "Ser bachiller o cursar grado 11": ("requisitos", r"bachiller|grado (?:once|11)"),
    "Prueba Saber 11 o ICFES": ("requisitos", r"saber 11|icfes"),
    "Estrato o Sisbén": ("requisitos", r"estrato|sisb[eé]n"),
    # "estudiantes" suelto no cuenta: el SENA lo usa para describir el público ("estudiantes, empresarios...").
    "Estar admitido o ser estudiante": ("requisitos", r"admitid|matriculad|ser estudiante|estudiantes? (?:de|que|nuevos|antiguos)"),
    "Manejo de herramientas digitales": ("requisitos", r"herramientas inform|ambientes virtuales"),
}
con_requisitos = becas_apoyos[becas_apoyos["requisitos"].notna()]
requisitos = porcentaje_por_entidad(INDICADORES_REQUISITOS, con_requisitos)
requisitos.loc["Registros con requisitos publicados (n)"] = con_requisitos["entidad"].value_counts()[ENTIDADES]
requisitos.loc["Registros totales (n)"] = becas_apoyos["entidad"].value_counts()[ENTIDADES]
requisitos.to_csv("results/tabla_requisitos.csv", encoding="utf-8-sig")
print("\nRequisitos (% de registros con requisitos publicados que mencionan cada condición):")
print(requisitos.to_string())

n_texto = ", ".join(f"{e.split()[-1]} n={int(requisitos.loc['Registros con requisitos publicados (n)', e])}"
                    for e in ENTIDADES)
grafico_indicadores(requisitos, "Qué piden las becas y apoyos que publican requisitos",
                    f"% de registros con requisitos publicados ({n_texto})", "requisitos_por_entidad.png")

# %% Interpretación
# Los requisitos marcan quién puede acceder:
# - Atenea es la más exigente y la más focalizada: en sus 5 registros con requisitos publicados, todos
#   mencionan Bogotá y 4 de 5 piden ser bachiller o estar en grado 11, haber presentado Saber 11 y
#   cumplir un límite de edad. Ojo: n = 5 (4 vigentes y 1 finalizada que comparte el PDF), porque
#   solo se descargaron los requisitos de la oferta actual; no describe el histórico.
# - Uniandes pide sobre todo ser estudiante o estar admitido en un programa (37,5 %); en la ficha
#   publica a qué programas aplica, no los criterios socioeconómicos, que están en el reglamento en PDF.
# - El SENA casi no pone barreras: edad mínima de 14 años en los 231 programas y, en el 85,3 %,
#   manejo básico de herramientas digitales (son cursos virtuales).
