# CLAUDE.md

*Author: Claude (Anthropic) — this document is AI generated, see [docs/init.md](docs/init.md).*

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`gpf-catalogue` turns the Géoplateforme CSW catalogue (336 ISO 19115-3 metadata records at
`https://data.geopf.fr/csw`) into a flat, LLM-consumable **pivot model**: one small JSON
document per resource, plus a static page to browse and measure them. It produces data,
not a search API — indexing and an MCP server are Phase 4 of [ROADMAP.md](ROADMAP.md).

Read [docs/why.md](docs/why.md) before proposing design changes: it records the measurements
(payload sizes, broken `AnyText` filtering, the three ISO encodings of a string) that justify
the pivot approach and is the reference for anything about the source service.

## Commands

```bash
uv sync                                     # install dependencies (requires uv, Python 3.13)
uv run pytest                               # full test suite, offline
uv run pytest tests/test_parse.py::test_service -v   # a single test
uvx ruff check .                            # lint (currently clean; ruff is not a declared dep)

uv run scripts/harvest.py --limit 5         # smoke run against the live CSW service
uv run scripts/harvest.py                   # mirror the whole catalogue (~10 min)
uv run scripts/harvest.py --only IGNF_BD-TOPO --force   # refresh one record
uv run scripts/parse.py                     # *.xml -> *.json + data/catalogue.json
uv run scripts/stats.py                     # catalogue.json -> data/stats.json
uv run scripts/stats.py --format markdown   # the coverage table quoted by the docs
uv run scripts/build_site.py                # assemble site/
uv run python -m http.server -d site 8000   # serve it; file:// does not work
uv run scripts/export_schema.py             # regenerate docs/pivot-schema.json
```

Every script takes `--data-dir`, `-v`/`--verbose`, and `--help`. `harvest.py` and `parse.py`
exit 1 when any record failed — that is expected on a full run (see "Known anomalies" below),
so a non-zero exit is not automatically a regression.

`uvx ruff format` is **not** applied repo-wide: 4 files would be reformatted. Don't run it as
a blanket cleanup; it would produce unrelated diff noise.

## Architecture

The pipeline is two stages over one directory, with the package split so the network-touching
part and the pure part never mix:

```
CSW service ──csw.py──> data/csw/{stem}.xml ──parse.py──> data/csw/{stem}.json
              harvest.py                                   data/catalogue.json
                                                           (CatalogueRecord)
                                                                  │
                                            stats.py ─────────────┤──> data/stats.json
                                            site.py + web/ ───────┴──> site/
```

`catalogue.json` is written *beside* `data_dir`, never inside it: a record identified
`catalogue` would otherwise be written to the same path.

| Module | Role |
|---|---|
| `gpf_catalogue/csw.py` | CSW 2.0.2 client. Only `list_identifiers()` (GetRecords, brief) and `get_record()` (GetRecordById, `mdb` 2.0, full). Returns **raw bytes** on purpose. |
| `gpf_catalogue/storage.py` | Identifier → file name rules, and the `data/csw` layout. |
| `gpf_catalogue/parse.py` | `parse_record(bytes) -> CatalogueRecord`, **pure**: no I/O, no network. This is what the tests cover. |
| `gpf_catalogue/model.py` | The pivot model (`CatalogueRecord`, Pydantic v2) — the contract downstream consumers read. |
| `gpf_catalogue/namespaces.py` | The ISO 19115-3 prefix map; ISO split the old single `gmd` namespace into a dozen. |
| `gpf_catalogue/stats.py` | `compute_stats(list[CatalogueRecord]) -> CatalogueStats`, **pure** like `parse_record`. Aggregates, field coverage, and the derived publisher / licence family / year. |
| `gpf_catalogue/site.py`, `web/` | Assembly of the static overview site, and its three vanilla HTML/CSS/JS files. No template engine, no CDN, no runtime dependency. |
| `gpf_catalogue/harvest.py`, `cli.py` | Orchestration and shared argparse/logging helpers. |
| `scripts/*.py` | Thin CLI wrappers: argparse + call the library + print a summary + exit code. |
| `.github/workflows/pages.yml` | Harvests, parses and publishes the site on GitHub Pages, weekly and on push. It caches `data/csw` and tolerates the expected non-zero exits, but refuses to publish fewer than 300 records. |

