"""What the three Géoplateforme services say they serve, read from their inventory.

Pure, like `parse.py` and `stats.py`: `parse_inventory()` takes bytes and returns a
`ServiceInventory`. No I/O, no network, so the tests run offline against the
samples of `tests/data/`.

Each service names its resources in its own way, and the whole point of this module
is to reduce the three to one shape — a `key` a metadata record can cite, and the
`title` the service itself gives it:

| Service | Element | `key` | `title` |
|---|---|---|---|
| WFS | `wfs:FeatureType` | `wfs:Name`, the `typeName` — `BDTOPO_V3:batiment` | `wfs:Title` |
| WMTS | `wmts:Layer` | `ows:Identifier` — `ORTHOIMAGERY.ORTHOPHOTOS` | `ows:Title` |
| download | `atom:entry` | last segment of `atom:id` — `ADMIN-EXPRESS` | `atom:title` |

The WMTS case is the one that needs care: `ows:Identifier` appears 2 292 times in
the capabilities, against 712 layers, because every style and every tile matrix set
is identified the same way. Only the identifier that is a *direct child* of a layer
names the layer, which is why the paths here are anchored and never `.//`.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field

from gpf_catalogue.model import BaseRecordModel
from gpf_catalogue.services import SERVICES
from gpf_catalogue.storage import service_pages

logger = logging.getLogger(__name__)

# Namespaces of the three inventories. They are kept apart from
# `gpf_catalogue.namespaces`, which maps the ISO 19115-3 record: none of these
# appears in a metadata record, and none of those appears here.
WFS = "http://www.opengis.net/wfs/2.0"
WMTS = "http://www.opengis.net/wmts/1.0"
OWS11 = "http://www.opengis.net/ows/1.1"
ATOM = "http://www.w3.org/2005/Atom"

#: Prefix to namespace map for the inventory documents.
SERVICE_NAMESPACES = {"wfs": WFS, "wmts": WMTS, "ows": OWS11, "atom": ATOM}


class PublishedResource(BaseRecordModel):
    """One resource a service says it serves.

    Attributes:
        key: What a metadata record has to cite to describe it. The `typeName` for
            the WFS, the layer identifier for the WMTS, the resource name for the
            download service.
        title: The label the service gives it, kept as published — it is the only
            human readable thing an uncovered resource carries.
    """

    key: str = Field(description="Identifier a metadata record has to cite.")
    title: str | None = Field(
        description="Label published by the service, null when it publishes none."
    )


@dataclass
class ServiceInventory:
    """Everything one service says it serves.

    Attributes:
        service: Short name of the service, `wfs`, `wmts` or `download`.
        endpoint: URL the inventory was read from.
        resources: The resources, in the order the service listed them, deduplicated
            on `key` — first occurrence wins, as everywhere else in this project.
    """

    service: str
    endpoint: str
    resources: list[PublishedResource]

    @property
    def keys(self) -> set[str]:
        """The keys a metadata record can cite."""
        return {resource.key for resource in self.resources}


def parse_inventory(
    service: str, bodies: list[bytes], endpoint: str = ""
) -> ServiceInventory:
    """Read the inventory of one service from the bodies its endpoint returned.

    Args:
        service: `wfs`, `wmts` or `download`.
        bodies: One body per page, as `ServiceClient.fetch()` returns them. The two
            capabilities documents come in one body, the download feed in twelve.
        endpoint: URL the bodies were read from, carried into the result.

    Returns:
        The resources the service publishes, deduplicated on `key`.

    Raises:
        ValueError: If `service` is not one of the three known ones.
        ET.ParseError: If a body is not XML.
    """
    readers = {
        "wfs": _read_wfs,
        "wmts": _read_wmts,
        "download": _read_download,
    }
    if service not in readers:
        raise ValueError(f"unknown service: {service!r}")

    resources: list[PublishedResource] = []
    seen: set[str] = set()
    for body in bodies:
        for resource in readers[service](ET.fromstring(body)):
            # The download feed repeats nothing, but a WFS publishing the same
            # typeName twice would otherwise be counted twice. First value wins.
            if resource.key in seen:
                continue
            seen.add(resource.key)
            resources.append(resource)

    logger.debug("%s: %d resources", service, len(resources))
    return ServiceInventory(service=service, endpoint=endpoint, resources=resources)


def read_inventories(
    services_dir: Path, services: list[str] | None = None
) -> tuple[list[ServiceInventory], list[str]]:
    """Read the inventories mirrored by `scripts/harvest_services.py`.

    A service that was never harvested is reported as missing rather than read as
    empty: an empty inventory would say "this service serves nothing", which would
    make every record citing it an unknown claim.

    Args:
        services_dir: Directory holding the mirrored pages.
        services: Which services to read, all of the known ones by default.

    Returns:
        The inventories that could be read, in the order asked for, and the names
        of those that could not.
    """
    inventories: list[ServiceInventory] = []
    missing: list[str] = []
    for service in services or list(SERVICES):
        pages = service_pages(services_dir, service)
        if not pages:
            logger.warning("no %s inventory in %s", service, services_dir)
            missing.append(service)
            continue
        bodies = [page.read_bytes() for page in pages]
        endpoint = SERVICES[service].url if service in SERVICES else ""
        inventory = parse_inventory(service, bodies, endpoint=endpoint)
        logger.info(
            "%s: %d resources from %d page(s)",
            service,
            len(inventory.resources),
            len(pages),
        )
        inventories.append(inventory)
    return inventories, missing


def _read_wfs(root: ET.Element) -> list[PublishedResource]:
    """Read the feature types of a WFS 2.0 capabilities document."""
    return _collect(
        root.findall("wfs:FeatureTypeList/wfs:FeatureType", SERVICE_NAMESPACES),
        key_path="wfs:Name",
        title_path="wfs:Title",
    )


def _read_wmts(root: ET.Element) -> list[PublishedResource]:
    """Read the layers of a WMTS 1.0 capabilities document.

    Anchored on `wmts:Contents/wmts:Layer`: a `.//ows:Identifier` would also pick
    up every style and every tile matrix set, which is three identifiers out of
    four in this document.
    """
    return _collect(
        root.findall("wmts:Contents/wmts:Layer", SERVICE_NAMESPACES),
        key_path="ows:Identifier",
        title_path="ows:Title",
    )


def _read_download(root: ET.Element) -> list[PublishedResource]:
    """Read the resources of one page of the INSPIRE Atom download feed.

    The key is the last segment of `atom:id`, not the entry title: the id is the
    resource URL — `https://data.geopf.fr/telechargement/resource/ADMIN-EXPRESS` —
    and that URL is exactly what a metadata record publishes as its download link,
    so matching on it compares two values that are the same thing. The title is
    kept for display, and used as the key only when an entry carries no id.
    """
    resources: list[PublishedResource] = []
    for entry in root.findall("atom:entry", SERVICE_NAMESPACES):
        title = _text(entry, "atom:title")
        identifier = _text(entry, "atom:id")
        key = resource_key(identifier) if identifier else None
        if not key:
            key = title
        if not key:
            logger.warning("download feed entry with neither id nor title, skipped")
            continue
        resources.append(PublishedResource(key=key, title=title))
    return resources


def resource_key(url: str) -> str | None:
    """Return the download resource a URL names, or `None` when it names none.

    The download service publishes two kinds of URL and only one of them is a
    resource: `/telechargement/resource/{key}` is the resource, while
    `/telechargement/download/{…}.7z` is one file of one delivery of it. A record
    linking straight to a file says nothing about which resource it covers, so it
    is not turned into a claim — counting it as an unknown one would report a
    catalogue anomaly that is not there.

    Args:
        url: The URL published by the catalogue, or by the feed as an entry id.

    Returns:
        The resource key, or `None`.
    """
    path = urlsplit(url).path.rstrip("/")
    prefix = "/telechargement/resource/"
    if not path.startswith(prefix):
        return None
    key = path[len(prefix) :]
    # One segment only: anything deeper is a file inside a delivery, not a resource.
    if not key or "/" in key:
        return None
    return key


def _collect(
    elements: list[ET.Element], key_path: str, title_path: str
) -> list[PublishedResource]:
    """Turn a list of inventory elements into resources, dropping the unnamed ones."""
    resources: list[PublishedResource] = []
    for element in elements:
        key = _text(element, key_path)
        if not key:
            logger.warning("inventory entry without %s, skipped", key_path)
            continue
        resources.append(PublishedResource(key=key, title=_text(element, title_path)))
    return resources


def _text(element: ET.Element, path: str) -> str | None:
    """Return the stripped text at `path`, or `None` when it is absent or empty.

    Titles of the live services carry leading and trailing spaces — " OCSGE Gers
    2016 " — so stripping is not cosmetic: it is what makes two runs comparable.
    """
    value = element.findtext(path, namespaces=SERVICE_NAMESPACES)
    return value.strip() or None if value else None
