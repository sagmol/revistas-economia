"""
05_normalize_subjects.py
========================
Normaliza materias/palabras clave con reglas conservadoras y alias manuales.

Entradas:
  data/processed/article_subjects.csv
  config/subject_aliases.csv

Salidas:
  data/processed/article_subjects_normalized.csv
  data/processed/subjects_normalized.csv
  docs/data/subjects_normalized.json
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "subject_aliases.csv"
PROC = BASE / "data" / "processed"
DOCS_DATA = BASE / "docs" / "data"

DOCS_DATA.mkdir(parents=True, exist_ok=True)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def subject_key(value: str) -> str:
    value = strip_accents(value or "").lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[\.;:,/\\\(\)\[\]¿\?¡!\"'“”‘’]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def title_fallback(value: str) -> str:
    key = subject_key(value)
    if not key:
        return ""
    small_words = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "of", "and", "the"}
    words = []
    for idx, word in enumerate(key.split()):
        if idx > 0 and word in small_words:
            words.append(word)
        elif word.isupper():
            words.append(word)
        else:
            words.append(word.capitalize())
    return " ".join(words)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_aliases() -> dict[str, dict]:
    aliases = {}
    for row in read_csv(CONFIG):
        key = subject_key(row["raw_key"])
        aliases[key] = {
            "normalized_subject": row["normalized_subject"].strip(),
            "category": row.get("category", "").strip() or "manual",
            "keep": row.get("keep", "1").strip() != "0",
        }
    return aliases


def main() -> None:
    aliases = load_aliases()
    rows = read_csv(PROC / "article_subjects.csv")

    normalized_rows = []
    variants: dict[str, Counter] = defaultdict(Counter)
    categories: dict[str, str] = {}
    kept_counts = Counter()

    for row in rows:
        raw = row["subject"]
        key = subject_key(raw)
        alias = aliases.get(key)
        if alias:
            normalized = alias["normalized_subject"]
            category = alias["category"]
            keep = alias["keep"]
        else:
            normalized = title_fallback(raw)
            category = "unmapped"
            keep = True

        if not normalized:
            continue

        normalized_rows.append(
            {
                "article_id": row["article_id"],
                "raw_subject": raw,
                "raw_key": key,
                "normalized_subject": normalized,
                "category": category,
                "keep": "1" if keep else "0",
            }
        )
        variants[normalized][raw] += 1
        categories.setdefault(normalized, category)
        if keep:
            kept_counts[normalized] += 1

    subjects_rows = []
    for subject, count in kept_counts.most_common():
        subject_variants = variants[subject].most_common()
        subjects_rows.append(
            {
                "normalized_subject": subject,
                "category": categories.get(subject, "unmapped"),
                "count": count,
                "variant_count": len(subject_variants),
                "top_variants": " | ".join(f"{raw} ({n})" for raw, n in subject_variants[:8]),
            }
        )

    write_csv(
        PROC / "article_subjects_normalized.csv",
        normalized_rows,
        ["article_id", "raw_subject", "raw_key", "normalized_subject", "category", "keep"],
    )
    write_csv(
        PROC / "subjects_normalized.csv",
        subjects_rows,
        ["normalized_subject", "category", "count", "variant_count", "top_variants"],
    )

    payload = {
        "total_raw_links": len(rows),
        "total_normalized_subjects": len(subjects_rows),
        "top_subjects": subjects_rows[:80],
    }
    (DOCS_DATA / "subjects_normalized.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(PROC / "subjects_normalized.csv")


if __name__ == "__main__":
    main()
