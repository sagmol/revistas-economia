# Decisiones metodologicas

Este archivo documenta el proceso de seleccion de revistas, fuentes y estrategias de extraccion. La idea es que el proyecto sea reproducible y auditable, no una coleccion opaca de scripts.

## Corte institucional

Decision actual: trabajar con revistas UNAM.

Motivo: mantiene coherencia institucional y permite comparar agendas dentro de un mismo ecosistema editorial/universitario.

Incluidas inicialmente:

- Problemas del Desarrollo
- Investigacion Economica
- Estudios Latinoamericanos
- Ola Financiera

Fuera por ahora:

- Denarius, porque no pertenece al eje UNAM y mezclaria otro circuito institucional.
- Ciencia Economica, porque requiere scraper de sitio estatico y no OAI comparable.
- Economia Informa, porque requiere scraper o semilla manual y no OAI comparable.
- Economia UNAM, porque fue localizada en Elsevier/Revistas UNAM, pero no expone OAI-PMH usable para este corte.

## Jerarquia de fuentes

1. OAI-PMH de OJS.
2. Archivo OJS por numeros (`/issue/archive`) solo como respaldo de validacion.
3. Scrapers de sitio estatico quedan fuera del corte inicial.

## Regla practica por revista

| Revista | Fuente inicial | Estrategia |
|---|---|---|
| Investigacion Economica | `https://revistas.unam.mx/index.php/rie` | OAI-PMH |
| Ola Financiera | `https://revistas.unam.mx/index.php/rof` | OAI-PMH |
| Estudios Latinoamericanos | `https://revistas.unam.mx/index.php/rel` | OAI-PMH |
| Problemas del Desarrollo | `https://www.probdes.iiec.unam.mx/index.php/pde` | OAI-PMH |

## Campos minimos del catalogo

Cada articulo debe intentar llegar a estos campos:

- revista
- titulo
- autores
- ano
- volumen/numero
- paginas
- resumen
- palabras clave
- DOI
- URL de articulo
- URL de PDF
- idioma
- tipo de texto

## Filtro documental

OAI etiqueta todos los registros descargados como `info:eu-repo/semantics/article`, incluso cuando el titulo parece indicar presentaciones, editoriales, indices o resenas. Por eso no se excluyen automaticamente registros por `type`.

La primera regla es crear una clasificacion auxiliar:

- `analitico_probable`
- `posible_no_analitico`

Los patrones iniciales de `posible_no_analitico` son: presentacion, editorial, resena, indice, convocatoria, nota, obituario, documentos y agradecimientos. Esta clasificacion se usa para auditar y visualizar, no para borrar datos crudos.

## Año de publicación

Decision: el campo `year` debe representar el año editorial del numero/articulo, no necesariamente el año de `dc:date`.

Motivo: en `Problemas del Desarrollo`, muchos registros historicos tienen `dc:date` como fecha de carga o actualizacion OAI, mientras `source` contiene el año real del volumen/numero. Ejemplo observado: articulos de `Vol. 31 Num. 121 (2000)` aparecian con `dc:date=2009`.

Regla implementada en `scripts/01_normalize.py`:

1. Extraer primero el año desde `source`.
2. Usar `dc:date` solo como respaldo.
3. Guardar tambien `date_oai_year` para auditoria.

## Cobertura de metadatos

Decision: las barras de resumen y materias se etiquetan como cobertura OAI, no como calidad o importancia de la revista.

Motivo: `Problemas del Desarrollo` es la revista dominante del corpus por volumen y profundidad historica, pero expone menos resumentes y materias en OAI que revistas con archivos mas recientes o mejor normalizados. Esa diferencia describe el estado del repositorio/metadatos, no la centralidad de la revista.

Para analisis tematico fino, conviene separar:

- analisis bibliometrico completo: puede usar todos los registros;
- analisis por resumen/palabras clave: debe filtrar a registros con esos campos o complementar metadatos desde paginas/PDF.

## Vocabulario controlado

Decision: las materias (`dc:subject`) se normalizan antes de mostrarse como "temas frecuentes".

Motivo: los metadatos mezclan idiomas, mayusculas, acentos y variantes equivalentes. Ejemplos detectados:

- `América Latina`, `Latin America`, `AMERICA LATINA`
- `México`, `Mexico`
- `Brasil`, `Brazil`
- `financiarización`, `financialization`, `Financialization`

Implementacion:

- `config/subject_aliases.csv` contiene alias manuales editables.
- `scripts/05_normalize_subjects.py` normaliza acentos, mayusculas, puntuacion y aplica alias.
- Se generan `data/processed/article_subjects_normalized.csv`, `data/processed/subjects_normalized.csv` y `docs/data/subjects_normalized.json`.

Regla metodologica: los alias deben ser conservadores. Conceptos muy generales o ambiguos se revisan antes de fusionarse, para no borrar diferencias teoricas relevantes.

## Doble proposito del sitio

Decision: el sitio debe funcionar en dos niveles.

1. Exploracion general de revistas: corpus, cobertura, autores, temas, series temporales y auditoria.
2. Laboratorio de investigacion `wealth and space`: deteccion de articulos candidatos vinculados con riqueza, desigualdad, propiedad, renta, financiarizacion, espacio, territorio, ciudad, vivienda, tierra y desarrollo regional.

Implementacion inicial:

- `config/research_lenses.json` define dimensiones y terminos.
- `scripts/06_wealth_space_lens.py` genera candidatos auditables.
- `docs/data/wealth_space.json` alimenta una seccion especifica del sitio.

Regla: el lente no es clasificacion definitiva. Es una herramienta de descubrimiento para lectura y refinamiento teorico.

## Ejemplo de flujo reproducible

```bash
python scripts/00_fetch_oai.py
python scripts/01_normalize.py
python scripts/02_summary.py
```

Cuando una revista requiera scraper propio, se agrega un script separado, por ejemplo:

```bash
python scripts/fetch_economia_informa_static.py
python scripts/01_normalize.py
python scripts/02_summary.py
```
