"""Fase 2: extracción y caché.

Si ACTUALIZAR_DATOS = True, vuelve a raspar las dos fuentes y sobrescribe data/raw/.
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

# %% Lectura de los insumos crudos al esquema común
becas_apoyos = pd.concat([scrapers.leer_uniandes(), scrapers.leer_atenea()], ignore_index=True)

# %% Resumen: registros por fuente, origen de la clasificación y campos vacíos
print("\nRegistros por entidad y origen de nivel, instrumento y área:")
print(becas_apoyos.groupby(["entidad", "origen_clasificacion"]).size().to_string())
print("\nCampos vacíos (NaN) por entidad:")
print(becas_apoyos.drop(columns="entidad").isna().groupby(becas_apoyos["entidad"]).sum().T.to_string())

# %% Guardado
becas_apoyos.to_csv("results/extraccion_sin_limpiar.csv", index=False, encoding="utf-8-sig")
print(f"\nGuardado results/extraccion_sin_limpiar.csv ({len(becas_apoyos)} filas)")
