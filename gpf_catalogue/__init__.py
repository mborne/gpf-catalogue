"""AI-ready catalogue of the Géoplateforme.

Responsibilities:

- harvest ISO 19115-3 metadata records from the Géoplateforme CSW service,
- convert them into a flat pivot model that a LLM can actually consume.

Organization:

- `model`: the pivot model (what we expose),
- `csw`: the CSW client (how we talk to the catalogue service),
- `harvest`: download raw records to `data/csw/{fileIdentifier}.xml`,
- `parse`: convert raw records to `data/csw/{fileIdentifier}.json`.
"""

__version__ = "0.1.0"
