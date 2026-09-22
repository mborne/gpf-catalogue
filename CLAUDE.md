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
uv run scripts/stats.py --format markdown   # the field coverage table quoted by the docs
uv run scripts/harvest_services.py          # WFS/WMTS/download inventories -> data/services/
uv run scripts/coverage.py                  # + catalogue.json -> data/coverage.json
uv run scripts/coverage.py --format markdown   # the service coverage table quoted by the docs
uv run scripts/build_site.py                # assemble site/ (needs web/dist)
uv run scripts/serve_site.py                # serve it; file:// does not work
uv run scripts/export_schema.py             # regenerate docs/pivot-schema.json

npm ci --prefix web                         # front end dependencies (node 24)
npm run build --prefix web                  # tsc + vite -> web/dist
npm run dev --prefix web                    # vite dev server, on the site/ data
VITE_BASE=/gpf-catalogue/ npm run build --prefix web   # what the Pages workflow does
```

`scripts/build_site.py` fails until `web/dist` exists; `npm run build` is not optional.
Two tests read that bundle and **skip** when it is missing, so a green `pytest` on a
machine that never ran npm is not proof the site builds.

`uv run python -m http.server -d site 8000` still serves the entry page, but answers 404
on `/records/{fileIdentifier}` — that is a route, not a file. `scripts/serve_site.py`
applies the rule GitHub Pages applies through `404.html`.

Every script takes `--data-dir`, `-v`/`--verbose`, and `--help`. `harvest.py`, `harvest_services.py` and `parse.py`
exit 1 when any record or inventory failed — that is expected on a full run (see "Known anomalies" below),
so a non-zero exit is not automatically a regression.

`uvx ruff format` is **not** applied repo-wide: 4 files would be reformatted. Don't run it as
a blanket cleanup; it would produce unrelated diff noise.

## Architecture

The pipeline is two stages over one directory, plus a side branch that mirrors what three
services say they serve. The package is split so the network-touching part and the pure
part never mix:

```
CSW service ──csw.py──> data/csw/{stem}.xml ──parse.py──> data/csw/{stem}.json
              harvest.py                                   data/catalogue.json
                                                           (CatalogueRecord)
                                                                  │
                                            stats.py ─────────────┤──> data/stats.json
                                            coverage.py ──────────┤──> data/coverage.json
                                                ▲                 │
WFS / WMTS / download ──services.py──> data/services/{svc}-{n}.xml │
              harvest_services.py          └──inventory.py──┘      │
                                                                  │
                                            site.py ──────────────┴──> site/
                                                ▲
                            web/ ──vite──> web/dist
