# Estado del proyecto

Actualizado: 2026-06-23.

## Avance actual

Ya existe una primera ingesta real por OAI-PMH para cuatro revistas:

| Revista | Registros OAI descargados |
|---|---:|
| Problemas del Desarrollo | 3107 |
| Estudios Latinoamericanos | 839 |
| Investigacion Economica | 497 |
| Ola Financiera | 458 |

`Economia UNAM` fue localizada despues en Elsevier y en `https://www.revistas.unam.mx/index.php/ecu/issue/archive`, pero no queda en el corte OAI: `/ecu/oai` devuelve 404 y el archivo respondio 403 al acceso automatizado.

Total normalizado:

- Articulos/registros: 4901
- Autores unicos: 3403
- Materias/palabras clave unicas: 9180
- Rango temporal detectado: 1969-2026

Auditoria inicial:

- Registros analiticos probables: 4612
- Posibles no analiticos: 289
- Cobertura de resumen/descripcion: 61.4%
- Cobertura de materias/palabras clave: 48.4%
- Cobertura de links/relaciones: 99.5%

Nota sobre `Problemas del Desarrollo`: concentra 3107 de 4901 registros y es la revista dominante del corpus, pero su cobertura OAI de resumen y materias es baja frente a otras revistas. Esto refleja metadatos incompletos en el repositorio, especialmente por archivo historico, no menor importancia.

Archivos generados:

- `data/raw/oai/problemas_desarrollo.json`
- `data/raw/oai/investigacion_economica.json`
- `data/raw/oai/estudios_latinoamericanos.json`
- `data/raw/oai/ola_financiera.json`
- `data/processed/articles.csv`
- `data/processed/authors.csv`
- `data/processed/article_authors.csv`
- `data/processed/subjects.csv`
- `data/processed/article_subjects.csv`
- `data/processed/revistas_economia.sqlite`
- `docs/data/summary.json`
- `data/processed/auditoria_corpus.md`
- `data/processed/auditoria_corpus.json`
- `docs/data/auditoria_corpus.json`
- `docs/data/descriptivos.json`
- `data/processed/article_subjects_normalized.csv`
- `data/processed/subjects_normalized.csv`
- `docs/data/subjects_normalized.json`
- `data/processed/wealth_space_candidates.csv`
- `docs/data/wealth_space.json`

## Sitio

`docs/index.html` ya muestra:

- metricas principales del corpus
- registros por revista
- auditoria documental
- evolucion anual total vs analiticos probables
- produccion por decada
- autores frecuentes
- cobertura de metadatos por revista
- temas frecuentes
- temas frecuentes normalizados con alias español/ingles
- lente de investigacion `wealth and space` con candidatos, dimensiones, terminos y ejemplos
- explorador de bibliografia para articulos que mencionan multilatinas/transnacionales

`docs/wealth_space.html` agrega un explorador dedicado con filtros por busqueda textual, revista, decada y dimension.

`docs/transnational_bibliography.html` agrega una primera exploracion de bibliografia extraida de PDFs disponibles para articulos que mencionan multilatinas, transnacionales o trasnacionales.

`docs/data/transnational_analysis.json` agrega una capa analitica del segmento: revistas, decadas, familias tematicas, dimensiones, paises/espacios, autores citados, palabras en referencias y articulos pivote.

## Revistas excluidas del corte inicial

| Revista | Estado | Proximo paso |
|---|---|---|
| Ciencia Economica | fuera por ahora | reincorporar solo si se decide escribir scraper |
| Economia Informa | fuera por ahora | reincorporar solo si se decide escribir scraper o semilla manual |
| Economia UNAM | fuera por ahora | reincorporar solo si se decide escribir scraper de Elsevier/archivo |

## Nota metodologica

Los conteos OAI son registros bibliograficos tal como los expone cada plataforma. La siguiente fase debe revisar si esos registros incluyen articulos, resenas, editoriales, indices u otros tipos de texto, y luego decidir filtros por tipo documental.

La primera auditoria muestra que OAI etiqueta todos los registros como `info:eu-repo/semantics/article`; por eso el filtro documental requiere heuristicas sobre titulo/fuente y revision cualitativa antes de excluir registros.

La serie anual fue corregida para preferir el año editorial en `source` antes que `dc:date`, porque `dc:date` puede registrar carga o actualizacion OAI. Se conserva `date_oai_year` para auditoria.

Los temas frecuentes usan un vocabulario controlado inicial. Ya se consolidan variantes como `América Latina/Latin America`, `México/Mexico`, `Brasil/Brazil` y `financiarización/financialization`.

El lente `wealth and space` identifica 911 articulos candidatos despues de ampliar el vocabulario hacia dependencia, cadenas globales, extractivismo, conflictos socioambientales, mineria y empresas transnacionales. La lista es amplia y debe leerse como herramienta exploratoria, no como corpus final.
