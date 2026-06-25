"""
06_wealth_space_lens.py
=======================
Construye un lente de investigacion para "wealth and space".

El objetivo no es clasificar definitivamente los articulos, sino crear una
lista auditable de candidatos para lectura, con dimensiones y terminos que
explican por que entraron.

Salida:
  docs/data/wealth_space.json
  data/processed/wealth_space_candidates.csv
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "research_lenses.json"
PROC = BASE / "data" / "processed"
DOCS_DATA = BASE / "docs" / "data"
AUDIT_SCRIPT = BASE / "scripts" / "03_auditoria_corpus.py"

DOCS_DATA.mkdir(parents=True, exist_ok=True)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def norm(value: str) -> str:
    value = strip_accents(value or "").lower()
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_audit_classifier():
    spec = spec_from_file_location("auditoria_corpus", AUDIT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar 03_auditoria_corpus.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify_record


def first_url(relations: str) -> str:
    for part in (relations or "").split("|"):
        part = part.strip()
        if part.startswith("http"):
            return part
    return ""


def match_terms(text: str, terms: list[str]) -> list[str]:
    text_norm = norm(text)
    found = []
    for term in terms:
        term_norm = norm(term)
        if not term_norm:
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(term_norm)}(?![a-z0-9])"
        if re.search(pattern, text_norm):
            found.append(term)
    return sorted(set(found), key=lambda x: norm(x))


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    lens = next(item for item in config["lenses"] if item["id"] == "wealth_space")
    dimensions = lens["dimensions"]
    classify_record = load_audit_classifier()

    articles = read_csv(PROC / "articles.csv")
    normalized_subjects = read_csv(PROC / "article_subjects_normalized.csv")
    subjects_by_article: dict[str, list[str]] = defaultdict(list)
    for row in normalized_subjects:
        if row.get("keep", "1") == "1":
            subjects_by_article[row["article_id"]].append(row["normalized_subject"])

    candidates = []
    dimension_counts = Counter()
    term_counts = Counter()
    journal_counts = Counter()
    decade_counts = Counter()

    for row in articles:
        cls, _flags = classify_record(row)
        if cls != "analitico_probable":
            continue

        subjects = subjects_by_article[row["article_id"]]
        searchable = " ".join(
            [
                row.get("title", ""),
                row.get("description", ""),
                row.get("source", ""),
                " ".join(subjects),
            ]
        )

        matched: dict[str, list[str]] = {}
        for dimension, terms in dimensions.items():
            hits = match_terms(searchable, terms)
            if hits:
                matched[dimension] = hits

        spatial_or_resource = any(
            key in matched
            for key in ("space", "land_housing", "extractivism_environment", "conflict_dispossession")
        )
        wealth_or_power = any(
            key in matched
            for key in (
                "wealth",
                "finance",
                "dependency_periphery",
                "global_value_chains_power",
                "conflict_dispossession",
            )
        )
        strong_research_dimension = any(
            key in matched
            for key in (
                "extractivism_environment",
                "conflict_dispossession",
                "dependency_periphery",
                "global_value_chains_power",
            )
        )
        if not ((spatial_or_resource and wealth_or_power and len(matched) >= 2) or strong_research_dimension):
            continue

        score = sum(len(v) for v in matched.values())
        year = row.get("year", "")
        decade = f"{(int(year) // 10) * 10}s" if year.isdigit() else "sin_ano"
        for dimension, hits in matched.items():
            dimension_counts[dimension] += 1
            for hit in hits:
                term_counts[hit] += 1
        journal_counts[row["journal_name"]] += 1
        decade_counts[decade] += 1

        candidates.append(
            {
                "article_id": row["article_id"],
                "journal": row["journal_name"],
                "year": year,
                "title": row.get("title", ""),
                "source": row.get("source", ""),
                "url": first_url(row.get("relations", "")),
                "score": score,
                "dimensions": "; ".join(sorted(matched)),
                "matched_terms": " | ".join(
                    f"{dimension}: {', '.join(hits)}" for dimension, hits in sorted(matched.items())
                ),
                "subjects": " | ".join(subjects[:12]),
            }
        )

    candidates.sort(key=lambda row: (-int(row["score"]), row["journal"], row["year"], row["title"]))

    write_csv(
        PROC / "wealth_space_candidates.csv",
        candidates,
        ["article_id", "journal", "year", "title", "source", "url", "score", "dimensions", "matched_terms", "subjects"],
    )

    payload = {
        "lens": {
            "id": lens["id"],
            "name": lens["name"],
            "description": lens["description"],
        },
        "total_candidates": len(candidates),
        "by_journal": [{"journal": k, "count": v} for k, v in journal_counts.most_common()],
        "by_decade": [{"decade": k, "count": v} for k, v in sorted(decade_counts.items())],
        "dimension_counts": [{"dimension": k, "count": v} for k, v in dimension_counts.most_common()],
        "top_terms": [{"term": k, "count": v} for k, v in term_counts.most_common(30)],
        "examples": candidates[:18],
        "candidates": candidates,
    }
    (DOCS_DATA / "wealth_space.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(DOCS_DATA / "wealth_space.json")


if __name__ == "__main__":
    main()