```

`catalogue.json` is written *beside* `data_dir`, never inside it: a record identified
`catalogue` would otherwise be written to the same path.

| Module | Role |
|---|---|
| `gpf_catalogue/csw.py` | CSW 2.0.2 client. Only `list_identifiers()` (GetRecords, brief) and `get_record()` (GetRecordById, `mdb` 2.0, full). Returns **raw bytes** on purpose. |
| `gpf_catalogue/storage.py` | Identifier → file name rules, and the `data/csw` and `data/services` layouts. |
| `gpf_catalogue/parse.py` | `parse_record(bytes) -> CatalogueRecord`, **pure**: no I/O, no network. This is what the tests cover. |
| `gpf_catalogue/model.py` | The pivot model (`CatalogueRecord`, Pydantic v2) — the contract downstream consumers read. |
| `gpf_catalogue/namespaces.py` | The ISO 19115-3 prefix map; ISO split the old single `gmd` namespace into a dozen. |
| `gpf_catalogue/stats.py` | `compute_stats(list[CatalogueRecord]) -> CatalogueStats`, **pure** like `parse_record`. Aggregates, field coverage, and the derived publisher / licence family / year. |
| `gpf_catalogue/services.py` | Clients for the three services publishing their own inventory (WFS and WMTS `GetCapabilities`, the paginated Atom feed of the download service). Returns **raw bytes**, like `csw.py`. |
| `gpf_catalogue/inventory.py` | `parse_inventory(service, list[bytes]) -> ServiceInventory`, **pure**. Reduces the three documents to one shape: a `key` a record can cite, and the service's own `title`. |
| `gpf_catalogue/coverage.py` | `compute_coverage(records, inventories) -> CatalogueCoverage`, **pure**. What is served against what is described, both ways round. |
| `gpf_catalogue/site.py` | Assembly of the static overview site: copy `web/dist` + the JSON documents into `site/`, and write `404.html`. `coverage.json` only when an inventory directory is passed. |
| `gpf_catalogue/serve.py` | A local static server that answers the application's routes with the entry document, which `python -m http.server` cannot. |
| `web/` | The front end: React, react-router and Vite, in TypeScript. Seven routes — `/overview`, `/records`, `/records/{fileIdentifier}`, `/quality`, `/coverage`, `/coverage/{service}`, `/about`. No CDN: React is bundled into the assets the site carries. See [docs/overview.md](docs/overview.md). |
| `gpf_catalogue/harvest.py`, `cli.py` | Orchestration and shared argparse/logging helpers. |
| `scripts/*.py` | Thin CLI wrappers: argparse + call the library + print a summary + exit code. |
| `.github/workflows/pages.yml` | Builds the front end, harvests, parses and publishes the site on GitHub Pages, weekly and on push. It caches `data/csw` and tolerates the expected non-zero exits, but refuses to publish fewer than 300 records. `configure-pages` runs **before** the front end build, because the bundle needs the deployment prefix. The service inventories are re-fetched on every run and **not** cached: three requests against ten minutes for the records, and a stale inventory would report withdrawn layers as uncovered. |

Logic belongs in `gpf_catalogue/`, never in `scripts/`. Front end logic belongs in
`web/src/`, never in `gpf_catalogue/site.py`, which only copies files.

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
- **`bbox` is the union, `extents` is the truth.** The catalogue publishes one
  `gex:EX_Extent` per territory: `IGNF_BD-TOPO` declares eight, named and coded
  `FXX`…`MAF`. Their union reaches from the Caribbean to Réunion, 65 times the area
  described, and `ENR_CONSO-ELECTRICITE-COMMUNE` gets a union **3 519 times** its four
  territories combined — 47 records declare more than one box. `bbox` is kept as the
  cheap first filter and is recomputed from `extents`, never read separately. An extent
  with no usable box produces no entry, which is how the 115 purely *temporal* extents
  ("Dates de publication") stay out of the geography; an extent with no description
  keeps `name: null`, like the 167 anonymous ones. Do not collapse or dissolve the
  zones: grouping belongs to the consumer, as it does for links.
- **`edition` is read on the resource citation only.** `cit:edition` also hangs under
  every `mrd:distributionFormat` citation, where it says `inapplicable`: `IGNF_BD-TOPO`
  publishes 695 of them against the one that matters, `3.5`. This is the nested citation
  trap, in a second place.
- **Links stay flat, one per published entry.** The catalogue publishes one
  `CI_OnlineResource` per *layer*, all sharing the endpoint URL and differing by
  `cit:name` and `cit:description`: `IGNF_BD-TOPO` publishes 109 WFS entries for one URL,
  `IGNF_ADMIN-EXPRESS` 251 for 16. Only exact `(type, url, name, description)` repeats
  are dropped, which is 9 entries catalogue wide. Do not collapse them on `(type, url)`:
  it drops 1 179 layer names, and names a whole WFS service after whichever layer comes
  first — `BDTOPO_V3:aerodrome` — which states something untrue. **Grouping and filtering
  belong to whoever consumes the model**, not to the model. The overview shows the links
  raw, one row per entry, because the repetition is part of what the catalogue looks like;
  it only *sections* them by protocol — one heading, one table per type — because a value
  that is identical on all 109 rows of a group is a heading, not a column.
- **`cit:name` and `cit:description` are both kept.** `name` is the machine readable
  layer (`BDTOPO_V3:batiment`, the WFS `typeName`), `description` is the human label
  ("BD TOPO® V3 batiment"); they differ on 2 212 of the 2 243 entries carrying both.
- **A code list value is read from its code, never from its label.** `spatialScope`
  comes from the `xlink:href` of the keyword anchor, because 6 records cite
  `.../SpatialScope/global` under the label "National", and the labels spell two codes
  four ways. The keyword itself stays in `keywords` as published, label and all.
- **Markdown is rendered in abstracts only, and never through `innerHTML`.** 94 of the
  326 abstracts use `**bold**`, so the page renders them; link names and descriptions are
  left raw because 155 carry `*` or `_` inside a layer name. The renderer builds DOM nodes
  and turns anything unrecognised into a text node — the text comes from a third party
  service, so a `<script>` in an abstract must be displayed, not run.
- **A route is a real path, and the site is still static.** `/records/{fileIdentifier}`
  is what the rewrite was for, and it costs two things. The bundle is built with its
  deployment prefix (`VITE_BASE`, `/` by default, `/gpf-catalogue/` on Pages) and the
  router takes the same value as its basename — relative asset URLs would resolve
  against the record instead of the site root. And `build_site` writes `404.html` as a
  byte copy of `index.html`, because a static host has no rewrite rule: that copy is
  what makes a pasted link to a record boot the application. Do not "fix" the 404
  status of that first response — the document is right and the code is the host's.
- **A route change decides where the page opens.** `web/src/scroll.ts` scrolls to the
  top on PUSH, restores the remembered offset on POP so Back lands on the row that was
  clicked, and moves nothing on REPLACE — a filter change replaces the entry, and the
  page must not slide under someone typing. It sets `history.scrollRestoration =
  "manual"`, because the browser restores against a document that had not rendered the
  route yet. It is called once, in `Layout`, since that is the component every route
  renders inside; a page calling it itself would be a page that can forget to.
- **The front end derives nothing, still.** Publisher, licence family and year are read
  from `recordFacets` in `stats.json`. A filter is a query parameter, and a filter
  change *replaces* the history entry rather than pushing one, so Back leads out of the
  search rather than through a transcript of keystrokes.
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
- **Coverage is matched on the key both sides publish, never on a title.** A WFS link
  carries the `typeName` in `cit:name` (`BDTOPO_V3:batiment`), a WMTS link the layer
  identifier, a download link the resource in its URL path
  (`/telechargement/resource/ADMIN-EXPRESS`) — and those are exactly the strings
  `wfs:FeatureType/wfs:Name`, `wmts:Layer/ows:Identifier` and `atom:id` publish. Since
  `srv:operatesOn` and `mdb:parentMetadata` appear zero times, a title similarity would
  *invent* the relation the catalogue declined to publish. A record and a layer sharing a
  theme but no key stay two separate gaps. A download link pointing at a `.7z` inside a
  delivery names no resource — 127 of the 232 — and is counted as unmatchable, not as a
  wrong claim. Reading the WMTS is anchored on `wmts:Contents/wmts:Layer`: the
  capabilities holds 2 292 `ows:Identifier` for 712 layers, the rest being styles and
  tile matrix sets.
- **`coverage.json` may legitimately be absent, and the page says so.** It is measured
  against three services other than the CSW, so `build_site()` takes the inventory
  directory **explicitly** rather than reaching for `data/services` — a figure that
  silently depends on what happens to be on disk is a figure nobody can check. A build
  without it publishes a correct site that reports the coverage as not measured, never
  zero. An inventory that was never harvested is *missing*, not empty: an empty one would
  say the service serves nothing, and turn every record citing it into a false anomaly.
- **`/coverage` carries the answer, `/coverage/{service}` carries the lists.** The
  three services publish 298, 387 and 40 resources no record describes, plus 137 and
  19 keys a record cites and they do not serve: stacked on one page that is 900 rows,
  and the figure a reader came for sits above a scroll nobody finishes. Each list is
  also a working list — *the WMTS layers nobody documented* is worth sending to
  someone, which a section of a longer page could not be. The shared pieces live in
  `web/src/components/Coverage.tsx`; neither page derives anything, both read
  `coverage.json`.
- **The word *coverage* does two jobs.** The quality page reports **field** coverage (how
  often a field of the pivot model is filled in, from `stats.json`); `/coverage` reports
  **service** coverage (how much of what is served is described, from `coverage.json`).
  They are different measurements and the headings say which.
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
7. Mirror it in `web/src/types.ts` — the reader's side of the same contract — and show it
   on the record page (`web/src/components/RecordDetail.tsx`). `tsc` is run by
   `npm run build`, so a field left out of the type is caught only where it is read.

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

Four more samples carry the *service* side: `wfs-capabilities.xml`,
`wmts-capabilities.xml` and `download-feed-{01,02}.xml`, trimmed from the live responses
and keeping one example of each shape that matters — a padded title, an entry with no
name, the `ows:Identifier` a WMTS gives to a style and to a tile matrix set, and a feed
that has to be walked across its pages. `test_inventory.py` and `test_coverage.py` cover
them, offline like the rest.

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
- One record publishes the maintenance frequency `quaterly` (sic) where the ISO code list
  says `quarterly`. `updateFrequency` is therefore a plain `str` and not a `StrEnum`: the
  code is kept verbatim, because rejecting the record and repairing the spelling are both
  worse than reporting what the catalogue says.
- 103 records publish `mrl:statement` and 14 publish `mri:purpose` with no text at all,
  so `lineage` and `purpose` are `null` on them — present in the XML, empty in substance.
- Test records (`test`, `TEST`, `1`, `lls`, `blba lbla`) are published alongside real ones.
