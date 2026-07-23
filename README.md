# repair-event-pack

Build a small, offline record pack for a community repair event. Give the CLI
one CSV; it creates printable event summary and repair cards plus a local
Open Repair Data Standard-shaped CSV export.

This is a no-account utility for transcription and reporting. It does not
diagnose faults, decide whether an item is safe, book appointments, message
owners, process payments, or replace repair-café management software.

## Install

Requires Python 3.9+.

```sh
python -m pip install .
```

## Input CSV

Required columns:

```text
event_date,event_name,item_id,item_category,brand,model,approx_age,fault,assessment,outcome,outcome_note
```

`outcome` must be `unknown`, `fixed`, `repairable`, or `end_of_life`, matching
the Open Repair Data Standard repair-status values. The tool copies text; it
does not infer a diagnosis or convert one status into another.

## Build and verify

```sh
repair-event-pack build records.csv --out ./repair-pack
repair-event-pack verify ./repair-pack
```

Optional metadata can provide `title`, `data_provider`, `group_identifier`, and
`country`:

```json
{"title":"Saturday Fix Day","data_provider":"Example Group","country":"GBR"}
```

The pack contains:

- `index.html` — offline summary and status counts.
- `cards.html` — printable one-card-per-item intake/outcome record.
- `open-repair-data.csv` — deterministic subset-shaped export using standard
  field names.
- `inspection.json` and `inspection.sha256` — normalized record and manifest.
- `README.txt` — local limitations and verification command.

The export is intentionally a subset-shaped local aid. Validate it against the
current [Open Repair Data Standard](https://standard.openrepair.org/standard.html)
and your group's data-sharing rules before publishing it.

## Development

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
python -m build
```

No network calls or runtime services are required.

## License

MIT. Fork it, adapt the CSV contract, or replace the renderer for your event.
