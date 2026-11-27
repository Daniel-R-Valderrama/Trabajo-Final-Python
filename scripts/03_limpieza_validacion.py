"""Fase 3: limpieza y validación.

Revisa tipos, faltantes, duplicados y valores atípicos; pasa las fechas a datetime; define el
alcance (apoyos para personas); calcula el estado de cada convocatoria a la fecha de extracción;
valida los enlaces y marca alertas de calidad.

Entrada: results/extraccion_sin_limpiar.csv (de scripts/02_extraccion.py)
         results/validacion_enlaces.csv (caché de enlaces, si ACTUALIZAR_DATOS = False)
Salida:  results/becas_apoyos.csv
         results/validacion_enlaces.csv (solo si ACTUALIZAR_DATOS = True)
Se corre desde la raíz del proyecto:  .venv\\Scripts\\python.exe scripts\\03_limpieza_validacion.py
"""

# %% Paquetes
import sys

import pandas as pd

sys.path.append(".")  # permite importar utils/ al correr el script desde la raíz del proyecto
from utils import scrapers

# %% Configuración
# True: vuelve a visitar cada enlace y guarda el resultado. False: usa el resultado guardado.
ACTUALIZAR_DATOS = False

becas_apoyos = pd.read_csv("results/extraccion_sin_limpiar.csv")
COLUMNAS_TEXTO = ["nombre", "cobertura", "requisitos"]
COLUMNAS_FECHA = ["fecha_apertura", "fecha_cierre", "fecha_extraccion"]

# %% 1. Tipos y faltantes
# Todas las columnas llegan como texto: las fechas se publican en formatos distintos según la fuente.
# Los faltantes no se rellenan: un NaN significa que la entidad no publica ese dato (ver data/README.md).
print("Tipos de dato:")
print(becas_apoyos.dtypes.to_string())
print("\nFaltantes por entidad:")
print(becas_apoyos[COLUMNAS_TEXTO + COLUMNAS_FECHA].isna().groupby(becas_apoyos["entidad"]).sum().to_string())

# %% 2. Duplicados
# Un registro es la misma convocatoria si repite el enlace. Nombres repetidos con enlaces distintos
# son convocatorias diferentes del mismo programa (por ejemplo, dos aperturas del mismo fondo): se conservan.
print("\nFilas idénticas:", becas_apoyos.duplicated().sum())
print("Enlaces repetidos:", becas_apoyos["enlace"].duplicated().sum())
repetidos = becas_apoyos[becas_apoyos.duplicated(["entidad", "nombre"], keep=False)]
print("Nombres repetidos dentro de una entidad (enlaces distintos):")
print(repetidos[["entidad", "nombre", "fecha_apertura", "enlace"]].to_string(index=False))
becas_apoyos = becas_apoyos.drop_duplicates(subset="enlace")

# %% 3. Limpieza de texto
# Se quitan caracteres invisibles (espacio de ancho cero en algunas páginas de Atenea), espacios
# repetidos y espacios antes de comas. No se cambia el contenido ni las mayúsculas del original.
for columna in COLUMNAS_TEXTO:
    becas_apoyos[columna] = becas_apoyos[columna].map(scrapers.limpiar_cadena)

# %% 4. Fechas a datetime
# Atenea publica ISO con zona horaria (se pasa a hora de Bogotá) o solo la fecha; Uniandes publica
# "26 de noviembre de 2026". Se revisa que ninguna fecha publicada quede sin convertir.
for columna in COLUMNAS_FECHA:
    convertidas = becas_apoyos[columna].map(scrapers.texto_a_fecha)
    sin_convertir = becas_apoyos[columna].notna() & convertidas.isna()
    print(f"{columna}: {int(sin_convertir.sum())} fechas publicadas que no se pudieron convertir")
    becas_apoyos[columna] = pd.to_datetime(convertidas)

