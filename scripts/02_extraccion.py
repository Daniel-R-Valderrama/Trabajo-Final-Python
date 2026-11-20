"""Fase 2: extracción y caché.

Si ACTUALIZAR_DATOS = True, vuelve a raspar las tres fuentes y sobrescribe data/raw/.
Si es False, todo se lee de data/raw/ (sin internet).

Entrada: data/raw/<fuente>/ (o las páginas en línea si ACTUALIZAR_DATOS = True).
Salida:  results/extraccion_sin_limpiar.csv (esquema común, sin limpiar)
Se corre desde la raíz del proyecto:  .venv\\Scripts\\python.exe scripts\\02_extraccion.py
"""

# %% Paquetes
import sys

import pandas as pd

sys.path.append(".")  # permite importar utils/ al correr el script desde la raíz del proyecto
from utils import scrapers

# %% Configuración
ACTUALIZAR_DATOS = False

# %% Descarga (solo si se pide actualizar)
if ACTUALIZAR_DATOS:
    scrapers.descargar_uniandes()
    scrapers.descargar_atenea()
    scrapers.descargar_betowa()

# %% Lectura de los insumos crudos al esquema común
uniandes, paginas_descartadas = scrapers.leer_uniandes()
atenea = scrapers.leer_atenea()
betowa = scrapers.leer_betowa()
print("Páginas de Uniandes descartadas (sin sección de cobertura):")
for url in paginas_descartadas:
    print("  ", url)

becas_apoyos = pd.concat([uniandes, atenea, betowa], ignore_index=True)

# %% Resumen: registros por fuente y campos vacíos
print("\nRegistros por entidad y tipo:")
print(becas_apoyos.groupby(["entidad", "tipo"]).size().to_string())
print("\nCampos vacíos (NaN) por entidad:")
print(becas_apoyos.drop(columns="entidad").isna().groupby(becas_apoyos["entidad"]).sum().T.to_string())
print("\nOrigen de los requisitos:")
print(becas_apoyos.groupby("entidad")["requisitos_origen"].value_counts(dropna=False).to_string())

# %% Guardado
becas_apoyos.to_csv("results/extraccion_sin_limpiar.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado results/extraccion_sin_limpiar.csv ({len(becas_apoyos)} filas)")
