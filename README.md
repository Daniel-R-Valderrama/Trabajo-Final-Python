# Tutorial: becas y apoyos educativos en Bogotá con web scraping

Trabajo final del Taller de Python (Facultad de Economía, Universidad de los Andes).

**Integrantes:** Daniel Eduardo Ramírez Hoyos (202626865) y Daniel Ricardo Valderrama Celis (20213250).

**Pregunta:** ¿En qué se diferencian y en qué se complementan los apoyos de una entidad pública que financia estudios en varias instituciones (Agencia Atenea) y los de universidades privadas que financian sus propios programas (Universidad de los Andes y Pontificia Universidad Javeriana)? La comparación se hace según el nivel y el área que quiere estudiar un joven en Bogotá: el tipo de ayuda que ofrecen y qué parte de la matrícula cubren (noviembre de 2026).

## Estructura

| Ruta | Contenido |
|---|---|
| `tutorial.ipynb` | **Entregable.** Tutorial completo: fuentes, extracción, limpieza, análisis, app, limitaciones y conclusiones. |
| `app.py` | App de Streamlit: portada con los hallazgos del tutorial y búsqueda guiada por nivel y área; lee solo archivos de `results/` y oculta las convocatorias vencidas. |
| `utils/scrapers.py` | Funciones auxiliares: extracción de las tres fuentes, reglas de clasificación (Atenea y Javeriana), áreas del SNIES, limpieza de fechas, estado, validación de enlaces y ficha por línea de apoyo. |
| `scripts/` | Scripts de desarrollo numerados (`01_` a `04_`), con celdas `# %%`. El tutorial reúne su contenido. |
| `data/raw/` | Copias crudas (HTML comprimido, PDF y JSON) del 2026-11-18 (Atenea), del 2026-11-22 (Uniandes) y del 2026-11-27 (Javeriana), con un `manifiesto.csv` por fuente. |
| `data/README.md` | Descripción de cada fuente, del esquema y de las decisiones de limpieza y clasificación. |
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

En Jupyter: *Kernel → Restart Kernel and Run All Cells*. Con `ACTUALIZAR_DATOS = False` (valor por defecto), todo se lee de `data/raw/` y `results/`, sin internet; tarda menos de un minuto. Con `True` vuelve a raspar las tres fuentes y a validar los enlaces (unos 10 minutos), y sobrescribe las copias.

Para ejecutarlo de principio a fin sin abrir Jupyter:

```powershell
.venv\Scripts\jupyter.exe nbconvert --to notebook --execute --inplace tutorial.ipynb
```

### App de Streamlit

```powershell
.venv\Scripts\streamlit.exe run app.py
```

Se abre en http://localhost:8501 y se cierra con Ctrl+C en la terminal.

- Muestra exactamente la tabla que deja el tutorial (`results/becas_apoyos.csv`); no raspa nada ni necesita internet.
- **Datos más recientes:** en el tutorial se pone `ACTUALIZAR_DATOS = True`, se da *Run All* (unos 10 minutos, con internet) y se vuelve a cargar la app.
- Portada con los hallazgos del tutorial (`results/hallazgos.csv`, sección 9).
- Búsqueda guiada por nivel y área de conocimiento (SNIES), con buscador por texto (no distingue tildes ni mayúsculas), filtros por entidad, tipo de ayuda, tipo de estudiante, estado y porcentaje mínimo de la matrícula, y orden por fecha de cierre, porcentaje o tipo de ayuda.
- Tarjetas con a quién va dirigido cada apoyo, qué cubre, la descripción completa, las fechas y el enlace oficial; no muestra las convocatorias vencidas.
- Líneas de apoyo de Atenea que se repiten (`results/tabla_lineas_apoyo.csv`, sección 8), para saber qué buscar cuando una convocatoria ya cerró. El tema visual está en `.streamlit/config.toml`.

## Contenido del .zip

Se comprime la carpeta del proyecto **sin** `.venv/`, `__pycache__/` ni `.ipynb_checkpoints/`. Quien lo reciba crea su propio entorno con las instrucciones de instalación.

## Procedencia de las salidas

| Archivo | Lo genera | Insumo |
|---|---|---|
| `results/reconocimiento_fuentes.csv` | `scripts/01_reconocimiento_fuentes.py` | Consulta en línea a las páginas de Uniandes, Atenea, SICORE y Betowa (2026-11-18). El SENA (Betowa) se revisó, pero quedó fuera de la pregunta. La Javeriana se revisó el 2026-11-27 con sus páginas guardadas (tutorial, sección 2). |
| `data/raw/<fuente>/` (HTML, PDF, JSON y `manifiesto.csv`) | `tutorial.ipynb` o `scripts/02_extraccion.py` con `ACTUALIZAR_DATOS = True` (funciones `descargar_*`) | Páginas en línea de Atenea (2026-11-18), catálogo JSON y fichas de Uniandes (2026-11-22) y páginas de becas de la Javeriana (2026-11-27) |
| `results/extraccion_sin_limpiar.csv` | `tutorial.ipynb` (sección 3) o `scripts/02_extraccion.py` | `data/raw/` |
| `results/validacion_enlaces.csv` | `tutorial.ipynb` o `scripts/03_limpieza_validacion.py` (función `validar_enlaces`; con `ACTUALIZAR_DATOS = False` solo visita los enlaces que falten) | Enlaces de la extracción visitados en línea (2026-11-18; los nuevos de Uniandes, 2026-11-26; los de la Javeriana, 2026-11-27) |
| `results/becas_apoyos.csv` | `tutorial.ipynb` (sección 4) o `scripts/03_limpieza_validacion.py` | `results/extraccion_sin_limpiar.csv` y `results/validacion_enlaces.csv` |
| `results/tabla_nivel.csv`, `results/tabla_instrumento.csv`, `results/tabla_porcentaje_matricula.csv`, `results/tabla_nivel_instrumento.csv`, `results/tabla_area.csv`, `results/tabla_area_nivel.csv`, `results/tabla_alcance_programas.csv`, `results/tabla_apoyos_por_programa.csv` | `tutorial.ipynb` (sección 5) o `scripts/04_analisis.py` | `results/becas_apoyos.csv` (y el catálogo de programas de Uniandes en `data/raw/uniandes/`) |
| `results/tabla_lineas_apoyo.csv`, `results/tabla_efecto_lineas.csv`, `results/guia_por_perfil.csv`, `results/hallazgos.csv` (sección 9) | `tutorial.ipynb` (sección 8, mejora sugerida por la IA) o `scripts/04_analisis.py` | `results/becas_apoyos.csv` |
| `figures/nivel_por_entidad.png`, `figures/instrumento_por_entidad.png`, `figures/porcentaje_matricula.png`, `figures/nivel_instrumento.png`, `figures/area_por_entidad.png`, `figures/area_nivel.png` (cada una lo indica en su pie) | `tutorial.ipynb` (sección 5) o `scripts/04_analisis.py` | `results/becas_apoyos.csv` |
| App web | `app.py` (Streamlit) | `results/becas_apoyos.csv`, `results/hallazgos.csv` y `results/tabla_lineas_apoyo.csv` |