# %% 5. Valores atípicos en las fechas
# Se revisan dos cosas: cierres anteriores a la apertura (error de publicación) y ventanas de
# inscripción muy largas. No se borran: se marcan como alerta para que el lector las vea.
becas_apoyos["dias_ventana"] = (becas_apoyos["fecha_cierre"] - becas_apoyos["fecha_apertura"]).dt.days
print("\nCierres antes de la apertura:", int((becas_apoyos["dias_ventana"] < 0).sum()))
print("Días entre apertura y cierre:")
print(becas_apoyos.groupby("entidad")["dias_ventana"].describe().round(1).to_string())
print("Ventanas más largas:")
print(becas_apoyos.nlargest(3, "dias_ventana")[["entidad", "nombre", "dias_ventana"]].to_string(index=False))

# %% 6. Alcance: becas y apoyos educativos para personas
# La pregunta es sobre apoyos para estudiar. Algunas convocatorias de Atenea financian proyectos de
# investigación, empresas (Mipymes) o prácticas laborales: no son apoyos educativos y se excluyen
# con una regla explícita (scrapers.PATRON_NO_ESTUDIANTES y PATRON_NO_ESTUDIANTES_NOMBRE).
# Se listan para que la exclusión sea verificable.
para_personas = [scrapers.dirigido_a_personas(n, c)
                 for n, c in zip(becas_apoyos["nombre"], becas_apoyos["cobertura"])]
excluidas = becas_apoyos.loc[[not x for x in para_personas], ["entidad", "nombre"]]
print(f"\nExcluidas por no ser apoyos educativos para personas ({len(excluidas)}):")
print(excluidas.to_string(index=False))
becas_apoyos = becas_apoyos[para_personas].reset_index(drop=True)

# %% 7. Estado de cada convocatoria a la fecha de extracción
# Reglas en scrapers.calcular_estado. Se agrega "próxima" a abierta / cerrada / sin fecha porque
# Atenea publica convocatorias que aún no abren: con solo la fecha de cierre parecerían abiertas.
becas_apoyos[["estado", "criterio_estado"]] = becas_apoyos.apply(
    scrapers.calcular_estado, axis=1, result_type="expand")
print("\nEstado por entidad:")
print(pd.crosstab(becas_apoyos["entidad"], becas_apoyos["estado"]).to_string())
print("\nRegla usada:")
print(pd.crosstab(becas_apoyos["entidad"], becas_apoyos["criterio_estado"]).to_string())

# Validación: en Atenea se compara el estado calculado con el que publica la entidad.
atenea = becas_apoyos[becas_apoyos["entidad"] == "Agencia Atenea"]
print("\nAtenea: estado calculado (filas) frente a estado publicado (columnas):")
print(pd.crosstab(atenea["estado"], atenea["estado_publicado"]).to_string())

# %% 8. Validación de enlaces
# Un enlace es válido si responde con código HTTP 200 en la fecha de validación.
validacion = scrapers.validar_enlaces(becas_apoyos["enlace"], ACTUALIZAR_DATOS)
becas_apoyos = becas_apoyos.merge(validacion[["enlace", "codigo_http", "fecha_validacion"]], on="enlace", how="left")
becas_apoyos["enlace_valido"] = becas_apoyos["codigo_http"] == 200
print("\nEnlaces válidos por entidad:")
print(becas_apoyos.groupby("entidad")["enlace_valido"].agg(["sum", "count"]).to_string())

# %% 9. Alertas de calidad por registro
# Resumen de lo que un aspirante debería verificar antes de confiar en el registro (scrapers.alertas_de).
becas_apoyos["alertas"] = becas_apoyos.apply(scrapers.alertas_de, axis=1)
print("\nAlertas más frecuentes por entidad:")
print(becas_apoyos.groupby("entidad")["alertas"].value_counts(dropna=False).to_string())

# %% 10. Guardado
becas_apoyos = becas_apoyos[scrapers.COLUMNAS_FINALES]
becas_apoyos.to_csv("results/becas_apoyos.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado results/becas_apoyos.csv ({len(becas_apoyos)} filas)")
