# Why a LLM cannot simply be plugged into a CSW service

*Author: Claude (Anthropic) — this document is AI generated, see [init.md](init.md).*

The Géoplateforme catalogue is already available through an open, standard, well documented
interface: a CSW 2.0.2 service at [`https://data.geopf.fr/csw`](https://data.geopf.fr/csw),
serving ISO 19115-3 metadata records. It is the interface that powers
[cartes.gouv.fr](https://cartes.gouv.fr/rechercher-une-donnee/).

So why build anything else? Because the two questions we want a LLM to answer —

> *Which dataset contains bridges?*
>
> *What data is available on the Géoplateforme?*

— are questions that CSW, as deployed, cannot answer, and that ISO 19115-3 records, as
served, cannot be fed to a model to answer either.

All figures below were measured against the live service on 2026-09-20.

## 1. The protocol is not a search API a model can drive

A `GetRecords` call is not a query string. It is a combination of `typeNames`,
`outputSchema`, `elementSetName`, `resultType`, `constraintLanguage`, `startPosition` and
`maxRecords`, plus a constraint expressed in CQL or in OGC Filter XML. Getting a model to
emit that reliably is possible, but it buys very little, because:

- **There is no relevance ranking.** CSW filters, it does not rank. A query either matches
  a record or it does not, and the service returns matches in catalogue order with no
  score. "Which dataset contains bridges?" is a ranking question, not a filtering one.
- **Full text search is broken on this deployment.** The obvious query,
  `constraint=AnyText like '%pont%'`, returns an `ows:ExceptionReport` carrying
  `java.lang.RuntimeException: java.util.UnknownFormatConversionException: Conversion = 'p'`
  — a server side formatting bug triggered by the `%` wildcard. The one queryable that
  would support keyword search is unusable.
- **Errors arrive with HTTP 200.** OWS services report failures in the body, not in the
  status code. Any client, model-driven or not, has to inspect the XML to know whether it
  succeeded.

Even where it works, `AnyText` matches substrings, not meaning. It will not connect
*bridges* to a record whose abstract mentions *ouvrages d'art*.

## 2. The payload does not fit, and is mostly not the answer

One record, `IGNF_BD-TOPO`, fetched with `GetRecordById`:

| | |
|---|---|
| Size | **201 813 bytes** |
| XML elements | 2 456 |
| Distinct namespace prefixes | 31 |
| Title + abstract | 1 413 characters, i.e. **0.7 %** of the document |

The whole catalogue is 336 records, roughly 10 to 15 MB of XML. Pushing that into a context
window is out of the question, and pushing a single record is already wasteful: 99.3 % of
it is coordinate reference system declarations, quality statements, distribution options
and lineage — real information, but not what answers "what is this dataset about?".

Retrieval has to happen *before* the model sees anything. Which brings the next problem.

## 3. Naive RAG over the raw XML retrieves markup, not meaning

Chunking these documents and embedding the chunks does not work well:

- Every chunk repeats the same namespace boilerplate, so chunks look alike to an embedding
  model regardless of what they describe.
- Chunk boundaries fall inside ISO structures, cutting a value away from the element that
  gives it meaning.
- The signal is diluted: the useful sentence is surrounded by two hundred lines of
  structural markup.

## 4. The same fact has several shapes

ISO 19115-3 offers more than one way to say the same thing, and the catalogue uses them all.

- **A title can be three different things**: a plain `gco:CharacterString`, a `gcx:Anchor`
  pointing at a register entry, or a multilingual `lan:PT_FreeText`. 19 of the first 100
  records carry an English translation alongside the French title.
- **Datasets and services do not share an element name**: the title of a dataset lives under
  `mri:MD_DataIdentification`, the title of a service under `srv:SV_ServiceIdentification`.
  Same question, two paths.
- **ISO 19115-3 split the former single `gmd` namespace into a dozen** (`mdb`, `mcc`, `mri`,
  `srv`, `cit`, `lan`, `gco`, `gcx`, …), so even a simple extraction needs a namespace map.

Every consumer — a search index, an MCP server, a notebook — would otherwise have to
reimplement these rules, and would get them subtly differently.

## The data is not clean

Harvesting the whole catalogue surfaces what a per-record view hides:

- **Eight records have no usable title.** Seven of them — `ddt74_instal_photovoltaique_*.xml`
  and friends — are published with a scope and an identifier but *no identification block
  whatsoever*, which is not valid ISO. The eighth, `VIGINOND_Atelier_metadata`, has the
  block but no title, and an abstract full of `xxxx` placeholders.
- **Three records cannot be served in ISO 19115-3 at all.** `GetRecordById` on
  `IGNF_BD-TRANSPORTS-EXCEPTIONNELS`, `MTECT_CORINE-LAND-COVER` and
  `fr-662043116-7D3DC709-E1EB-470B-9FD0-8ABF8AAFD8E4` returns
  `Error occured while transforming metadata with id '…' using 'mdb-full.xsl'`. The same
  records are served fine in the older `gmd` schema.
- **Identifiers are not file names.** Three contain spaces, accents and parentheses; nine
  already end in `.xml`; one is `1.0`; and two pairs — `id`/`ID` and `test`/`TEST` — differ
  only by case, which silently overwrites a record on a case insensitive file system.
- **Test records are published alongside real ones**: `test`, `TEST`, `1`, `lls`,
  `blba lbla`.

Out of 336 published records, a full run harvests 333 and converts 326.

None of this is a reason to distrust the catalogue — it is a reason to normalize it once,
in one place, and to *report* the anomalies instead of letting each consumer trip over them.
A model asking "what is available?" should get 326 answers it can use, not 336 documents it
has to sanity check.

## What the pivot model changes

| | Raw ISO 19115-3 record | Pivot record |
|---|---|---|
| Size | 40 KB – 200 KB | under 2 KB |
| Structure | nested, 31 namespaces | flat, no namespace |
| Vocabulary | depends on dataset vs service | one shape for every resource |
| Rankable | no | yes, once indexed |
| Readable by a model | no | directly |

The pivot model is **lossy on purpose**. It is not a replacement for the metadata records:
the raw XML stays in `data/csw/*.xml`, and every pivot record keeps its `fileIdentifier`,
so a model that has found a resource can always be pointed back at the authoritative
record — or at its page on cartes.gouv.fr.

What this unlocks, in order (see [ROADMAP.md](../ROADMAP.md)):

1. **Enumerate** — "what is available?" becomes reading 336 short documents instead of 15 MB
   of XML.
2. **Index and rank** — flat text is what a search index, lexical or semantic, expects.
3. **Serve** — an MCP server exposing `search` and `describe` over the pivot catalogue,
   so the model asks a question instead of building an OGC request.
