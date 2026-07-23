from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {
    "event_date",
    "event_name",
    "item_id",
    "item_category",
    "brand",
    "model",
    "approx_age",
    "fault",
    "assessment",
    "outcome",
    "outcome_note",
}
OUTCOMES = {"unknown", "fixed", "repairable", "end_of_life"}


class PackError(ValueError):
    """Raised when a repair-event pack violates its input contract."""


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_rows(source: Path) -> list[dict[str, str]]:
    if not source.is_file():
        raise PackError(f"records is not a file: {source}")
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise PackError(f"records missing columns: {', '.join(sorted(missing))}")
        rows = []
        seen: set[str] = set()
        for number, raw in enumerate(reader, start=2):
            row = {key: (value or "").strip() for key, value in raw.items()}
            item_id = row.get("item_id", "")
            outcome = row.get("outcome", "")
            if not item_id:
                raise PackError(f"row {number}: item_id is required")
            if item_id in seen:
                raise PackError(f"row {number}: duplicate item_id {item_id!r}")
            if not row.get("event_date") or not row.get("event_name"):
                raise PackError(f"row {number}: event_date and event_name are required")
            if outcome not in OUTCOMES:
                raise PackError(f"row {number}: invalid outcome {outcome!r}")
            seen.add(item_id)
            rows.append(row)
    if not rows:
        raise PackError("records contains no rows")
    return rows


def _ora_rows(rows: list[dict[str, str]], metadata: dict) -> list[dict[str, str]]:
    provider = str(metadata.get("data_provider") or "")
    group = str(metadata.get("group_identifier") or "")
    country = str(metadata.get("country") or "")
    return [
        {
            "id": row["item_id"],
            "partner_product_category": row["item_category"],
            "product_category": row["item_category"],
            "product_category_id": "",
            "brand": row["brand"],
            "year_of_manufacture": "",
            "product_age": row["approx_age"],
            "problem": row["fault"],
            "repair_status": row["outcome"],
            "repair_barrier_if_end_of_life": "",
            "group_identifier": group,
            "event_date": row["event_date"],
            "data_provider": provider,
            "country": country,
            "record_date": row["event_date"],
        }
        for row in rows
    ]


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_pack(records: str | Path, out_dir: str | Path, metadata: dict | None = None) -> dict:
    source = Path(records).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    if out == source or source in out.parents:
        raise PackError("output must be a directory distinct from and outside the input file")
    if out.exists():
        raise PackError(f"output already exists: {out}")
    metadata = metadata or {}
    rows = _read_rows(source)
    out.mkdir(parents=True)
    title = str(metadata.get("title") or rows[0]["event_name"])
    ora = _ora_rows(rows, metadata)
    fields = list(ora[0])
    _write_csv(out / "open-repair-data.csv", ora, fields)

    cards = []
    for row in rows:
        cards.append(
            "<article><h2>"
            + html.escape(row["item_id"])
            + " — "
            + html.escape(row["item_category"])
            + "</h2><dl>"
            + "".join(
                f"<dt>{html.escape(label)}</dt><dd>{html.escape(row[key]) or '—'}</dd>"
                for key, label in (("brand", "Brand"), ("model", "Model"), ("approx_age", "Approx. age"), ("fault", "Reported fault"), ("assessment", "Assessment"), ("outcome", "Repair status"), ("outcome_note", "Outcome note"))
            )
            + "</dl></article>"
        )
    style = "body{font:16px system-ui;max-width:1000px;margin:2rem auto}article{border:1px solid #bbb;border-radius:8px;padding:1rem;margin:1rem 0;break-inside:avoid}dt{font-weight:700}dd{margin:0 0 .5rem 0}"
    (out / "cards.html").write_text("<!doctype html><meta charset=utf-8><title>" + html.escape(title) + " cards</title><style>" + style + "</style><h1>" + html.escape(title) + " — repair cards</h1>" + "".join(cards), encoding="utf-8")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    summary = "".join(f"<li>{html.escape(status)}: {count}</li>" for status, count in sorted(counts.items()))
    (out / "index.html").write_text("<!doctype html><meta charset=utf-8><title>" + html.escape(title) + "</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:.4rem;text-align:left}</style><h1>" + html.escape(title) + "</h1><p>Offline repair-event summary. Records are transcribed observations, not diagnoses or safety determinations.</p><ul>" + summary + "</ul><table><tr><th>ID</th><th>Category</th><th>Brand</th><th>Status</th><th>Note</th></tr>" + "".join(f"<tr><td>{html.escape(r['item_id'])}</td><td>{html.escape(r['item_category'])}</td><td>{html.escape(r['brand'])}</td><td>{html.escape(r['outcome'])}</td><td>{html.escape(r['outcome_note'])}</td></tr>" for r in rows) + "</table>", encoding="utf-8")

    (out / "README.txt").write_text("Offline repair-event pack. Open index.html or cards.html. Verify with: repair-event-pack verify .\nThe Open Repair export is a local subset-shaped export; validate it against the current standard before publication.\n", encoding="utf-8")
    file_names = ["index.html", "cards.html", "open-repair-data.csv", "README.txt"]
    record = {"version": 1, "created_utc": _utc_now(), "metadata": metadata, "rows": rows, "ora_fields": fields, "files": {name: _sha256(out / name) for name in file_names}}
    (out / "inspection.json").write_bytes(_canonical(record))
    manifest_names = ["inspection.json"] + file_names
    (out / "inspection.sha256").write_text("".join(f"{_sha256(out / name)}  {name}\n" for name in manifest_names), encoding="utf-8")
    return record


def verify_pack(pack_dir: str | Path) -> list[str]:
    pack = Path(pack_dir).expanduser().resolve()
    record_path = pack / "inspection.json"
    hash_path = pack / "inspection.sha256"
    if not record_path.is_file() or not hash_path.is_file():
        raise PackError("missing inspection.json or inspection.sha256")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    errors = []
    for line in hash_path.read_text(encoding="utf-8").splitlines():
        try:
            expected, name = line.split("  ", 1)
        except ValueError:
            errors.append("invalid manifest line")
            continue
        path = pack / name
        if not path.is_file():
            errors.append(f"missing: {name}")
        elif _sha256(path) != expected:
            errors.append(f"changed: {name}")
    for name in ("index.html", "cards.html", "open-repair-data.csv", "README.txt"):
        if not (pack / name).is_file() and f"missing: {name}" not in errors:
            errors.append(f"missing: {name}")
    return errors
