"""
01_normalize.py
===============
Normaliza metadatos OAI-PMH descargados a CSV y SQLite.

Salidas:
  data/processed/articles.csv
  data/processed/authors.csv
  data/processed/article_authors.csv
  data/processed/subjects.csv
  data/processed/article_subjects.csv
  data/processed/revistas_economia.sqlite
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
RAW_OAI = BASE / "data" / "raw" / "oai"
OUT = BASE / "data" / "processed"

OUT.mkdir(parents=True, exist_ok=True)


def first(values: list[str]) -> str:
    return values[0].strip() if values else ""


def best_description(values: list[str]) -> str:
    """Elige el resumen mas sustantivo; OJS a veces pone avisos de idioma primero."""
    boilerplate = {
        "spanish only.",
        "espagnol seulement.",
        "somente em espanhol.",
        "english only.",
        "anglais seulement.",
        "somente em ingles.",
    }
    candidates = []
    for value in values:
        clean = normalize_space(value)
        if not clean:
            continue
        if clean.lower() in boilerplate:
            continue
        candidates.append(clean)
    if not candidates:
        return ""
    return max(candidates, key=len)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def slug_id(*parts: str) -> str:
    raw = "||".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def extract_year(values: list[str]) -> int | None:
    for value in values:
        match = re.search(r"(19|20)\d{2}", value or "")
        if match:
            return int(match.group(0))
    return None


def extract_publication_year(record: dict) -> int | None:
    """Prefiere el año editorial en source; dc:date suele ser carga OAI."""
    source_year = extract_year(record.get("source", []))
    if source_year:
        return source_year
    return extract_year(record.get("dates", []))


def read_payloads() -> list[dict]:
    payloads = []
    for path in sorted(RAW_OAI.glob("*.json")):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    articles: list[dict] = []
    authors_by_name: dict[str, dict] = {}
    article_authors: list[dict] = []
    subjects_by_name: dict[str, dict] = {}
    article_subjects: list[dict] = []

    for payload in read_payloads():
        journal = payload["journal"]
        journal_id = journal["id"]

        for record in payload["records"]:
            oai_identifier = record.get("identifier", "")
            title = normalize_space(first(record.get("titles", [])))
            year = extract_publication_year(record)
            article_id = slug_id(journal_id, oai_identifier or title)

            article = {
                "article_id": article_id,
                "journal_id": journal_id,
                "journal_name": journal["name"],
                "oai_identifier": oai_identifier,
                "datestamp": record.get("datestamp", ""),
                "title": title,
                "year": year or "",
                "date_oai_year": extract_year(record.get("dates", [])) or "",
                "date_raw": "; ".join(record.get("dates", [])),
                "type": first(record.get("types", [])),
                "language": first(record.get("languages", [])),
                "source": first(record.get("source", [])),
                "description": best_description(record.get("descriptions", [])),
                "publisher": first(record.get("publishers", [])),
                "relations": " | ".join(record.get("relations", [])),
                "rights": " | ".join(record.get("rights", [])),
            }
            articles.append(article)

            for position, creator in enumerate(record.get("creators", []), start=1):
                name = normalize_space(creator)
                if not name:
                    continue
                author_id = slug_id(name.lower())
                authors_by_name.setdefault(author_id, {"author_id": author_id, "name": name})
                article_authors.append(
                    {
                        "article_id": article_id,
                        "author_id": author_id,
                        "author_name": name,
                        "position": position,
                    }
                )

            for subject in record.get("subjects", []):
                label = normalize_space(subject)
                if not label:
                    continue
                subject_id = slug_id(label.lower())
                subjects_by_name.setdefault(subject_id, {"subject_id": subject_id, "subject": label})
                article_subjects.append(
                    {
                        "article_id": article_id,
                        "subject_id": subject_id,
                        "subject": label,
                    }
                )

    authors = sorted(authors_by_name.values(), key=lambda row: row["name"].lower())
    subjects = sorted(subjects_by_name.values(), key=lambda row: row["subject"].lower())

    write_csv(
        OUT / "articles.csv",
        articles,
        [
            "article_id",
            "journal_id",
            "journal_name",
            "oai_identifier",
            "datestamp",
            "title",
            "year",
            "date_oai_year",
            "date_raw",
            "type",
            "language",
            "source",
            "description",
            "publisher",
            "relations",
            "rights",
        ],
    )
    write_csv(OUT / "authors.csv", authors, ["author_id", "name"])
    write_csv(OUT / "article_authors.csv", article_authors, ["article_id", "author_id", "author_name", "position"])
    write_csv(OUT / "subjects.csv", subjects, ["subject_id", "subject"])
    write_csv(OUT / "article_subjects.csv", article_subjects, ["article_id", "subject_id", "subject"])

    db_path = OUT / "revistas_economia.sqlite"
    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as conn:
        for table, rows in {
            "articles": articles,
            "authors": authors,
            "article_authors": article_authors,
            "subjects": subjects,
            "article_subjects": article_subjects,
        }.items():
            if not rows:
                continue
            columns = list(rows[0].keys())
            conn.execute(f"CREATE TABLE {table} ({', '.join(col + ' TEXT' for col in columns)})")
            placeholders = ", ".join("?" for _ in columns)
            conn.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                [[row.get(col, "") for col in columns] for row in rows],
            )

    print(f"Articulos: {len(articles)}")
    print(f"Autores: {len(authors)}")
    print(f"Materias: {len(subjects)}")
    print(f"SQLite: {db_path}")


if __name__ == "__main__":
    main()
