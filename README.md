# Revistas Mexicanas de Economia - UNAM

Corpus bibliometrico y sitio estatico para explorar revistas mexicanas de economia publicadas por la UNAM.

Este proyecto toma como modelo el flujo de `banxico-dibm`: ingesta de metadatos, normalizacion relacional, analisis exploratorio y publicacion en `docs/` como sitio estatico.

El sitio tiene un doble proposito:

- exploracion general del campo editorial de revistas economicas UNAM;
- laboratorio de investigacion para el proyecto `wealth and space`.

## Corpus inicial

El primer corte se limita a revistas UNAM:

| Revista | Institucion / plataforma | Estado |
|---|---|---|
| Problemas del Desarrollo | IIEc UNAM / OJS dominio propio | validar OAI; fallback scraper |
| Investigacion Economica | Facultad de Economia UNAM / OJS | endpoint inicial |
| Estudios Latinoamericanos | CELA-FCPyS UNAM / OJS | endpoint inicial |
| Ola Financiera | IIEc + Facultad de Economia UNAM / OJS | endpoint inicial |

`Denarius` queda fuera del corpus inicial porque no pertenece al eje UNAM y su inclusion cambiaria el diseno institucional del proyecto.

Tambien quedan fuera de esta version `Ciencia Economica`, `Economia Informa` y `Economia UNAM`, porque no aportan una fuente OAI-PMH inmediatamente comparable en el corte actual. Se pueden reincorporar despues con scrapers especificos si el proyecto lo requiere.

## Preguntas guia

- Como cambia la agenda tematica de las revistas economicas UNAM por periodo?
- Que autores, instituciones y redes aparecen con mayor centralidad?
- Como se distribuyen los enfoques: desarrollo, economia politica, macroeconomia, finanzas, historia economica, metodologia, politica publica?
- Que dialogos hay entre revistas: autores repetidos, temas compartidos, referencias y vocabulario?
- Como se compara el vocabulario de revistas criticas/plurales con publicaciones mas mainstream?

## Estructura

```text
revistas_economia/
config/
  journals.json              # manifiesto de revistas y endpoints
  subject_aliases.csv        # vocabulario controlado editable
  research_lenses.json       # lentes de investigacion
data/
  raw/                       # respuestas crudas por fuente
  processed/                 # CSV, SQLite y JSON para sitio
docs/
  index.html                 # sitio estatico publicable en GitHub Pages
  wealth_space.html          # explorador del lente de investigacion
  transnational_bibliography.html # explorador de bibliografia extraida
  data/                      # datos livianos para visualizaciones
project_docs/
  DECISIONES.md              # bitacora metodologica
logs/
scripts/
  00_fetch_oai.py            # descarga metadatos OAI-PMH
  01_normalize.py            # normaliza a tablas relacionales
  02_summary.py              # resumen temporal/por revista para docs
  03_auditoria_corpus.py     # auditoria de cobertura y tipos de registro
  04_descriptivos.py         # agregados para visualizaciones descriptivas
  05_normalize_subjects.py   # normaliza materias/keywords con alias
  06_wealth_space_lens.py    # candidatos para investigacion wealth and space
  07_transnational_bibliography.py # extrae PDFs/texto/bibliografia de transnacionales
  08_transnational_segment_analysis.py # analiza el segmento transnacionales/multilatinas
README.md
```

## Orden de ejecucion

```bash
python scripts/00_fetch_oai.py
python scripts/01_normalize.py
python scripts/02_summary.py
python scripts/03_auditoria_corpus.py
python scripts/05_normalize_subjects.py
python scripts/04_descriptivos.py
python scripts/06_wealth_space_lens.py
python scripts/07_transnational_bibliography.py
python scripts/08_transnational_segment_analysis.py
```

Los scripts usan principalmente librerias de la biblioteca estandar de Python para arrancar sin friccion. Mas adelante se pueden agregar `pandas`, `plotly`, `networkx`, `sklearn`, `pdfplumber` y NLP, como en el proyecto Banxico.

## Estado actual

La primera ingesta OAI-PMH produjo 4,901 registros normalizados de cuatro revistas: `Problemas del Desarrollo`, `Investigacion Economica`, `Estudios Latinoamericanos` y `Ola Financiera`. `Economia UNAM` fue localizada, pero no expone OAI usable para este corte. El rango editorial normalizado es 1969-2026.

El resumen vivo esta en `docs/data/summary.json`. La bitacora de avance esta en `project_docs/ESTADO.md`.

La primera auditoria del corpus esta en `data/processed/auditoria_corpus.md` y `docs/data/auditoria_corpus.json`. Los agregados descriptivos para graficos estan en `docs/data/descriptivos.json`.

Los temas frecuentes usan un vocabulario controlado inicial definido en `config/subject_aliases.csv`, con salida en `data/processed/subjects_normalized.csv` y `docs/data/subjects_normalized.json`.

El lente `wealth and space` se define en `config/research_lenses.json` y genera `docs/data/wealth_space.json`.

El explorador dedicado esta en `docs/wealth_space.html` y permite filtrar candidatos por texto, revista, decada y dimension.

La exploracion inicial de multilatinas/transnacionales esta en `docs/transnational_bibliography.html` y usa `docs/data/transnational_bibliography.json`. Incluye una red D3 de topicos anclados y articulos, donde cada paper aparece cerca de su topico dominante.

El analisis detallado de ese segmento se genera con `scripts/08_transnational_segment_analysis.py` y publica agregados en `docs/data/transnational_analysis.json`.

## Notas de diseno

- La primera fuente preferida es OAI-PMH de OJS porque entrega metadatos estructurados y paginables.
- Cuando una revista no exponga OAI o tenga metadatos incompletos, se agregara un scraper especifico y se documentara en `config/journals.json`.
- Las paginas estaticas sin OAI quedan fuera del corte inicial para mantener un corpus comparable y reproducible.
- Los PDFs y texto completo quedan para una fase posterior; primero se estabiliza el catalogo bibliografico.
- El sitio en `docs/` debe funcionar sin backend para poder publicarse via GitHub Pages.
- Cada decision de inclusion, descarte y estrategia de extraccion queda registrada en `project_docs/DECISIONES.md`.

## Fases sugeridas

### Fase 1 - Catalogo

Construir una base unica de articulos, autores, revistas, volumen/numero, fechas, paginas, resumen, palabras clave, DOI y URLs.

### Fase 2 - Analisis descriptivo

Produccion por revista, ano, periodo, tipo de texto, idioma, cobertura de resumen/DOI/PDF y autores mas productivos.

### Fase 3 - Redes y temas

Red de coautoria, autores compartidos entre revistas, clusters tematicos por resumen/titulo y vocabulario por periodo.

### Fase 4 - Texto completo y referencias

Descarga de PDFs, extraccion de texto, bibliografias, autores citados, journals citados y mapa intelectual.
