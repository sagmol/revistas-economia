"""
07_transnational_bibliography.py
================================
Extrae texto y bibliografia de articulos que usan el campo semantico de
multilatinas, transnacionales y trasnacionales.

Entradas:
  data/processed/wealth_space_candidates.csv

Salidas:
  data/processed/transnational_bibliography.csv
  docs/data/transnational_bibliography.json
  project_docs/TRANSNACIONALES_BIBLIOGRAFIA.md

Los PDFs descargados se guardan en data/pdfs/transnational/.
"""

from __future__ import annotations

import csv
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pdfplumber


BASE = Path(__file__).resolve().parent.parent
PROC = BASE / "data" / "processed"
DOCS_DATA = BASE / "docs" / "data"
PDF_DIR = BASE / "data" / "pdfs" / "transnational"
TEXT_DIR = BASE / "data" / "texts" / "transnational"
REPORT = BASE / "project_docs" / "TRANSNACIONALES_BIBLIOGRAFIA.md"

PDF_DIR.mkdir(parents=True, exist_ok=True)
TEXT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DATA.mkdir(parents=True, exist_ok=True)

TERMS = [
    "multilatinas",
    "transnacionales",
    "trasnacionales",
    "transnacional",
    "trasnacional",
    "empresas transnacionales",
    "empresas trasnacionales",
    "empresa transnacional",
    "empresa trasnacional",
    "corporaciones transnacionales",
    "corporaciones trasnacionales",
    "capital transnacional",
    "capital trasnacional",
    "transnational corporations",
]

