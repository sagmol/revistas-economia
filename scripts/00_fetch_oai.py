"""
00_fetch_oai.py
===============
Descarga metadatos OAI-PMH para las revistas que tengan endpoint confirmado.

Salida:
  data/raw/oai/<journal_id>.json

El script usa solo biblioteca estandar para que el proyecto arranque sin
dependencias externas. Si una revista no tiene endpoint configurado, se omite y
queda registrada en el log.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "journals.json"
RAW_OAI = BASE / "data" / "raw" / "oai"
LOG_DIR = BASE / "logs"

RAW_OAI.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "00_fetch_oai.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}


def build_url(endpoint: str, params: dict[str, str]) -> str:
    return endpoint + "?" + urllib.parse.urlencode(params)


def fetch_xml(url: str) -> ET.Element:
    log.info("GET %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "revistas-economia-unam/0.1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    return ET.fromstring(data)


def text_list(parent: ET.Element, tag: str) -> list[str]:
    values = []
    for node in parent.findall(f".//dc:{tag}", NS):
        if node.text and node.text.strip():
            values.append(node.text.strip())
    return values


def parse_record(record: ET.Element) -> dict:
    header = record.find("oai:header", NS)
    metadata = record.find("oai:metadata/oai_dc:dc", NS)
    if metadata is None:
        metadata = record.find("oai:metadata", NS)

    return {
        "identifier": (header.findtext("oai:identifier", default="", namespaces=NS) if header is not None else ""),
        "datestamp": (header.findtext("oai:datestamp", default="", namespaces=NS) if header is not None else ""),
        "sets": [s.text.strip() for s in header.findall("oai:setSpec", NS) if s.text] if header is not None else [],
        "titles": text_list(metadata, "title") if metadata is not None else [],
        "creators": text_list(metadata, "creator") if metadata is not None else [],
        "subjects": text_list(metadata, "subject") if metadata is not None else [],
        "descriptions": text_list(metadata, "description") if metadata is not None else [],
        "publishers": text_list(metadata, "publisher") if metadata is not None else [],
        "contributors": text_list(metadata, "contributor") if metadata is not None else [],
        "dates": text_list(metadata, "date") if metadata is not None else [],
        "types": text_list(metadata, "type") if metadata is not None else [],
        "formats": text_list(metadata, "format") if metadata is not None else [],
        "source": text_list(metadata, "source") if metadata is not None else [],
        "languages": text_list(metadata, "language") if metadata is not None else [],
        "relations": text_list(metadata, "relation") if metadata is not None else [],
        "coverage": text_list(metadata, "coverage") if metadata is not None else [],
        "rights": text_list(metadata, "rights") if metadata is not None else [],
    }


def list_records(endpoint: str, pause: float = 0.8) -> list[dict]:
    records: list[dict] = []
    token: str | None = None

    while True:
        if token:
            params = {"verb": "ListRecords", "resumptionToken": token}
        else:
            params = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}

        root = fetch_xml(build_url(endpoint, params))
        error = root.find("oai:error", NS)
        if error is not None:
            raise RuntimeError(f"OAI error {error.attrib}: {error.text}")

        for record in root.findall(".//oai:ListRecords/oai:record", NS):
            records.append(parse_record(record))

        token_node = root.find(".//oai:ListRecords/oai:resumptionToken", NS)
        token = token_node.text.strip() if token_node is not None and token_node.text else None
        log.info("Registros acumulados: %s", len(records))

        if not token:
            break
        time.sleep(pause)

    return records


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    run_at = datetime.now(timezone.utc).isoformat()
    selected = set(sys.argv[1:])

    for journal in config["journals"]:
        if selected and journal["id"] not in selected:
            continue

        endpoint = journal.get("oai_endpoint")
        if not endpoint:
            log.info("Omitiendo %s: sin endpoint OAI confirmado", journal["id"])
            continue

        try:
            records = list_records(endpoint)
        except Exception as exc:
            log.exception("Fallo al descargar %s: %s", journal["id"], exc)
            continue

        payload = {
            "journal": journal,
            "fetched_at": run_at,
            "record_count": len(records),
            "records": records,
        }
        out = RAW_OAI / f"{journal['id']}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("Guardado %s (%s registros)", out, len(records))


if __name__ == "__main__":
    main()
