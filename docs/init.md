# How this repository was bootstrapped

*Author: Claude (Anthropic) — this document, like the rest of this repository, is AI generated.*

This repository was created on 2026-09-20 from a single instruction, kept here verbatim so
that the origin of the choices made below stays auditable. The prompt is in French; the
code, comments and documentation are in English, as it asks.

## The original instruction

> La Géoplateforme offre une fonctionnalité de recherche ( https://cartes.gouv.fr/rechercher-une-donnee/ ) qui présente des jeux de données et des services ( https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-TOPO ) et des services ( ex : https://cartes.gouv.fr/rechercher-une-donnee/service/GeoPF_Altimetrie ).
>
> En coulisse, cette fonctionnalité s'appuie sur des fiches de métadonnées ISO 19115. Ex :
>
> - https://data.geopf.fr/csw?REQUEST=GetRecordById&SERVICE=CSW&VERSION=2.0.2&OUTPUTSCHEMA=http://standards.iso.org/iso/19115/-3/mdb/2.0&elementSetName=full&ID=IGNF_BD-TOPO pour BDTOPO
> - https://data.geopf.fr/csw?REQUEST=GetRecordById&SERVICE=CSW&VERSION=2.0.2&OUTPUTSCHEMA=http://standards.iso.org/iso/19115/-3/mdb/2.0&elementSetName=full&ID=GeoPF_Altimetrie pour le service altimétrie
>
> De nombreuses informations sont présentes dans ces fiches (liens WFS, service de téléchargement,...). Toutefois, elles sont loin d'être "AI ready" pour permettre une exploitation par un LLM :
>
> - Rechercher une données par mot clé (ex : dans quel jeu de données peut-on trouver les ponts)
> - Découvrir les données disponibles (ex : quels sont les données disponibles sur la Géoplateforme)
>
> A travers ce dépôt gpf-catalogue, nous allons procéder dans un premier temps comme suit :
>
> - Expliquer la démarche à travers un doc "docs/why.md" où tu expliqueras pourquoi un LLM ne peut pas tout simplement être branché sur un CSW
> - Définir un modèle pivot (Dataset, Service,...) le plus plat possible en commençant par récupérer un minimum d'information (fileIdentifier, title, abstract)
> - Scrapper les fiches de métadonnées du service CSW ( https://data.geopf.fr/csw ) dans data/csw/{fileIdentifier}.xml
> - Parser ces fiches de métadonnées pour les convertir dans le modèle pivot data/csw/{fileIdentifier}.json
>
> Par la suite :
>
> - Nous compléterons le modèle (producteur de la donnée, contact, liens WFS, liens service de téléchargement,...)
> - L'indexation des données pour permettre une recherche par LLM avec la création d'un MCP
>
> Au niveau technique :
>
> - Nous travaillerons avec le langage python
> - Le code, les commentaires et la doc doivent être en anglais
>
> Rédige un README.md et une ROADMAP.md pour débuter ces travaux. Converse une trace de cette commande dans "docs/init.md". Si tu as des questions, n'hésite pas.

## Decisions taken

Four questions were asked before writing any code:

| Question | Decision |
|---|---|
| Scope of the first iteration | Documentation **and** working code: the harvest and the parser were run for real against the live service |
| Pivot model implementation | **Pydantic v2** — validation plus a JSON schema that doubles as the contract for downstream consumers |
| What goes into git | **`data/` is ignored entirely**: it is a rebuildable mirror, not source |
| Repository setup | `git init` and uv scaffolding, **no commit** — the first commit is the author's |

## What the service actually looks like

The CSW endpoint was probed before designing anything. These measurements shaped the code
and are the source of the figures quoted in [why.md](why.md):

| Observation | Value |
|---|---|
| Records published | 336 (163 `dataset`, 154 `series`, 19 `service`) |
| Listing identifiers | one `GetRecords` call, `typeNames=csw:Record`, `elementSetName=brief` |
| Fetching a record | `GetRecordById`, `outputSchema=…/mdb/2.0`, `elementSetName=full` |
| Record size | 40 KB to 200 KB |
| Title and abstract | `mri:citation/cit:CI_Citation/cit:title` and `mri:abstract`, under `mri:MD_DataIdentification` or `srv:SV_ServiceIdentification` |
| Text encodings in use | `gco:CharacterString`, `gcx:Anchor`, `lan:PT_FreeText` |
| `AnyText` CQL filtering | broken server side, returns an `UnknownFormatConversionException` |

Three findings changed the implementation:

1. **A dozen records have no title.** `title` is therefore optional in the model, and the
   parser reports the gap rather than dropping the record or inventing a title.
2. **Identifiers are not safe file names.** Spaces, accents, parentheses, a trailing `.xml`,
   and the case-only pairs `id`/`ID` and `test`/`TEST`. File names are percent encoded, and
   case collisions are disambiguated with a short hash computed over the whole catalogue —
   otherwise a record would be silently overwritten on macOS or Windows.
3. **`GetRecordById` rather than splitting `GetRecords` pages.** Four `GetRecords` calls
   would fetch everything, but splitting a page means re-serializing the XML, which
   renumbers its 31 namespace prefixes. Per-record fetching keeps `data/csw/*.xml` byte
   identical to what the service sent, and makes the harvest resumable.

## Result of the first run, 2026-09-20

```
=== Harvest summary ===        === Parse summary ===
listed     : 336               records : 333
downloaded : 333               written : 326
failed     : 3                   dataset : 155
                                 series  : 152
                                 service : 19
                               no title: 1
                               failed  : 7
```

11 MB of XML in, 326 pivot records out. The 3 harvest failures are records the service
cannot transform to ISO 19115-3; the 7 parse failures are records published without any
identification block. Both are listed in [ROADMAP.md](../ROADMAP.md#known-issues-left-open).

## Reproducing the result

```bash
uv sync
uv run scripts/harvest.py     # 333 records into data/csw/*.xml
uv run scripts/parse.py       # 326 pivot records into data/csw/*.json
uv run pytest
```

## Authorship

This repository is an experimentation, and is almost entirely written by Claude (Anthropic)
through Claude Code, from the instruction above. So that this stays visible in the files
themselves and not only in the README, every generated file carries an author line:

| File kind | Where the attribution lives |
|---|---|
| Python (`gpf_catalogue/`, `scripts/`, `tests/`) | a comment right below the module docstring, so it stays out of `--help` output |
| Markdown (`README.md`, `ROADMAP.md`, `CLAUDE.md`, `docs/*.md`) | a line below the title |
| `pyproject.toml`, `.gitignore` | a header comment; `pyproject.toml` also declares PEP 621 `authors` / `maintainers` |
| [`pivot-schema.json`](pivot-schema.json) | a `$comment` key, since JSON has none — emitted by `scripts/export_schema.py`, so it survives regeneration |
| HTML, CSS and JavaScript (`gpf_catalogue/web/`) | a comment on the first line, below the doctype for HTML |
| GitHub Actions workflows (`.github/workflows/*.yml`) | a header comment, above the `name:` key |
| `tests/data/dataset.xml`, `no-title.xml`, `anchor-no-scope.xml` | an XML comment |

Four files carry none, on purpose:

- `tests/data/GeoPF_Altimetrie.xml` — a record served verbatim by the Géoplateforme. It was
  not authored here, and the point of the fixture is that it is what the service sent.
- `LICENSE` — MIT boilerplate. Copyright and ownership are the maintainer's, not Claude's.
- `uv.lock` — resolved by uv, not written here.
- `.python-version` — a bare value, with no comment syntax.

Ownership is unchanged by any of this: the repository is reviewed, merged and licensed by
[@mborne](https://github.com/mborne). Attribution records how the code was produced, not who
is responsible for it.
