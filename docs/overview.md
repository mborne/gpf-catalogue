# The overview

*Author: Claude (Anthropic) — this document is AI generated, see [init.md](init.md).*

A static site over the pivot catalogue: what the Géoplateforme publishes, what can
be reached, and what the metadata is missing. It answers the second of the two questions
this project started from — *what data is available?* — which a search index does not
answer, and it is the phase 3 deliverable of [ROADMAP.md](../ROADMAP.md).

```bash
uv run scripts/parse.py          # produces data/catalogue.json
uv run scripts/stats.py          # aggregates it into data/stats.json
npm ci --prefix web              # once: the front end dependencies
npm run build --prefix web       # builds web/dist
uv run scripts/build_site.py     # assembles site/ from web/dist + the data
uv run scripts/serve_site.py     # serves it on http://localhost:8000
```

The published copy, rebuilt weekly from the live service, is at
<https://mborne.github.io/gpf-catalogue/>.

The site is published by an individual and is **not** an IGN or Géoplateforme site. It
says so on every page, in a notice placed ahead of every figure it qualifies rather than
in the footer: a catalogue overview is easy to mistake for the catalogue's own. The
notice names the authoritative source, states that the figures are a weekly copy, and
links the [mentions légales](https://mborne.github.io/mentions-legales/), which the
footer repeats. The `<title>` carries the word too, on every route, since that is what a
search result and a bookmark show. A plain `file://` open does not work: the page fetches
its two JSON documents, and browsers refuse cross origin `file://` requests.

The site is **static data**: `catalogue.json` and `stats.json` are published beside it
and read in the browser. There is no API and no server-side rendering, and nothing is
loaded from a network at runtime — React is bundled into the copied assets, not fetched
from a CDN, which is what keeps the result a directory anyone can serve, zip or publish
as a release artifact (ROADMAP phase 5).

## A record has a URL

Everything below is reachable by a link, which is what the [rewrite of
issue #2](https://github.com/mborne/gpf-catalogue/issues/2) was for. The page used to be
one document with three tab buttons and a `<details>` per record, so the only way to
point at `IGNF_BD-TOPO` was a sentence describing which filters to type.

| Route | What it shows |
|---|---|
| `/overview` | The dashboard. The entry point redirects here, so the section being looked at is always written in the URL |
| `/records` | The faceted search. Every filter is a query parameter: `/records?theme=Altitude&link=wfs` |
| `/records/{fileIdentifier}` | One record, on its own page |
| `/quality` | The quality report |

Two consequences are worth stating, because they are what the routes cost:

- **The bundle has to know its deployment prefix.** A route is a real path, so
  `/gpf-catalogue/records/IGNF_BD-TOPO` must resolve its script against the site root
  rather than against the record — which rules out relative asset URLs. The prefix is a
  build time value, `VITE_BASE`, defaulting to `/`; the Pages workflow reads it from
  `actions/configure-pages` and hands the same value to the router as its basename.
- **A static host has no rewrite rule.** The build writes `404.html` as a byte copy of
  `index.html`, which is what GitHub Pages serves for an unknown path, so a link to a
  record pasted into a browser boots the application and renders the record. The HTTP
  status of that first response is 404 — the document is right, the code is the host's,
  and no static host can do better without a rewrite rule. `python -m http.server` has
  no such convention, which is why `scripts/serve_site.py` exists: it serves the entry
  document for the application's routes and keeps a missing asset a real 404.

The record page is also where the search links to: a result row is a link, not a
disclosure triangle. And on the dashboard, a bar whose value is a facet leads to the
records it counts — `/records?type=service` — so a number on a chart became a question
the search answers rather than something to reproduce by hand in the filters.

## What it shows

| Page | Question it answers |
|---|---|
| **Overview** | What is in the catalogue: resources by type, by ISO topic category, by INSPIRE theme, by spatial scope, by publisher, by licence family, by publication year, and which access protocols are offered. |
| **Records** | Which resource matches a need: full text filtering on title, abstract, identifier, keywords **and layer names**, combined with facets. |
| **One record** | Everything the catalogue published about one resource, including every access link, raw. |
| **Quality** | What the source metadata is missing: coverage of every field of the pivot model, and the anomaly counts below. |

Filtering happens in the browser, over `catalogue.json` as a whole — 1.2 MB for 326
records, which is small enough that paging, a server and an index are all unnecessary at
this size. Both documents are loaded once, at the root, so moving from the search to a
record refetches nothing. When the catalogue grows past a few thousand records, that
trade changes, and that is what phase 4 is for.

A filter change **replaces** the history entry rather than pushing one. Typing eight
characters is one search, not eight, and Back has to lead out of the page — to the chart
the filter came from, or to the record just closed — rather than through a transcript of
keystrokes. The URL still carries the current state at every point, so it can be copied
at any time.

## Derived values, and their rules

The pivot model is **not modified** by the overview. The three values below are computed
for display by [`gpf_catalogue/stats.py`](../gpf_catalogue/stats.py) and written to
`stats.json`. Each is a published rule, so a reader can check why a record landed where
it did.

### Publisher is the contact email domain

The facet is built on the domain of `contactEmail`, lowercased — `ign.fr` on 119
records, `developpement-durable.gouv.fr` on 29 — and not on `producer`.

`producer` carries **134 distinct spellings** for far fewer organisations. IGN alone
appears as `INSTITUT NATIONAL DE L'INFORMATION GEOGRAPHIQUE ET FORESTIERE (IGN)` 82
times, `Institut national de l'information géographique et forestière (IGN-F)` 19 times
and `BETA-IGN` 15 times. Folding those three into one organisation would be correct, and
it would still be *our* editorial decision presented as something the catalogue said.
The domain is a value the record actually carries, on 98.2 % of them.

The consequence is stated rather than hidden: a producer who publishes under a personal
or a delegated address is attributed to that domain. `producer` remains visible on every
record detail, spelled exactly as published.

### Licence families come from a published mapping

`licence_family()` tries an ordered list of substrings against the casefolded licence
string, and the list is the whole rule:

| Family | Matched on | Records |
|---|---|---:|
| Licence Ouverte | `licence ouverte`, `open license` | 129 |
| Terms of use of cartes.gouv.fr | `cartes.gouv.fr/cgu` | 19 |
| No condition stated | `pas de restriction`, `aucune restriction`, `no conditions` | 7 |
| Terms of use of the producer | `conditions générales` | 6 |
| ODbL | `odbl`, `open database license` | 2 |
| **Undeclared** | `licence` is null | **163** |

Two properties of that table matter more than the grouping itself. The catalogue
publishes 10 distinct licence strings, and the two most frequent are the *same* Licence
Ouverte: 100 records carry it bare, 28 more carry it with the Etalab URL glued to the
label — which `_strip_repeated_href` leaves alone, because it is not an exact trailing
repeat of the `xlink:href`. And the largest bucket by far is the one where nothing was
declared at all: it reads **Undeclared**, never *open*.

A licence matching no rule falls into `Other, as published` rather than into the nearest
family. That bucket is meant to stay near zero; if it grows, the mapping needs a rule,
which is exactly what it is there to tell you.

### Publication year prefers `published`, falls back on `created`

Only 47.2 % of the records carry a publication date, so a histogram built on it alone
would describe half the catalogue. `created` (57.1 %) is used when `published` is
absent. A record carrying neither is **left out of the histogram**, not bucketed as
unknown: a bar labelled *unknown* on a time axis is not a year.

A year in which nothing was published keeps a column, at zero. The catalogue publishes
nothing between 1994 and 2008, and drawing those two as adjacent columns would draw a
gap as if it were a step — the axis would no longer be time.

The site reads each record's publisher, licence family and year from `recordFacets` in
`stats.json` rather than recomputing them. Two implementations of one rule are two
rules, and the one in `stats.py` is the one the charts count with.

## The spatial scope is read, not derived

`spatialScope` is a field of the pivot model, so the page reads it from the record
rather than from `recordFacets` — there is no rule to publish, only a code the record
cites. The chart counts it, `national` 118, `global` 6, `regional` 5,
`local` 4, `european` 3 — and closes with **Not stated 190**
([issue #3](https://github.com/mborne/gpf-catalogue/issues/3)).

That last bar is the complement of the code list, not a value of it, and the chart says
so by where it puts it: the five codes stay ranked among themselves, then a rule, then
the records that cite nothing — in a muted italic, below the values it is not one of.
It keeps the single bar colour, because it is the same records counted the same way; a
second hue would be one more thing for the chart to explain.

The chart was built without it at first, on the argument that an undeclared scope is not
a scope and that a bar labelled *undeclared* would be the tallest one on a chart about
extent. It is the tallest one, and that is the finding: **58 % of the catalogue cites no
spatial scope at all**. Leaving it out made the chart describe 136 records while looking
like it described 326, which is the more misleading of the two. The year histogram still
leaves undated records out, for a reason that does not transfer — its axis is time, and
*unknown* is not a year; this axis is a code list, and *nothing* is a possible answer.

The count is `quality.undeclaredSpatialScope`, measured by `stats.py` and read from
`stats.json` — the page does not subtract it from the bars. `bySpatialScope` itself stays
a list of code list values, so a consumer of `stats.json` never finds *Not stated* mixed
in with `national`.

The same bar filters: it links to `/records?scope=(not stated)`, the option the facet has
always carried next to the five codes, which matches on `spatialScope` being null.

On the Records page it is a facet, and a badge next to the resource type on every
record summary — the question *national product or local data?* is asked while scanning
the list, not after opening a record. A record citing no scope carries no badge, rather
than one reading *unknown*: a row of the list is one record, where a bar is a group, and
*this record did not say* is what the absent badge already means.

The label is not what is counted. 6 records cite `…/SpatialScope/global` under the
label "National", so the keyword `National` — the most frequent of the catalogue, 123
records — and the code `national` — 118 records — are not the same set. See
[model.md](model.md#where-and-when).

## What the overview refuses to derive

- **No map, and no territory label built from `bbox`.** The boxes are real, but they
  barely discriminate: `(-5.15, 41.32, 9.57, 51.1)` is declared by 81 records and
  `(-180, -90, 180, 90)` by 24, out of 139 distinct boxes. Binning them into
  *métropole / outre-mer / monde* would publish a classification no producer made —
  where `spatialScope` is a classification the producers *did* make, which is why it is
  counted and a box is not. A spatial filter belongs to phase 4, where it can be a real
  geometric test.
- **No keyword facet.** 638 distinct keywords for 1 749 occurrences, 432 of them used
  once, and the two most frequent — `National` (123) and `données ouvertes` (112) —
  separate nothing. Keywords are searched, and only those shared by at least 5 records
  are displayed at all.
- **No dataset to service relation.** `srv:operatesOn` and `mdb:parentMetadata` appear
  **zero** times in the 333 harvested records. Reconstructing the relation from URL or
  title similarity would be a guess wearing the clothes of a fact.

### Abstracts are rendered as Markdown, the links table is not

Abstracts are written in Markdown and the catalogue stores them that way: 94 of the 326
use `**bold**`, 36 carry a list, 16 a link, 167 contain line breaks. Showing the
asterisks shows the source's markup instead of its text, so the page renders paragraphs,
lists, headings, bold, italic, code and links.

It stops there, and it stops at abstracts. Link names and descriptions are left exactly
as published: 155 of them contain `*` or `_` inside a layer name such as
`trichls_s_d51_gpkg_07-10-2024_wfs`, which any Markdown renderer would eat.

The renderer also undoes what the source escaped twice — five abstracts read
`INFO&amp;SOLS` or `&lt; 5 bâtiments` — and turns the stray `<br />` of one record into
line breaks.

Nothing here builds HTML from catalogue text. Every branch of the renderer creates DOM
nodes, and anything it does not recognise becomes a text node, so a `<script>` in an
abstract is displayed rather than run. That is not theoretical: the text comes from a
third party service over which this project has no control.

### Links are shown raw

One row per entry the catalogue published — protocol, URL, name, description — sorted by
protocol, then URL, then name. No grouping, no folding, no tidying: `IGNF_BD-TOPO` shows
all 178 rows, of which 109 are the same WFS URL repeated once per feature type.

That repetition is the point. Tidying it in the page would hide what a consumer of this
catalogue actually has to deal with, and the table is where the source's shape becomes
obvious: the same endpoint under four spellings, 332 entries with no description, two
different products (`BDTOPO_V3:` and `BDTOPO_V3_DIFF:`, 59 and 50 layers) behind one URL,
and a layer name carrying a literal tab character —
`BDTOPO_V3_DIFF:commune_associee_ou_deleguee\tB`. None of it is cleaned up on the way in.

Grouping stays available to whoever wants it: the model is flat, so a consumer folds it
on `(type, url)` in two lines. The reverse is not true, which is why the model does not
fold it first.

## The anomalies the quality page reports

Measured over the 326 records of the pivot catalogue, unless stated otherwise. These are
properties of the source catalogue, not defects of this pipeline; they are published so
that they can be acted upon.

| Anomaly | Count |
|---|---:|
| Records declaring no licence | 163 |
| Records declaring no limitation on public access | 176 |
| Records citing no INSPIRE spatial scope | 190 |
| Links carrying neither a name nor a description | 4 of 2 575 |
| Links carrying no description | 332 of 2 575 |
| Distinct spellings of `producer` | 134 |
| Records offering no access link at all | 5 |
| Records flagged as test publications | 14 |
| Records published with no title | 1 |

Three more sit outside the pivot catalogue, because they never reached it, and the page
names them as such:

- **3 records cannot be served as ISO 19115-3**, the service failing on `mdb-full.xsl`:
  `IGNF_BD-TRANSPORTS-EXCEPTIONNELS`, `MTECT_CORINE-LAND-COVER` and
  `fr-662043116-7D3DC709-E1EB-470B-9FD0-8ABF8AAFD8E4`. They exist in the older `gmd`
  schema.
- **7 records are published with no identification block**, so they have neither title
  nor abstract and are counted as parse failures.
- The full funnel is therefore **336 published → 333 harvested → 326 in the catalogue**.

## How it is built

`web/` is a npm project — React, react-router and Vite, in TypeScript — and
`scripts/build_site.py` copies its `web/dist` next to the two JSON documents. So the
site has a build step, which the repository did not have before, and two directories
that are rebuildable rather than source: `web/node_modules` and `web/dist`, gitignored
like `data/` and `site/`. `web/package-lock.json` **is** versioned: it is what makes the
published bundle reproducible.

| Path | What lives there |
|---|---|
| `web/src/types.ts` | The reader's side of the pivot model contract, mirroring `model.py` and `stats.py`. A field added to the model is added here too |
| `web/src/catalogue.tsx` | Loading `catalogue.json` and `stats.json` once, and indexing them by identifier |
| `web/src/filters.ts` | Which facets exist, which query parameter carries each, and what each one matches |
| `web/src/markdown.tsx` | The abstract renderer |
| `web/src/pages/` | One file per route |
| `web/src/components/` | The charts, the layout, a record row and a record body |
| `web/src/styles.css` | The stylesheet, carried over from the previous site rather than rewritten |

The build is deterministic: Vite names its assets after their content, there is no
timestamp anywhere, and two builds over the same catalogue produce the same bytes —
which is what makes catalogue drift diffable (ROADMAP phase 5). `build_site.py` clears
`site/assets` before copying, since a content hash means a rebuild writes new names
beside the old ones rather than over them.

Why React at all, for 326 records in a browser: four routes, a record page and a
filter state in the query string are what the previous 660 lines of hand written DOM
manipulation had started to be, without the router. React is the runtime cost —
286 KB, 91 KB gzipped, bundled and served from the site — and the routes are what it
buys. Nothing else changed: the same aggregates, the same rules, the same raw links.

## `stats.json`

One document, written beside `data/catalogue.json`, carrying every aggregate the page
displays. It has no timestamp, and every list is ordered by count descending then value
ascending, so two runs over the same catalogue produce the same bytes and a diff is a
real change — the same rule as `catalogue.json`
([model.md](model.md#design-rules)).

| Key | Contents |
|---|---|
| `source`, `count` | The CSW service, and how many records the figures cover |
| `byType`, `byTopicCategory`, `byInspireTheme` | Records per value; a record may carry several themes or categories, so these sum to more than `count` |
| `bySpatialScope` | Records per INSPIRE spatial scope. Code list values only: the records citing none are counted by `quality.undeclaredSpatialScope`, which is what the chart draws its last bar from |
| `byPublisher`, `byLicenceFamily`, `byYear` | The three derived aggregates above; `byYear` is chronological rather than ranked, and keeps empty years at zero |
| `recordFacets` | The publisher, licence family and year of each record, in catalogue order |
| `byLinkType`, `recordsByLinkType` | Links per type, and records offering at least one link of that type. The second is the one to filter on |
| `topKeywords` | Keywords shared by at least 5 records |
| `coverage` | Every optional field of the pivot model, in declaration order, with its count and share |
| `quality` | The anomaly counts of the table above, plus the identifiers of the 14 suspected test records |

`coverage` is read from `CatalogueRecord.model_fields`, not from a list maintained by
hand: a field added to the pivot model is measured without anyone remembering to
register it. `uv run scripts/stats.py --format markdown` prints that section as the
markdown table quoted by [model.md](model.md), so a figure in the documentation is
measured rather than remembered.
