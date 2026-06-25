"""
02_summary.py
=============
Genera datos livianos para el sitio estatico en docs/.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
PROC = BASE / "data" / "processed"
DOCS_DATA = BASE / "docs" / "data"

DOCS_DATA.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    articles = read_csv(PROC / "articles.csv")
    article_authors = read_csv(PROC / "article_authors.csv")
    subjects = read_csv(PROC / "article_subjects.csv")

    by_journal = Counter(row["journal_name"] for row in articles)
    by_year = Counter(row["year"] for row in articles if row.get("year"))
    by_journal_year: dict[str, Counter] = defaultdict(Counter)
    for row in articles:
        if row.get("year"):
            by_journal_year[row["journal_name"]][row["year"]] += 1

    author_counts = Counter(row["author_name"] for row in article_authors)
    subject_counts = Counter(row["subject"] for row in subjects)

    summary = {
        "total_articles": len(articles),
        "total_authors": len({row["author_id"] for row in article_authors}),
        "total_subjects": len({row["subject_id"] for row in subjects}),
        "by_journal": [{"journal": k, "count": v} for k, v in by_journal.most_common()],
        "by_year": [{"year": k, "count": v} for k, v in sorted(by_year.items())],
        "by_journal_year": {
            journal: [{"year": y, "count": c} for y, c in sorted(counter.items())]
            for journal, counter in sorted(by_journal_year.items())
        },
        "top_authors": [{"author": k, "count": v} for k, v in author_counts.most_common(25)],
        "top_subjects": [{"subject": k, "count": v} for k, v in subject_counts.most_common(40)],
    }

    (DOCS_DATA / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(DOCS_DATA / "summary.json")


if __name__ == "__main__":
    main()
