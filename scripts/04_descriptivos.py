"""
04_descriptivos.py
==================
Genera agregados descriptivos para el sitio estatico.

Salida:
  docs/data/descriptivos.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location


BASE = Path(__file__).resolve().parent.parent
PROC = BASE / "data" / "processed"
DOCS_DATA = BASE / "docs" / "data"
AUDIT_SCRIPT = BASE / "scripts" / "03_auditoria_corpus.py"

DOCS_DATA.mkdir(parents=True, exist_ok=True)


def load_audit_helpers():
    spec = spec_from_file_location("auditoria_corpus", AUDIT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar 03_auditoria_corpus.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify_record


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def decade(year: str) -> str:
    if not year or not year.isdigit():
        return "sin_ano"
    y = int(year)
    return f"{(y // 10) * 10}s"


def pct(n: int, total: int) -> float:
    return round((n / total * 100), 1) if total else 0.0


def main() -> None:
    classify_record = load_audit_helpers()
    articles = read_csv(PROC / "articles.csv")
    article_authors = read_csv(PROC / "article_authors.csv")
    article_subjects = read_csv(PROC / "article_subjects.csv")
    normalized_subjects_path = PROC / "article_subjects_normalized.csv"
    article_subjects_normalized = read_csv(normalized_subjects_path) if normalized_subjects_path.exists() else []

    class_by_article = {}
    for row in articles:
        cls, flags = classify_record(row)
        class_by_article[row["article_id"]] = {"class": cls, "flags": flags}

    by_year_total = Counter()
    by_year_analytic = Counter()
    by_decade_total = Counter()
    by_decade_analytic = Counter()
    by_journal_class: dict[str, Counter] = defaultdict(Counter)
    by_journal_decade: dict[str, Counter] = defaultdict(Counter)

    fields = ["description", "subjects", "relations", "language"]
    coverage_by_journal = defaultdict(lambda: {field: 0 for field in fields} | {"total": 0})
    subject_article_counts = Counter(row["article_id"] for row in article_subjects)

    for row in articles:
        article_id = row["article_id"]
        journal = row["journal_name"]
        cls = class_by_article[article_id]["class"]
        year = row.get("year", "")
        dec = decade(year)

        by_year_total[year] += 1
        by_decade_total[dec] += 1
        by_journal_class[journal][cls] += 1
        by_journal_decade[journal][dec] += 1

        if cls == "analitico_probable":
            by_year_analytic[year] += 1
            by_decade_analytic[dec] += 1

        coverage_by_journal[journal]["total"] += 1
        if row.get("description"):
            coverage_by_journal[journal]["description"] += 1
        if subject_article_counts[article_id] > 0:
            coverage_by_journal[journal]["subjects"] += 1
        if row.get("relations"):
            coverage_by_journal[journal]["relations"] += 1
        if row.get("language"):
            coverage_by_journal[journal]["language"] += 1

    analytic_articles = {
        row["article_id"]
        for row in articles
        if class_by_article[row["article_id"]]["class"] == "analitico_probable"
    }
    top_authors = Counter(
        row["author_name"]
        for row in article_authors
        if row["article_id"] in analytic_articles and row.get("author_name")
    )
    if article_subjects_normalized:
        top_subjects = Counter(
            row["normalized_subject"]
            for row in article_subjects_normalized
            if row["article_id"] in analytic_articles
            and row.get("normalized_subject")
            and row.get("keep", "1") == "1"
        )
    else:
        top_subjects = Counter(
            row["subject"]
            for row in article_subjects
            if row["article_id"] in analytic_articles and row.get("subject")
        )

    years = sorted(y for y in by_year_total if y and y.isdigit())
    decades = sorted(d for d in by_decade_total if d != "sin_ano")

    output = {
        "by_year": [
            {
                "year": year,
                "total": by_year_total[year],
                "analytic_probable": by_year_analytic[year],
            }
            for year in years
        ],
        "by_decade": [
            {
                "decade": dec,
                "total": by_decade_total[dec],
                "analytic_probable": by_decade_analytic[dec],
            }
            for dec in decades
        ],
        "by_journal_class": [
            {
                "journal": journal,
                "analytic_probable": counts["analitico_probable"],
                "possible_non_analytic": counts["posible_no_analitico"],
                "total": sum(counts.values()),
            }
            for journal, counts in sorted(by_journal_class.items())
        ],
        "by_journal_decade": {
            journal: [{"decade": dec, "count": count} for dec, count in sorted(counts.items())]
            for journal, counts in sorted(by_journal_decade.items())
        },
        "coverage_by_journal": [
            {
                "journal": journal,
                "total": stats["total"],
                "description_pct": pct(stats["description"], stats["total"]),
                "subjects_pct": pct(stats["subjects"], stats["total"]),
                "relations_pct": pct(stats["relations"], stats["total"]),
                "language_pct": pct(stats["language"], stats["total"]),
            }
            for journal, stats in sorted(coverage_by_journal.items())
        ],
        "top_authors_analytic": [
            {"author": author, "count": count} for author, count in top_authors.most_common(30)
        ],
        "top_subjects_analytic": [
            {"subject": subject, "count": count} for subject, count in top_subjects.most_common(50)
        ],
        "subjects_are_normalized": bool(article_subjects_normalized),
    }

    out = DOCS_DATA / "descriptivos.json"
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
