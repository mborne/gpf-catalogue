# gpf-catalogue

**An AI-ready catalogue of the Géoplateforme**, built from the ISO 19115 metadata records
served by its CSW service.

The Géoplateforme already publishes a rich catalogue: 336 records describing datasets,
dataset series and web services, exposed through
[cartes.gouv.fr](https://cartes.gouv.fr/rechercher-une-donnee/) and behind it through the
CSW endpoint [`https://data.geopf.fr/csw`](https://data.geopf.fr/csw). That catalogue is
made for humans and for spatial data infrastructures — not for language models.

This project turns it into something a LLM can actually work with:

- **A flat pivot model** — one small JSON document per resource, instead of a 200 KB XML
  tree spread over a dozen namespaces.
- **A local mirror** — the raw records are harvested once, so parsing, indexing and
  experimenting never hammer the production service.
- **A reproducible pipeline** — two commands rebuild the whole catalogue from scratch.

See [docs/why.md](docs/why.md) for why a LLM cannot simply be plugged into a CSW service.

## Quick start

```bash
uv sync                                 # install the dependencies
uv run scripts/harvest.py --limit 5     # try on 5 records
uv run scripts/harvest.py               # mirror the whole catalogue (~10 min)
uv run scripts/parse.py                 # convert it to the pivot model
```

Both commands write to `data/csw/`, which is not versioned: it is a rebuildable mirror.

```bash
cat data/csw/IGNF_BD-TOPO.json
```

```json
{
  "fileIdentifier": "IGNF_BD-TOPO",
  "type": "series",
  "title": "BD TOPO®",
  "abstract": "La BD TOPO® version 3.5 contient une description vectorielle 3D (structurée en objets) des éléments du territoire et de ses infrastructures, de précision métrique. [...]"
}
```

That is 320 bytes where the source record is 201 813.

## Pipeline

| Step | Command | Input | Output |
|---|---|---|---|
| Harvest | `uv run scripts/harvest.py` | `GetRecords` + `GetRecordById` on `data.geopf.fr/csw` | `data/csw/{name}.xml` |
| Parse | `uv run scripts/parse.py` | `data/csw/*.xml` | `data/csw/{name}.json` |
| Export schema | `uv run scripts/export_schema.py` | the model | [`docs/pivot-schema.json`](docs/pivot-schema.json) |

Each command supports `--help`, and `-v` for debug logs. The harvest is **resumable**:
records already on disk are skipped, so an interrupted run is restarted by running it
again. Use `--force` to refresh them.

## Pivot model

The first version deliberately carries the strict minimum needed to identify and describe
a resource:

| Field | Type | Description |
|---|---|---|
| `fileIdentifier` | `string` | Stable identifier of the record, as used by the CSW service and by cartes.gouv.fr URLs |
| `type` | `dataset` \| `series` \| `service` | Kind of resource described |
| `title` | `string` \| `null` | Human readable name |
| `abstract` | `string` \| `null` | Free text description |

Producer, contacts, keywords and service links (WFS, WMS, download) come next — see
[ROADMAP.md](ROADMAP.md) and [docs/model.md](docs/model.md).

## Status and limits

Last full run, 2026-09-20:

| | |
|---|---|
| Records published by the service | 336 |
| Harvested | 333 |
| Converted to the pivot model | 326 |

- **Work in progress** — the model is intentionally incomplete, see [ROADMAP.md](ROADMAP.md).
- **No index, no MCP server yet** — this repository currently produces data, not a search API.
- **3 records cannot be served as ISO 19115-3.** The service answers
  `Error occured while transforming metadata with id '…' using 'mdb-full.xsl'` for
  `IGNF_BD-TRANSPORTS-EXCEPTIONNELS`, `MTECT_CORINE-LAND-COVER` and
  `fr-662043116-7D3DC709-E1EB-470B-9FD0-8ABF8AAFD8E4`. They are available in the older
  `gmd` schema; supporting it is on the roadmap.
- **7 harvested records carry no identification block at all**, so they have neither title
  nor abstract and are reported as parse failures rather than written as empty records.
- **Not every identifier is a file name** — some contain spaces or accents, nine end in
  `.xml`, and two pairs collide once compared case insensitively. The pipeline encodes and
  disambiguates them, and says so; see [docs/why.md](docs/why.md#the-data-is-not-clean).

## Documentation

- [docs/why.md](docs/why.md) — why a LLM cannot be plugged directly into a CSW service.
- [docs/model.md](docs/model.md) — the pivot model, field by field.
- [docs/init.md](docs/init.md) — how this repository was bootstrapped.
- [ROADMAP.md](ROADMAP.md) — what comes next.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```bash
uv sync
uv run pytest
```

The parser is pure (bytes in, model out) and is covered by tests running offline on the
sample records of `tests/data/`.

## See also

- [cartes.gouv.fr](https://cartes.gouv.fr/rechercher-une-donnee/) — the public search interface.
- [geocontext](https://github.com/ignfab/geocontext) — MCP server exposing Géoplateforme data to a LLM.

## License

[MIT](LICENSE)
