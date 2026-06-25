"""
03_auditoria_corpus.py
======================
Audita el corpus normalizado antes de construir visualizaciones analiticas.

Objetivo:
  - Distinguir registros OAI de articulos analiticos probables.
  - Medir cobertura de campos clave.
  - Identificar anos fuera de rango, duplicados y metadatos incompletos.

Salidas:
  data/processed/auditoria_corpus.json
  data/processed/auditoria_corpus.md
  docs/data/auditoria_corpus.json
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
PROC = BASE / "data" / "processed"
DOCS_DATA = BASE / "docs" / "data"

DOCS_DATA.mkdir(parents=True, exist_ok=True)


NON_ANALYTIC_PATTERNS = [
    ("presentacion", r"\bpresentaci[oó]n\b"),
    ("editorial", r"\beditorial\b"),
    ("resena", r"\brese[nñ]a\b|\bbook review\b"),
    ("indice", r"\b[ií]ndice\b|\bindex\b"),
    ("convocatoria", r"\bconvocatoria\b|\bcall for papers\b"),
    ("nota", r"\bnota editorial\b|\bnota\b"),
    ("obituario", r"\bobituario\b|\bin memoriam\b"),
    ("documentos", r"\bdocumentos?\b"),
    ("agradecimientos", r"\bagradecimientos?\b"),
]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def has_value(row: dict, field: str) -> bool:
    return bool((row.get(field) or "").strip())


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def classify_record(row: dict) -> tuple[str, list[str]]:
    title = normalize_text(row.get("title", ""))
    source = normalize_text(row.get("source", ""))
    haystack = f"{title} {source}"
    flags = [label for label, pattern in NON_ANALYTIC_PATTERNS if re.search(pattern, haystack)]
    if flags:
        return "posible_no_analitico", flags
    return "analitico_probable", []


def pct(n: int, total: int) -> float:
    return round((n / total * 100), 1) if total else 0.0


def main() -> None:
    articles = read_csv(PROC / "articles.csv")
    article_authors = read_csv(PROC / "article_authors.csv")
    article_subjects = read_csv(PROC / "article_subjects.csv")

    total = len(articles)
    years = [int(row["year"]) for row in articles if row.get("year") and row["year"].isdigit()]
    by_journal = Counter(row["journal_name"] for row in articles)
    by_journal_year: dict[str, Counter] = defaultdict(Counter)
    classifications = Counter()
    flags = Counter()
    examples: dict[str, list[dict]] = defaultdict(list)

    author_counts = Counter(row["article_id"] for row in article_authors)
    subject_counts = Counter(row["article_id"] for row in article_subjects)

    for row in articles:
        journal = row["journal_name"]
        if row.get("year"):
            by_journal_year[journal][row["year"]] += 1

        cls, cls_flags = classify_record(row)
        classifications[cls] += 1
        for flag in cls_flags:
            flags[flag] += 1
            if len(examples[flag]) < 8:
                examples[flag].append(
                    {
                        "journal": journal,
                        "year": row.get("year", ""),
                        "title": row.get("title", ""),
                        "source": row.get("source", ""),
                    }
                )

    fields = ["title", "year", "description", "relations", "source", "publisher", "language"]
    coverage = {
        field: {
            "count": sum(1 for row in articles if has_value(row, field)),
            "pct": pct(sum(1 for row in articles if has_value(row, field)), total),
        }
        for field in fields
    }
    coverage["authors"] = {
        "count": sum(1 for row in articles if author_counts[row["article_id"]] > 0),
        "pct": pct(sum(1 for row in articles if author_counts[row["article_id"]] > 0), total),
    }
    coverage["subjects"] = {
        "count": sum(1 for row in articles if subject_counts[row["article_id"]] > 0),
        "pct": pct(sum(1 for row in articles if subject_counts[row["article_id"]] > 0), total),
    }

    duplicate_titles = Counter(
        (normalize_text(row["journal_name"]), normalize_text(row["title"]), row.get("year", ""))
        for row in articles
        if row.get("title")
    )
    duplicate_count = sum(1 for count in duplicate_titles.values() if count > 1)

    audit = {
        "total_records": total,
        "journals": [{"journal": k, "count": v} for k, v in by_journal.most_common()],
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "coverage": coverage,
        "classifications": dict(classifications),
        "non_analytic_flags": dict(flags.most_common()),
        "non_analytic_examples": examples,
        "duplicate_title_year_groups": duplicate_count,
        "by_journal_year": {
            journal: [{"year": y, "count": c} for y, c in sorted(counter.items())]
            for journal, counter in sorted(by_journal_year.items())
        },
    }

    json_text = json.dumps(audit, ensure_ascii=False, indent=2)
    (PROC / "auditoria_corpus.json").write_text(json_text, encoding="utf-8")
    (DOCS_DATA / "auditoria_corpus.json").write_text(json_text, encoding="utf-8")

    md = [
        "# Auditoria del corpus",
        "",
        f"Registros OAI normalizados: {total}",
        f"Rango temporal detectado: {audit['year_min']}-{audit['year_max']}",
        "",
        "## Registros por revista",
        "",
        "| Revista | Registros |",
        "|---|---:|",
    ]
    md.extend(f"| {row['journal']} | {row['count']} |" for row in audit["journals"])
    md.extend(
        [
            "",
            "## Cobertura de campos",
            "",
            "| Campo | Registros | Cobertura |",
            "|---|---:|---:|",
        ]
    )
    md.extend(f"| {field} | {stats['count']} | {stats['pct']}% |" for field, stats in coverage.items())
    md.extend(
        [
            "",
            "## Clasificacion heuristica",
            "",
            "| Clase | Registros |",
            "|---|---:|",
        ]
    )
    md.extend(f"| {k} | {v} |" for k, v in classifications.most_common())
    md.extend(
        [
            "",
            "## Posibles registros no analiticos",
            "",
            "| Patron | Registros marcados |",
            "|---|---:|",
        ]
    )
    md.extend(f"| {k} | {v} |" for k, v in flags.most_common())
    md.extend(
        [
            "",
            "## Nota",
            "",
            "La clasificacion es conservadora y heuristica. OAI etiqueta todos los registros como `info:eu-repo/semantics/article`, por lo que los filtros deben revisarse antes de excluir registros definitivamente.",
        ]
    )

    (PROC / "auditoria_corpus.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(PROC / "auditoria_corpus.md")


if __name__ == "__main__":
    main()
