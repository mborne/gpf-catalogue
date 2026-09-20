# Roadmap

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

- [ ] **Producer and contacts** — organisation name, role, email (`cit:CI_Responsibility`)
- [ ] **Keywords and topic categories** — including the INSPIRE thesaurus
      (`mri:descriptiveKeywords`, `mri:topicCategory`)
- [ ] **Access links** — WFS, WMS, WMTS, TMS and download endpoints
      (`mrd:MD_Distribution`, `cit:CI_OnlineResource`), typed rather than dumped
- [ ] **Spatial and temporal extent** — bounding box and time period (`gex:EX_Extent`)
- [ ] **Dates** — creation, revision, publication (`cit:CI_Date`)
- [ ] **Licence and use constraints** (`mco:MD_LegalConstraints`)
- [ ] **Relations** — which service serves which dataset (`srv:operatesOn`, `mdb:parentMetadata`)
- [ ] Decide what to do with the test records published in the catalogue: keep, flag or drop
- [ ] Publish the pivot catalogue as a single `catalogue.json`, in addition to one file per record

Open question: how much of a record should be flattened before it stops being a pivot model
and becomes a copy of ISO. The rule so far — a field enters the model when a search or a
question needs it, not because it exists.

## Phase 3 — Search and MCP

- [ ] Index the pivot catalogue (lexical first, it is only 336 records)
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
