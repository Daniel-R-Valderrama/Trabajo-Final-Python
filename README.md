# Tutorial: becas y apoyos educativos en Bogotá con web scraping

Trabajo final del Taller de Python (Facultad de Economía, Universidad de los Andes).

**Integrantes:** Daniel Eduardo Ramírez Hoyos (202626865) y Daniel Ricardo Valderrama Celis (20213250).

**Pregunta:** ¿Cómo se comparan las becas y apoyos educativos publicados por la Universidad de los Andes, la Agencia Atenea y el SENA, a la fecha de extracción, en cobertura, requisitos y vigencia de sus convocatorias?

## Estructura

| Ruta | Contenido |
|---|---|
| `tutorial.ipynb` | **Entregable.** Tutorial completo: fuentes, extracción, limpieza, análisis, app, limitaciones y conclusiones. |
| `app.py` | App de Streamlit; lee `results/becas_apoyos.csv`. |
| `utils/scrapers.py` | Funciones auxiliares: extracción, limpieza de fechas, estado y validación de enlaces. |
| `scripts/` | Scripts de desarrollo numerados (`01_` a `04_`), con celdas `# %%`. El tutorial reúne su contenido. |
| `data/raw/` | Copias crudas (HTML comprimido y PDF) del 2026-11-18, con un `manifiesto.csv` por fuente. |
| `data/README.md` | Descripción de cada fuente, del esquema y de las decisiones de limpieza. |
| `results/` | Tablas generadas. |
| `figures/` | Gráficos generados. |
| `requirements.txt` | Paquetes con versiones fijas. |
| `Enunciados/` | PDF del curso (solo lectura). No se publica en el repositorio. |

## Instalación (Windows, PowerShell)

Requiere Python 3.11 y Git. Descarga el proyecto y crea el entorno:

```powershell
git clone https://github.com/Daniel-R-Valderrama/Trabajo-Final-Python.git
cd Trabajo-Final-Python
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

También se puede descargar como .zip desde el botón *Code → Download ZIP* de GitHub. En macOS o Linux, los ejecutables del entorno están en `.venv/bin/` en lugar de `.venv\Scripts\`.

## Ejecución

### Tutorial

```powershell
.venv\Scripts\jupyter.exe notebook tutorial.ipynb
```

En Jupyter: *Kernel → Restart Kernel and Run All Cells*. Con `ACTUALIZAR_DATOS = False` (valor por defecto), todo se lee de `data/raw/` y `results/`, sin internet; tarda menos de un minuto. Con `True` vuelve a raspar las fuentes y a validar los enlaces (unos 25 minutos), y sobrescribe las copias.

Para ejecutarlo de principio a fin sin abrir Jupyter:

```powershell
.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace tutorial.ipynb
```

### App de Streamlit

La app solo lee `results/becas_apoyos.csv`, sin internet y sin raspar nada:

```powershell
.venv\Scripts\streamlit.exe run app.py
```

Se abre en http://localhost:8501. Tiene un buscador por texto (no distingue tildes ni mayúsculas) y filtros por entidad, tipo y estado. "Solo abiertas" viene activado por defecto. Se cierra con Ctrl+C en la terminal.

## Contenido del .zip

Se comprime la carpeta del proyecto **sin** `.venv/`, `__pycache__/` ni `.ipynb_checkpoints/`. Quien lo reciba crea su propio entorno con las instrucciones de instalación.

## Procedencia de las salidas

| Archivo | Lo genera | Insumo |
|---|---|---|
| `results/reconocimiento_fuentes.csv` | `scripts/01_reconocimiento_fuentes.py` | Consulta en línea a las páginas de Uniandes, Atenea, SICORE y Betowa (2026-11-18) |
| `data/raw/<fuente>/` (HTML, PDF y `manifiesto.csv`) | `tutorial.ipynb` o `scripts/02_extraccion.py` con `ACTUALIZAR_DATOS = True` (funciones `descargar_*`) | Páginas en línea de Uniandes, Atenea y Betowa (2026-11-18) |
| `results/extraccion_sin_limpiar.csv` | `tutorial.ipynb` (sección 3) o `scripts/02_extraccion.py` | `data/raw/` |
| `results/validacion_enlaces.csv` | `tutorial.ipynb` o `scripts/03_limpieza_validacion.py` con `ACTUALIZAR_DATOS = True` (función `validar_enlaces`) | Enlaces de la extracción visitados en línea (2026-11-18) |
| `results/becas_apoyos.csv` | `tutorial.ipynb` (sección 4) o `scripts/03_limpieza_validacion.py` | `results/extraccion_sin_limpiar.csv` y `results/validacion_enlaces.csv` |
| `results/tabla_vigencia.csv`, `results/tabla_convocatorias_vigentes.csv`, `results/tabla_cobertura.csv`, `results/tabla_requisitos.csv` | `tutorial.ipynb` (sección 5) o `scripts/04_analisis.py` | `results/becas_apoyos.csv` |
| `figures/estado_por_entidad.png`, `figures/dias_para_cierre.png`, `figures/cobertura_por_entidad.png`, `figures/requisitos_por_entidad.png` (cada una lo indica en su pie) | `tutorial.ipynb` (sección 5) o `scripts/04_analisis.py` | `results/becas_apoyos.csv` |
| App web | `app.py` (Streamlit) | `results/becas_apoyos.csv` |
