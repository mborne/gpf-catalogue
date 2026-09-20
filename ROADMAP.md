# Roadmap

*Author: Claude (Anthropic) — this document is AI generated, see [docs/init.md](docs/init.md).*

The goal is a catalogue of the Géoplateforme that a LLM can search and describe, built from
the ISO 19115 records of [`https://data.geopf.fr/csw`](https://data.geopf.fr/csw).

The approach is incremental on purpose: a minimal model harvested end to end first, then
more fields, then search. Each phase leaves the repository in a working state.

## Phase 1 — A minimal pivot catalogue

Prove the whole chain on the smallest model that is still useful.

- [x] Explain the approach — [docs/why.md](docs/why.md)
- [x] Define a flat pivot model: `fileIdentifier`, `type`, `title`, `abstract`
- [x] Harvest the records to `data/csw/{name}.xml`
- [x] Parse them into `data/csw/{name}.json`
- [x] Report catalogue anomalies (missing titles, colliding identifiers) instead of hiding them
- [x] Unit tests on the parser, running offline

### Known issues left open

- [ ] 3 records cannot be served in the `mdb` schema (`mdb-full.xsl` fails server side).
      They are readable in the older `gmd` schema: either fall back to it, or report the
      failure upstream.
- [ ] 7 records are published without any identification block. Nothing can be done here
      but report them; they are counted as failures by `scripts/parse.py`.

## Phase 2 — A model worth searching

Add the fields that make a record answerable, still one flat JSON per resource.

- [x] **Producer and contacts** — organisation name and email (`cit:CI_Responsibility`),
      read most specific first: resource point of contact, then citation, then
      `mdb:contact`
- [x] **Keywords and topic categories** — including the INSPIRE thesaurus, exposed
      separately as `inspireThemes` because it is a controlled vocabulary
      (`mri:descriptiveKeywords`, `mri:topicCategory`)
- [x] **Access links** — WFS, WMS, WMTS, TMS, download, capabilities and documentation
      endpoints, typed and deduplicated (`mrd:MD_Distribution`, `cit:CI_OnlineResource`)
- [x] **Spatial and temporal extent** — bounding box union and time period (`gex:EX_Extent`)
- [x] **Dates** — creation, revision, publication (`cit:CI_Date`)
- [x] **Licence and use constraints** (`mco:MD_LegalConstraints`), split by whether the
      block declares `useConstraints` or `accessConstraints`
- [x] Test records are **flagged**, not dropped: `suspectedTest` marks 14 of the 326
      records, and the consumer decides
- [x] Publish the pivot catalogue as a single `catalogue.json`, in addition to one file
      per record
- [ ] ~~**Relations** — which service serves which dataset (`srv:operatesOn`,
      `mdb:parentMetadata`)~~ — **not possible**, see below

Answered along the way: how much of a record should be flattened before it stops being a
pivot model and becomes a copy of ISO. The rule held — a field enters the model when a
search or a question needs it, not because it exists. `Link` is the one sub-object the
model allows, and [docs/model.md](docs/model.md#why-links-are-objects) argues why.

### What the catalogue does not carry

Measured over the 333 harvested records, not inferred from the standard:

- **`srv:operatesOn` and `mdb:parentMetadata` appear zero times.** Nothing in the
  catalogue says which service serves which dataset, so the relation cannot be published.
  Reconstructing it from URL or title similarity would be a guess wearing the clothes of
  a fact. Either the producers start filling those elements, or a future phase publishes
  an explicitly heuristic link, clearly marked as such.
- **`cit:protocol` is empty on 85 % of the links** (2 203 of 2 584), which is why link
  typing leans on the URL.
- **1 054 of 2 584 links are internal repeats**, the same endpoint published once per
  layer it serves.

## Phase 3 — Search and MCP

- [ ] Index the pivot catalogue (lexical first, it is only 326 records), with
      `inspireThemes`, `topicCategories`, `bbox` and `type` as facets
- [ ] Evaluate on real questions: *which dataset contains bridges?*, *which service computes
      an elevation?*, *what is available on land use?*
- [ ] Expose an MCP server: `search_catalogue`, `describe_resource`
- [ ] Decide how it relates to [geocontext](https://github.com/ignfab/geocontext): separate
      server, or a catalogue tool contributed there
- [ ] Return links a model can act on, so search results lead to actual data access

## Phase 4 — Keep it current

- [ ] Incremental refresh based on the record revision date, rather than a full harvest
- [ ] CI checking that the pipeline still runs against the live service
- [ ] Track catalogue drift: new, removed and modified records between two harvests
- [ ] Publish the built catalogue as a release artifact, so consumers do not each re-harvest

## Deliberately out of scope for now

- Mirroring the data itself — this project catalogues resources, it does not copy them.
- Harvesting other CSW services. The model should not be Géoplateforme specific, but the
  harvest is, and generalizing before the second catalogue exists would be guesswork.
- Writing back to the catalogue. This project is read-only.