Logic belongs in `gpf_catalogue/`, never in `scripts/`.

### Invariants that look like quirks

These were each derived from a real property of the live catalogue. Changing them silently
corrupts the mirror.

- **Records are fetched one by one, not by splitting `GetRecords` pages.** Splitting a page
  means re-serializing XML, which renumbers its 31 namespace prefixes. Per-record fetching
  keeps `data/csw/*.xml` byte-identical to what the service sent, and makes the harvest
  resumable.
- **CSW reports errors with HTTP 200**, inside an `ows:ExceptionReport` body. `CswClient._get`
  inspects every body; never rely on the status code alone.
- **Identifiers are not file names.** Some contain spaces/accents/parentheses, nine already end
  in `.xml`, one is `1.0`, and the pairs `id`/`ID` and `test`/`TEST` differ only by case.
  Hence: percent encoding, `build_filename_map()` computed over the *whole* catalogue (so a
  name never depends on harvest order), and `stem_of()` instead of `Path.stem` /
  `Path.with_suffix()`. The harvest always lists the full catalogue even with `--limit`,
  because file names depend on the complete identifier set.
- **The harvest is resumable and fault-tolerant**: existing files are skipped unless `--force`,
  and one failing record is reported rather than aborting a run of several hundred. Parsing,
  by contrast, always rewrites the JSON so it reflects the current parser.
- **Missing values become `null`, never fabricated.** A title is never derived from an
  identifier, a half declared bounding box is never completed, a licence is never guessed.
  Anomalies are logged and counted in the run reports instead of being hidden.
- **Link typing leans on the URL, not the protocol.** `cit:protocol` is empty on 85 % of
  the 2 584 published online resources. A `?REQUEST=GetCapabilities` *query* is the
  service endpoint itself and
  must stay typed `wfs`/`wms`/…; only a static `capabilities.xml` file is `capabilities`.
  Typing the query as a document would hide the endpoint from a consumer asking for the WFS.
- **Links stay flat, one per published entry.** The catalogue publishes one
  `CI_OnlineResource` per *layer*, all sharing the endpoint URL and differing by
  `cit:name` and `cit:description`: `IGNF_BD-TOPO` publishes 109 WFS entries for one URL,
  `IGNF_ADMIN-EXPRESS` 251 for 16. Only exact `(type, url, name, description)` repeats
  are dropped, which is 9 entries catalogue wide. Do not collapse them on `(type, url)`:
  it drops 1 179 layer names, and names a whole WFS service after whichever layer comes
  first — `BDTOPO_V3:aerodrome` — which states something untrue. **Grouping and filtering
  belong to whoever consumes the model**, not to the model. The overview shows the links
  raw, one row per entry, because the repetition is part of what the catalogue looks like.
- **`cit:name` and `cit:description` are both kept.** `name` is the machine readable
  layer (`BDTOPO_V3:batiment`, the WFS `typeName`), `description` is the human label
  ("BD TOPO® V3 batiment"); they differ on 2 212 of the 2 243 entries carrying both.
- **Output is deterministic.** No timestamp in `catalogue.json`, first value wins on every
  ambiguity, stable ordering. Two runs over the same mirror produce identical bytes, which
  is what makes catalogue drift diffable (ROADMAP phase 5). Do not add a `generated` field.
- **The overview never writes back into the pivot model.** The publisher (contact email
  domain), the licence family and the publication year are derived in `stats.py` for
  display only, each by a rule published in [docs/overview.md](docs/overview.md), and are
  shipped per record in `stats.json` so the page never reimplements them. Two
  implementations of one rule become two rules. Do not normalise `producer` into the
  model: 134 spellings hide fewer organisations, but folding them is an editorial
  decision, not something the catalogue said.
- **A zero is drawn as zero.** The year histogram keeps empty years at zero so the axis
  stays time, and a zero column draws nothing — the 2 px minimum that keeps small bars
  visible would otherwise make "no record" look like "one record".
- **`data/` and `site/` are gitignored** — both rebuildable, not source.

### Adding a field to the pivot model

1. Add it to `CatalogueRecord` in `model.py`, with a `Field(description=...)` — the description
   ends up in the exported JSON schema, which is the consumer-facing documentation.