REFERENCE_HEADINGS = [
    "bibliografia",
    "bibliography",
    "referencias",
    "references",
    "referencias bibliograficas",
    "bibliographic references",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(html.unescape(href))


def strip_accents(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def norm(value: str) -> str:
    value = strip_accents(value or "").lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def matches_transnational(row: dict) -> bool:
    haystack = norm(" ".join([row.get("title", ""), row.get("matched_terms", ""), row.get("subjects", "")]))
    return any(norm(term) in haystack for term in TERMS)


def article_slug(row: dict) -> str:
    raw = row.get("article_id") or row.get("url") or row.get("title")
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def fetch_url(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read(), response.headers.get("content-type", "")


def find_pdf_link(page_url: str, html_bytes: bytes) -> str | None:
    from urllib.parse import urljoin

    text = html_bytes.decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(text)
    candidates = []
    for href in parser.links:
        low = href.lower()
        if "article/download" in low or "/download/" in low or "download" in low or ".pdf" in low:
            candidates.append(urljoin(page_url, href))
    if candidates:
        candidates.sort(key=lambda u: (0 if "article/download" in u.lower() else 1, len(u)))
        return candidates[0]
    return None


def download_pdf(row: dict) -> Path | None:
    url = row.get("url", "").strip()
    if not url:
        return None
    out = PDF_DIR / f"{article_slug(row)}.pdf"
    if out.exists() and out.stat().st_size > 1000:
        return out

    try:
        data, content_type = fetch_url(url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"WARN download failed: {url} :: {exc}", file=sys.stderr)
        return None

    if not data.startswith(b"%PDF"):
        pdf_url = find_pdf_link(url, data)
        if not pdf_url:
            print(f"WARN no PDF link found: {url} ({content_type})", file=sys.stderr)
            return None
        try:
            data, content_type = fetch_url(pdf_url)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"WARN PDF link failed: {pdf_url} :: {exc}", file=sys.stderr)
            return None
        if not data.startswith(b"%PDF"):
            print(f"WARN linked response is not PDF: {pdf_url} ({content_type})", file=sys.stderr)
            return None

    out.write_bytes(data)
    time.sleep(0.3)
    return out


def extract_text(pdf_path: Path) -> str:
    txt_path = TEXT_DIR / f"{pdf_path.stem}.txt"
    if txt_path.exists() and txt_path.stat().st_size > 1000:
        return txt_path.read_text(encoding="utf-8", errors="replace")

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    text = "\n\n".join(pages)
    txt_path.write_text(text, encoding="utf-8")
    return text


def find_references_block(text: str) -> str:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        clean = norm(line).strip(" .:-")
        if clean in REFERENCE_HEADINGS:
            start = i + 1
    if start is None:
        return ""
    return "\n".join(lines[start:]).strip()


def split_references(block: str) -> list[str]:
    if not block:
        return []
    raw_lines = [re.sub(r"\s+", " ", line).strip() for line in block.splitlines()]
    raw_lines = [line for line in raw_lines if line]

    refs = []
    current = ""
    for line in raw_lines:
        starts_ref = bool(re.search(r"\b(18|19|20)\d{2}[a-z]?\b", line)) and (
            bool(re.match(r"^[A-ZÁÉÍÓÚÑÄËÏÖÜ][^,]{1,80},", line))
            or bool(re.match(r"^[A-ZÁÉÍÓÚÑÄËÏÖÜ][A-Za-zÁÉÍÓÚÑáéíóúñü\.-]+", line))
        )
        if starts_ref and current:
            refs.append(current.strip())
            current = line
        else:
            current = f"{current} {line}".strip() if current else line
    if current:
        refs.append(current.strip())

    cleaned = []
    for ref in refs:
        if len(ref) < 25:
            continue
        if re.search(r"\b(18|19|20)\d{2}[a-z]?\b", ref) or "doi" in ref.lower() or "http" in ref.lower():
            cleaned.append(ref)
    return cleaned[:120]


def context_snippets(text: str, terms: list[str], radius: int = 180) -> list[str]:
    text_one_line = re.sub(r"\s+", " ", text)
    text_norm = norm(text_one_line)
    snippets = []
    for term in terms:
        term_norm = norm(term)
        idx = text_norm.find(term_norm)
        if idx < 0:
            continue
        start = max(0, idx - radius)
        end = min(len(text_one_line), idx + len(term) + radius)
        snippets.append(text_one_line[start:end].strip())
    return snippets[:4]


def main() -> None:
    candidates = [row for row in read_csv(PROC / "wealth_space_candidates.csv") if matches_transnational(row)]
    rows = []
    examples = []
    total_refs = 0
    downloaded = 0

    for idx, row in enumerate(candidates, start=1):
        pdf_path = download_pdf(row)
        status = "no_pdf"
        refs: list[str] = []
        snippets: list[str] = []
        text_chars = 0
        if pdf_path:
            downloaded += 1
            try:
                text = extract_text(pdf_path)
                text_chars = len(text)
                refs = split_references(find_references_block(text))
                snippets = context_snippets(text, TERMS)
                status = "ok"
            except Exception as exc:  # noqa: BLE001 - keep extraction resilient
                print(f"WARN extract failed: {pdf_path} :: {exc}", file=sys.stderr)
                status = "extract_failed"

        total_refs += len(refs)
        result = {
            "article_id": row["article_id"],
            "journal": row["journal"],
            "year": row["year"],
            "title": row["title"],
            "url": row["url"],
            "score": row["score"],
            "dimensions": row["dimensions"],
            "matched_terms": row["matched_terms"],
            "status": status,
            "pdf_path": str(pdf_path.relative_to(BASE)) if pdf_path else "",
            "text_chars": text_chars,
            "reference_count": len(refs),
            "references": refs,
            "sample_references": refs[:8],
            "snippets": snippets,
        }
        examples.append(result)
        rows.append(
            {
                "article_id": result["article_id"],
                "journal": result["journal"],
                "year": result["year"],
                "title": result["title"],
                "url": result["url"],
                "status": result["status"],
                "pdf_path": result["pdf_path"],
                "text_chars": result["text_chars"],
                "reference_count": result["reference_count"],
                "matched_terms": result["matched_terms"],
            }
        )
        print(f"{idx}/{len(candidates)} {status} refs={len(refs)} {row['title'][:70]}")

    payload = {
        "total_candidates": len(candidates),
        "downloaded_pdfs": downloaded,
        "total_references_extracted": total_refs,
        "articles": examples,
    }
    (DOCS_DATA / "transnational_bibliography.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(
        PROC / "transnational_bibliography.csv",
        rows,
        [
            "article_id",
            "journal",
            "year",
            "title",
            "url",
            "status",
            "pdf_path",
            "text_chars",
            "reference_count",
            "matched_terms",
        ],
    )

    md = [
        "# Bibliografia: multilatinas y transnacionales",
        "",
        f"Articulos candidatos: {len(candidates)}",
        f"PDFs descargados: {downloaded}",
        f"Referencias extraidas: {total_refs}",
        "",
        "## Articulos con mas referencias extraidas",
        "",
    ]
    for item in sorted(examples, key=lambda x: x["reference_count"], reverse=True)[:20]:
        md.extend(
            [
                f"### {item['title']}",
                "",
                f"- Revista: {item['journal']}",
                f"- Ano: {item['year']}",
                f"- URL: {item['url']}",
                f"- Estado: {item['status']}",
                f"- Referencias extraidas: {item['reference_count']}",
                "",
            ]
        )
        if item["sample_references"]:
            md.append("Referencias de muestra:")
            md.extend(f"- {ref}" for ref in item["sample_references"][:5])
            md.append("")
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print(DOCS_DATA / "transnational_bibliography.json")


if __name__ == "__main__":
    main()
