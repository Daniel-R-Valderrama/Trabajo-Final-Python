# AGENTS.md — reglas para agentes que trabajen en este proyecto

Proyecto: tutorial "Becas y apoyos educativos en Bogotá con web scraping" (Taller de Python, Facultad de Economía, Uniandes).

1. **Lee `data/README.md` y la rúbrica en `Enunciados/` (si está disponible; no se publica en el repositorio) antes de analizar o cambiar algo.**
2. **`Enunciados/` es solo lectura.** `data/raw/` solo la escriben los scripts de extracción; nada procesado va en `data/`.
3. **Usa SOLO el Python de `.venv`** (`.venv\Scripts\python.exe`). Nunca instales paquetes de forma global.
4. **Todo el trabajo lo hace Python.** El análisis aceptado vive en archivos guardados (`scripts/` y `utils/`), no en comandos sueltos de la terminal. Las descargas, la inspección de páginas y el análisis se hacen con código Python, no con curl, grep u otras herramientas de consola.
5. **Las tablas van a `results/` y los gráficos a `figures/`.** Cada archivo generado indica qué script y qué insumo lo produjo.
6. **No inventes datos, columnas ni significados.** Si un campo no se puede extraer, queda como NaN y se documenta. Marca con (inferido) cualquier cosa que deduzcas.
7. **Respeta `robots.txt`** y pon pausas entre solicitudes (`time.sleep`).
8. **Rutas siempre relativas** a la raíz del proyecto.
9. **Código explícito y legible:** comentarios en español, sin celdas de prueba ni imports sin uso.
10. **Trabaja por fases** y detente al final de cada una para esperar la aprobación del equipo.
11. **Antes de cada comando que necesite aprobación**, explica en una o dos frases en español qué hace, qué archivos lee y qué crea, cambia o borra. Un comando a la vez.
12. **Al terminar una tarea, resume qué cambió.** No pegues archivos completos en el chat.