2. Read it in `parse.py` through the existing `_text()` helper, which resolves the three ISO
   encodings of a string (`gco:CharacterString`, `gcx:Anchor`,
   `lan:PT_FreeText/…/lan:LocalisedCharacterString`) in one place. Don't reimplement that.
3. Datasets and services are the same shape with a different `type`. Identification lives under
   `mri:MD_DataIdentification` *or* `srv:SV_ServiceIdentification` (`_IDENTIFICATION_PATHS`);
   both inherit citation and abstract from the same ISO type, so one code path reads both.
4. Watch out for nested citations — a thesaurus citation must not be mistaken for the resource
   title (there is a test for this). Prefer anchored `find()` paths over `.//`.
5. Run `uv run scripts/export_schema.py`, then
   `uv run scripts/stats.py --format markdown` and paste its table into
   [docs/model.md](docs/model.md). Coverage is measured, never estimated; `stats.py`
   reads the field list from the model, so a new field is counted without being
   registered anywhere.
6. Add a shape to `tests/data/dataset.xml` and assert it in `tests/test_parse.py`. That
   fixture is meant to carry one example of every shape the live catalogue uses.

The rule for what enters the model: *a field enters when a search or a question needs it, not
because ISO defines it.* The model is lossy by design; the raw XML stays next to it.

### Tests

`tests/` runs fully offline against six hand-picked samples in `tests/data/`: a dataset
carrying every field of the model, a real service record with English translations, a
record with no title, a title carried by a `gcx:Anchor` with no scope code, a test record,
and a real record with a test-looking identifier (`test_openig`, titled "Communes de
l'Hérault"). The `sample` fixture loads them.

`test_parse.py` covers the pure parser; `test_catalogue.py` covers `parse_all` and the
aggregate, working in `tmp_path`. `GeoPF_Altimetrie.xml` is a verbatim service response —
do not edit it, its value is being exactly what the service sent.

## Conventions

- **Code, comments and documentation are in English**, even though the project is French and
  the source metadata is French. This was an explicit requirement (see [docs/init.md](docs/init.md)).
- Google-style docstrings on every public function, including `Args:`/`Returns:`/`Raises:`.
  Comments explain *why* — typically which property of the real catalogue forced the code.
- Type hints throughout, modern syntax (`str | None`, `list[str]`).
- camelCase in JSON (via the Pydantic `to_camel` alias generator), snake_case in Python.
- Lines wrap around 88 characters.
- Numbers quoted in the docs (336 records, 333 harvested, 326 converted, 201 813 bytes for
  `IGNF_BD-TOPO`) are measurements from the run of 2026-09-20. Re-measure before changing them;
  don't estimate.
- **Every new generated file carries an `Author: Claude (Anthropic)` line.** This repository
  is an AI generated experiment and says so in each file; the placement per file kind, and the
  four files deliberately left without one, are listed in
  [docs/init.md](docs/init.md#authorship). In Python it goes *below* the module docstring —
  `scripts/*.py` pass `__doc__` to argparse, so a line inside the docstring leaks into `--help`.

## Known anomalies in the source catalogue

Not bugs in this code — tracked under "Known issues left open" in [ROADMAP.md](ROADMAP.md):

- 3 records fail server-side ISO 19115-3 transformation (`mdb-full.xsl`) and cannot be
  harvested: `IGNF_BD-TRANSPORTS-EXCEPTIONNELS`, `MTECT_CORINE-LAND-COVER`,
  `fr-662043116-7D3DC709-E1EB-470B-9FD0-8ABF8AAFD8E4`. They exist in the older `gmd` schema.
- 7 records are published with no identification block at all, so they parse as failures.
- `srv:operatesOn` and `mdb:parentMetadata` appear **zero** times, so nothing says which
  service serves which dataset. Do not reconstruct the relation from URL or title
  similarity and present it as a fact.
- Some records glue an anchor's `xlink:href` onto its own label. Only an exact trailing
  repeat is stripped (`_strip_repeated_href`); anything else is kept verbatim.
- `AnyText` CQL filtering is broken server-side (`UnknownFormatConversionException` on `%`).
- Test records (`test`, `TEST`, `1`, `lls`, `blba lbla`) are published alongside real ones.
