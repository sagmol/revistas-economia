"""
08_transnational_segment_analysis.py
====================================
Analisis descriptivo del segmento de articulos sobre multilatinas,
transnacionales y trasnacionales.

Entradas:
  docs/data/transnational_bibliography.json
  data/texts/transnational/*.txt (si existen localmente)

Salidas:
  docs/data/transnational_analysis.json
  project_docs/TRANSNACIONALES_ANALISIS.md
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
DOCS_DATA = BASE / "docs" / "data"
TEXT_DIR = BASE / "data" / "texts" / "transnational"
REPORT = BASE / "project_docs" / "TRANSNACIONALES_ANALISIS.md"

SOURCE = DOCS_DATA / "transnational_bibliography.json"
OUT = DOCS_DATA / "transnational_analysis.json"


TERM_FAMILIES = {
    "empresas_transnacionales": [
        "transnacional",
        "transnacionales",
        "trasnacional",
        "trasnacionales",
        "transnational corporation",
        "transnational corporations",
        "corporacion transnacional",
        "corporaciones transnacionales",
    ],
    "multilatinas": ["multilatina", "multilatinas"],
    "capital_extranjero": [
        "capital extranjero",
        "foreign capital",
        "inversion extranjera",
        "foreign investment",
        "inversion extranjera directa",
        "ied",
    ],
    "cadenas_valor": [
        "cadena global",
        "cadenas globales",
        "cadena de valor",
        "cadenas de valor",
        "global value chain",
        "global value chains",
    ],
    "extractivismo_mineria": [
        "extractivismo",
        "extractive",
        "mineria",
        "mining",
        "minerales",
        "mineral",
        "recursos naturales",
        "natural resources",
    ],
    "energia_hidrocarburos": [
        "energia",
        "energy",
        "hidrocarburos",
        "hydrocarbon",
        "petroleo",
        "oil",
        "eolica",
        "wind farm",
    ],
    "conflictos_territorio": [
        "conflicto",
        "conflicts",
        "socioambiental",
        "socio-environmental",
        "territorio",
        "territorial",
        "despojo",
        "dispossession",
        "comunidad",
        "communities",
    ],
    "dependencia_periferia": [
        "dependencia",
        "dependency",
        "periferia",
        "periphery",
        "centro-periferia",
        "capitalismo dependiente",
    ],
    "finanzas": [
        "financiarizacion",
        "financialization",
        "financiero",
        "financial",
        "banca",
        "bank",
        "deuda",
        "debt",
    ],
    "trabajo": [
        "trabajo",
        "labor",
        "labour",
        "salarios",
        "wages",
        "sindical",
        "workers",
        "fuerza de trabajo",
    ],
    "agricultura_alimentacion": [
        "agricultura",
        "agriculture",
        "alimentacion",
        "food",
        "semillas",
        "seeds",
        "hambre",
    ],
}

COUNTRIES = [
    "Mexico",
    "Brasil",
    "Brazil",
    "Argentina",
    "Ecuador",
    "Chile",
    "Colombia",
    "Peru",
    "Venezuela",
    "Bolivia",
    "Estados Unidos",
    "United States",
    "South Korea",
    "Corea",
]

STOPWORDS = {
    "para",
    "como",
    "sobre",
    "entre",
    "desde",
    "hasta",
    "contra",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "una",
    "uno",
    "unos",
    "unas",
    "los",
    "las",
    "del",
    "por",
    "con",
    "sin",
    "les",
    "des",
    "dans",
    "development",
    "desarrollo",
    "problemas",
    "revista",
    "mexico",
    "http",
    "https",
    "disponible",
    "recuperado",
    "available",
    "retrieved",
    "consultado",
    "accessed",
}

AUTHOR_EXCLUDE = {
    "Anual",
    "Annual",
    "Mining",
    "Press",
    "Disponible",
    "Recuperado",
    "Available",
    "Retrieved",
    "America",
    "Latin America",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def norm(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def decade(year: str) -> str:
    try:
        n = int(float(year))
    except (TypeError, ValueError):
        return "sin_ano"
    return f"{(n // 10) * 10}s"


def counter_rows(counter: Counter, limit: int | None = None) -> list[dict]:
    rows = [{"name": name, "count": count} for name, count in counter.most_common(limit)]
    return rows


def split_dimensions(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def article_text(article: dict) -> str:
    pdf_path = article.get("pdf_path", "")
    if not pdf_path:
        return ""
    txt_path = TEXT_DIR / f"{Path(pdf_path).stem}.txt"
    if not txt_path.exists():
        return ""
    return txt_path.read_text(encoding="utf-8", errors="replace")


def family_hits(text: str) -> dict[str, int]:
    normalized = norm(text)
    hits = {}
    for family, terms in TERM_FAMILIES.items():
        count = 0
        for term in terms:
            count += normalized.count(norm(term))
        if count:
            hits[family] = count
    return hits


def country_hits(text: str) -> dict[str, int]:
    normalized = norm(text)
    hits = {}
    for country in COUNTRIES:
        count = normalized.count(norm(country))
        if count:
            key = "Mexico" if norm(country) == "mexico" else country
            key = "Brasil" if norm(country) == "brazil" else key
            key = "Estados Unidos" if norm(country) in {"united states", "estados unidos"} else key
            hits[key] = hits.get(key, 0) + count
    return hits


def cited_years(refs: list[str]) -> Counter:
    years = Counter()
    for ref in refs:
        for year in re.findall(r"\b(18|19|20)\d{2}\b", ref):
            # Regex group returns prefix only; use a second pass for whole year.
            pass
        for year in re.findall(r"\b(?:18|19|20)\d{2}\b", ref):
            years[year] += 1
    return years


def normalize_author(raw: str) -> str:
    raw = re.sub(r"\s+", " ", raw).strip(" .;:-")
    raw = re.sub(r"^_+\s*", "", raw)
    raw = raw.replace(" y ", " & ")
    raw = raw.replace(" and ", " & ")
    return raw[:90]


def cited_authors(refs: list[str]) -> Counter:
    authors = Counter()
    for ref in refs:
        before_year = re.split(r"\b(?:18|19|20)\d{2}[a-z]?\b", ref, maxsplit=1)[0]
        before_year = before_year.strip(" .,(;:-")
        if not before_year:
            continue
        parts = re.split(r"\s*&\s*|,\s*y\s+|,\s+and\s+", before_year)
        for part in parts[:3]:
            author = normalize_author(part)
            if len(author) < 3 or len(author.split()) > 8:
                continue
            if author in AUTHOR_EXCLUDE:
                continue
            if norm(author) in {norm(item) for item in AUTHOR_EXCLUDE}:
                continue
            authors[author] += 1
    return authors


def reference_keywords(refs: list[str]) -> Counter:
    words = Counter()
    for ref in refs:
        for word in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", ref):
            w = norm(word)
            if w not in STOPWORDS and len(w) > 3:
                words[w] += 1
    return words


def article_keywords(articles: list[dict], texts: dict[str, str]) -> Counter:
    words = Counter()
    for article in articles:
        text = " ".join(
            [
                article.get("title", ""),
                article.get("matched_terms", ""),
                " ".join(article.get("snippets", [])),
                texts.get(article["article_id"], "")[:50000],
            ]
        )
        for word in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", text):
            w = norm(word)
            if w not in STOPWORDS and len(w) > 3:
                words[w] += 1
    return words


def build_analysis() -> dict:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    articles = data["articles"]
    texts = {article["article_id"]: article_text(article) for article in articles}

    by_journal = Counter(article["journal"] for article in articles)
    by_decade = Counter(decade(article.get("year", "")) for article in articles)
    by_status = Counter(article["status"] for article in articles)
    dimensions = Counter()
    dimension_pairs = Counter()
    families_articles = Counter()
    families_mentions = Counter()
    family_by_journal: dict[str, Counter] = defaultdict(Counter)
    countries = Counter()
    refs_by_journal = Counter()
    all_refs: list[str] = []

    article_summaries = []
    for article in articles:
        dims = split_dimensions(article.get("dimensions", ""))
        dimensions.update(dims)
        dimension_pairs.update(" + ".join(pair) for pair in combinations(sorted(dims), 2))

        combined_text = " ".join(
            [
                article.get("title", ""),
                article.get("matched_terms", ""),
                " ".join(article.get("snippets", [])),
                texts.get(article["article_id"], ""),
            ]
        )
        hits = family_hits(combined_text)
        families_articles.update(hits.keys())
        families_mentions.update(hits)
        for family in hits:
            family_by_journal[family][article["journal"]] += 1
        countries.update(country_hits(combined_text))

        refs = article.get("references", [])
        all_refs.extend(refs)
        refs_by_journal[article["journal"]] += len(refs)
        article_summaries.append(
            {
                "article_id": article["article_id"],
                "title": article["title"],
                "journal": article["journal"],
                "year": article["year"],
                "url": article["url"],
                "score": int(float(article.get("score") or 0)),
                "reference_count": int(article.get("reference_count") or 0),
                "status": article["status"],
                "families": [{"name": name, "count": count} for name, count in sorted(hits.items())],
                "dimensions": dims,
                "snippets": article.get("snippets", [])[:3],
            }
        )

    authors = cited_authors(all_refs)
    years = cited_years(all_refs)
    ref_words = reference_keywords(all_refs)
    text_words = article_keywords(articles, texts)

    top_reference_articles = sorted(article_summaries, key=lambda x: x["reference_count"], reverse=True)[:15]
    top_score_articles = sorted(article_summaries, key=lambda x: x["score"], reverse=True)[:15]

    return {
        "source": "docs/data/transnational_bibliography.json",
        "total_articles": len(articles),
        "articles_with_pdf_text": sum(1 for article in articles if texts.get(article["article_id"])),
        "total_references": len(all_refs),
        "by_journal": counter_rows(by_journal),
        "by_decade": counter_rows(by_decade),
        "by_status": counter_rows(by_status),
        "dimensions": counter_rows(dimensions),
        "dimension_pairs": counter_rows(dimension_pairs, 20),
        "term_families_articles": counter_rows(families_articles),
        "term_families_mentions": counter_rows(families_mentions),
        "term_families_by_journal": {
            family: counter_rows(counter) for family, counter in sorted(family_by_journal.items())
        },
        "countries": counter_rows(countries, 20),
        "references_by_journal": counter_rows(refs_by_journal),
        "cited_authors": counter_rows(authors, 40),
        "cited_years": counter_rows(years, 40),
        "reference_keywords": counter_rows(ref_words, 50),
        "text_keywords": counter_rows(text_words, 50),
        "top_reference_articles": top_reference_articles,
        "top_score_articles": top_score_articles,
        "article_summaries": article_summaries,
        "notes": [
            "El conteo de familias usa coincidencias lexicas en titulo, terminos, fragmentos y texto completo local cuando existe.",
            "Los autores citados se infieren de la parte anterior al primer ano en cada referencia; requiere revision manual.",
            "Los PDFs/textos completos no se publican; solo se publican agregados, metadatos y referencias ya extraidas.",
        ],
    }


def write_report(analysis: dict) -> None:
    md = [
        "# Analisis del segmento: multilatinas y transnacionales",
        "",
        f"Articulos candidatos: {analysis['total_articles']}",
        f"Articulos con texto local extraido: {analysis['articles_with_pdf_text']}",
        f"Referencias extraidas: {analysis['total_references']}",
        "",
        "## Lectura rapida",
        "",
    ]

    def bullet_rows(title: str, rows: list[dict], limit: int = 10) -> None:
        md.extend([f"## {title}", ""])
        for row in rows[:limit]:
            md.append(f"- {row['name']}: {row['count']}")
        md.append("")

    bullet_rows("Revistas", analysis["by_journal"])
    bullet_rows("Decadas", analysis["by_decade"])
    bullet_rows("Familias tematicas por articulos", analysis["term_families_articles"], 12)
    bullet_rows("Dimensiones wealth and space", analysis["dimensions"], 12)
    bullet_rows("Paises/espacios mencionados", analysis["countries"], 12)
    bullet_rows("Autores y fuentes citadas frecuentes", analysis["cited_authors"], 20)
    bullet_rows("Palabras frecuentes en referencias", analysis["reference_keywords"], 20)

    md.extend(["## Articulos con mas bibliografia extraida", ""])
    for item in analysis["top_reference_articles"][:10]:
        md.extend(
            [
                f"### {item['title']}",
                "",
                f"- Revista: {item['journal']}",
                f"- Ano: {item['year']}",
                f"- Referencias: {item['reference_count']}",
                f"- Score: {item['score']}",
                f"- Familias: {', '.join(f['name'] for f in item['families']) or 'sin conteo local'}",
                f"- URL: {item['url']}",
                "",
            ]
        )

    md.extend(["## Notas", ""])
    md.extend(f"- {note}" for note in analysis["notes"])
    md.append("")
    REPORT.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    analysis = build_analysis()
    OUT.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(analysis)
    print(OUT)
    print(REPORT)


if __name__ == "__main__":
    main()
