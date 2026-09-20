# Roadmap

*Author: Claude (Anthropic) — this document is AI generated, see [docs/init.md](docs/init.md).*

The goal is a catalogue of the Géoplateforme that a LLM can search and describe, built from
the ISO 19115 records of [`https://data.geopf.fr/csw`](https://data.geopf.fr/csw).

The approach is incremental on purpose: a minimal model harvested end to end first, then
more fields, then a look at what was actually collected, then search. Each phase leaves the
repository in a working state.

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
- [ ] One record publishes the maintenance frequency `quaterly` (sic). `updateFrequency`
      keeps it verbatim rather than repairing it, which is why the field is a `str` and
      not an enumeration.
- [ ] 103 records publish an empty `mrl:statement`, and 14 an empty `mri:purpose`: the
      element is there, the text is not. They are read as `null`.

## Phase 2 — A model worth searching

Add the fields that make a record answerable, still one flat JSON per resource.

- [x] **Producer and contacts** — organisation name and email (`cit:CI_Responsibility`),
      read most specific first: resource point of contact, then citation, then
      `mdb:contact`
- [x] **Keywords and topic categories** — including the INSPIRE thesaurus, exposed
      separately as `inspireThemes` because it is a controlled vocabulary
      (`mri:descriptiveKeywords`, `mri:topicCategory`)
- [x] **Access links** — WFS, WMS, WMTS, TMS, download, capabilities and documentation
      endpoints, typed and kept flat (`mrd:MD_Distribution`, `cit:CI_OnlineResource`)
- [x] **Spatial and temporal extent** — bounding box union and time period (`gex:EX_Extent`)
- [x] **Named extents** — `extents`, one entry per `gex:EX_Extent` with the description
      and the ISO 3166 code the record publishes for it. Added after phase 3, from a
      reading of the `IGNF_BD-TOPO` XML: the union alone was not merely lossy but wrong,
      giving `ENR_CONSO-ELECTRICITE-COMMUNE` a box 3 519 times its real coverage. `bbox`
      stays, recomputed from `extents`, as the cheap first filter
- [x] **Lineage, purpose, edition, update frequency and thumbnail** — the blocks the
      catalogue fills widely and the model was dropping: `mrl:LI_Lineage/statement`
      (191 records), `mri:resourceMaintenance` (315), `mri:graphicOverview` (206),
      `cit:edition` on the resource citation (139), `mri:purpose` (129)
- [x] **Dates** — creation, revision, publication (`cit:CI_Date`)
- [x] **Licence and use constraints** (`mco:MD_LegalConstraints`), split by whether the
      block declares `useConstraints` or `accessConstraints`
- [x] Test records are **flagged**, not dropped: `suspectedTest` marks 14 of the 326
      records, and the consumer decides
- [x] Publish the pivot catalogue as a single `catalogue.json`, in addition to one file
      per record
- [x] **Spatial scope** — `spatialScope`, the INSPIRE code list value carried as a
      keyword anchor (`mri:descriptiveKeywords`), cited by 136 of the 326 records.
      Added after phase 3, for [issue #1](https://github.com/mborne/gpf-catalogue/issues/1):
      it is the cheapest filter for *local data or national product?*, which `bbox`
      does not answer — 81 records declare the same mainland France box. The code is
      read, not the label: the two disagree on 6 records
- [ ] ~~**Relations** — which service serves which dataset (`srv:operatesOn`,
      `mdb:parentMetadata`)~~ — **not possible**, see below

Answered along the way: how much of a record should be flattened before it stops being a
pivot model and becomes a copy of ISO. The rule held — a field enters the model when a
search or a question needs it, not because it exists. `Link` and `Extent` are the two
sub-objects the model allows, and
[docs/model.md](docs/model.md#why-links-and-extents-are-objects) argues why.

Still measured and still out, for want of a question that needs them: `mrs:MD_ReferenceSystem`
(143 records, 344 EPSG codes), `mrd:distributionFormat` (134, 394 entries),
`mri:spatialResolution` (181), the `xlink:href` of the licence and access anchors (128
and 154), `mco:useLimitation` (167, mostly "Aucune contrainte"),
`mri:supplementalInformation` (24) and `mri:credit` (3).

### What the catalogue does not carry

Measured over the 333 harvested records, not inferred from the standard:

- **`srv:operatesOn` and `mdb:parentMetadata` appear zero times.** Nothing in the
  catalogue says which service serves which dataset, so the relation cannot be published.
  Reconstructing it from URL or title similarity would be a guess wearing the clothes of
  a fact. Either the producers start filling those elements, or a future phase publishes
  an explicitly heuristic link, clearly marked as such.
- **The INSPIRE spatial scope contradicts its own label on 6 records**, which cite
  `…/SpatialScope/global` under the label "National". The code is what the pivot model
  keeps; producers publishing a scope they do not mean is theirs to fix.
- **`cit:protocol` is empty on 85 % of the links** (2 203 of 2 584), which is why link
  typing leans on the URL.
- **1 054 of the 2 584 online resources repeat an endpoint URL**, once per layer it
  serves. Calling them repeats was the wrong reading, and phase 3 corrected it: they
  differ by `cit:name` and `cit:description`, which carry the layer. Only 9 are exact
  duplicates. See phase 3.

## Phase 3 — An overview of what the catalogue holds

Before searching the catalogue, show it. This answers the second of the two questions the
repository started from — *what data is available on the Géoplateforme?* — which no index
answers, and it publishes what the source metadata is worth, field by field.

- [x] **Aggregate the pivot catalogue** — `gpf_catalogue/stats.py`, pure like the parser:
      counts by type, topic category, INSPIRE theme, link type and publication year, plus
      the coverage of every optional field, written to a deterministic `data/stats.json`
- [x] **A static overview site** — `uv run scripts/build_site.py` writes `site/`: a
      dashboard, a faceted record explorer and a quality report, reading `catalogue.json`
      in the browser. No server, no runtime dependency, no CDN — the repository still
      ships data, and the site is one more artifact built from it
- [x] **Facet on what has cardinality**, measured rather than assumed: `type` (3 values),
      `topicCategories` (19 values, 93.3 % coverage), `inspireThemes` (79, long tailed),
      link types (8, exposed as *can I download it, query it as WFS, view it as WMS*), and
      `suspectedTest` as a toggle that is off by default. `keywords` stays search only:
      638 distinct values for 1 749 occurrences, 432 of them used once, and the two most
      frequent — `National` (123) and `données ouvertes` (112) — separate nothing
- [x] **A quality report, not a landing page** — the 336 / 333 / 326 funnel, the 3 records
      `mdb-full.xsl` cannot serve, the 7 with no identification block, the one left without
      a title, the 14 flagged as tests, the coverage of each field, the 4 links carrying
      neither a name nor a description, and the 163 records declaring no licence
- [x] **Coverage figures generated, not typed** — `scripts/stats.py --format markdown`
      emits the coverage of every field as a markdown table, measured over the current
      catalogue, so the figures [README.md](README.md) and [docs/model.md](docs/model.md)
      quote stop being numbers someone remembered to update. `stats.py` reads the field
      list from the model, so a new field is counted without being registered anywhere
- [x] Unit tests on the aggregation, running offline like the parser tests, including the
      byte stability of `stats.json`
- [x] **Every view has a URL** — the overview was one document with three tab buttons
      and a `<details>` per record, so nothing in it could be linked to: not a record,
      not a search, not a tab, and the Back button did nothing. It is now a React
      application with `react-router` and four routes — `/overview`, `/records`,
      `/records/{fileIdentifier}`, `/quality` — with the filters carried in the query
      string ([issue #2](https://github.com/mborne/gpf-catalogue/issues/2)). The site
      stays static data: `catalogue.json` and `stats.json` published beside it and read
      in the browser, React bundled rather than fetched from a CDN, and a `404.html`
      copy of the entry document so a link to a record survives being pasted somewhere.
      The cost is a build step the repository did not have — npm and Vite next to uv —
      and it is what a record page is worth: phase 4 will want to hand a model and a
      human the same link to a resource
- [x] **Links kept flat, with their descriptions** — browsing the overview showed the
      model collapsing every entry of an endpoint into one, which dropped 1 179 layer
      names and left a whole WFS service named `BDTOPO_V3:aerodrome`. Entries are now one
      per published resource, carrying `cit:name` *and* `cit:description`, and the page
      lists them raw — protocol, URL, name, description — so the repetition stays visible

Answered along the way: whether an overview needs a server. It does not, at this size —
1.2 MB of `catalogue.json` filters in the browser faster than a round trip, and the whole
site is a bundle and two JSON documents that any static host serves. The trade flips
somewhere in the thousands of records, which is phase 4, not a bigger page.

Answered along the way: whether a router needs one either. Also no, but it needs two
things a single page did not — the deployment prefix at build time, because a route is a
real path, and a `404.html` that *is* the application, because a static host has no
rewrite rule. Both are written down in [docs/overview.md](docs/overview.md); the second
means a cold deep link answers 404 with the right document, which no static host can
improve on.

Answered along the way, twice over: where aggregation belongs. Not in the model. The
catalogue publishes one entry per layer, and collapsing them looked like tidying until
the page showed what was lost — 1 179 layer names, and a WFS service labelled after its
first layer. The model keeps what was published, and the page shows it raw:
tidying it away would hide what a consumer actually has to deal with.

Found along the way, and worth knowing before building a lexical index: **the word
*pont* appears in exactly one of the 326 records**, and it is not a dataset about
bridges. The question `docs/why.md` opens with — *which dataset contains bridges?* — is
not answered by matching words against this catalogue, however it is indexed. Keeping the
layer names did widen what is reachable, though: *batiment* now matches 8 records where
it matched almost none, because the theme is written in the layers, not in the abstract.

### What the overview derives, and what it refuses to

The pivot model is unchanged by this phase: everything below is computed for display, and
each rule is written down in [docs/overview.md](docs/overview.md).

- **The publisher facet is built on the contact email domain, not on `producer`.** 134
  distinct spellings describe far fewer organisations — IGN alone appears as
  `INSTITUT NATIONAL … (IGN)` 82 times, `Institut national … (IGN-F)` 19 and `BETA-IGN`
  15. The domain is a value the record carries (98.2 % coverage, `ign.fr` on 119 records);
  a normalised organisation name would be an editorial decision, and the catalogue would
  be credited with a fact it never stated.
- **Licences are grouped through an explicit published mapping**, not by string
  similarity. There are 10 raw values, and the two most frequent are the same Licence
  Ouverte twice — 100 records, and 28 more carrying the Etalab URL glued to the label,
  which `_strip_repeated_href` leaves alone because it is not an exact trailing repeat.
  Five families cover all of them. `licence: null` is a bucket of its own, 163 records
  strong — the largest one — and reads as undeclared, never as open.
- **No map, and no territory label derived from `bbox`.** The boxes are real but barely
  discriminating: `(-5.15, 41.32, 9.57, 51.1)` is declared by 81 records and
  `(-180, -90, 180, 90)` by 24. Binning them into *métropole / outre-mer / monde* would
  publish a classification the producers never made. A spatial filter waits for phase 4.
- **No dataset to service relation**, for the reason phase 2 established: `srv:operatesOn`
  and `mdb:parentMetadata` appear zero times.

## Phase 4 — Search and MCP

- [ ] Index the pivot catalogue (lexical first, it is only 326 records), with
      `inspireThemes`, `topicCategories` and `type` as facets — the cardinalities measured
      in phase 3 make `bbox` a spatial filter rather than a facet
- [ ] Evaluate on real questions: *which dataset contains bridges?*, *which service computes
      an elevation?*, *what is available on land use?*
- [ ] Expose an MCP server: `search_catalogue`, `describe_resource`, and
      `catalogue_overview` answering from the phase 3 aggregates
- [ ] Decide how it relates to [geocontext](https://github.com/ignfab/geocontext): separate
      server, or a catalogue tool contributed there
- [ ] Return links a model can act on, so search results lead to actual data access —
      including the record's own page, which phase 3 gave it an address for

## Phase 5 — Keep it current

- [ ] Incremental refresh based on the record revision date, rather than a full harvest
- [x] CI checking that the pipeline still runs against the live service —
      [`.github/workflows/pages.yml`](.github/workflows/pages.yml) harvests, parses
      and rebuilds weekly, and refuses to publish a catalogue of fewer than 300
      records rather than quietly shipping a truncated one
- [ ] Track catalogue drift: new, removed and modified records between two harvests
- [x] Publish the overview site on GitHub Pages —
      <https://mborne.github.io/gpf-catalogue/>, rebuilt weekly. It carries
      `catalogue.json` and `stats.json`, so publishing the page publishes the data:
      consumers do not each re-harvest, and the figures are readable without cloning

## Deliberately out of scope for now

- Mirroring the data itself — this project catalogues resources, it does not copy them.
- Harvesting other CSW services. The model should not be Géoplateforme specific, but the
  harvest is, and generalizing before the second catalogue exists would be guesswork.
- Writing back to the catalogue. This project is read-only.
