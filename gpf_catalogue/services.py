"""Clients for the three Géoplateforme services that publish their own inventory.

The catalogue says what is described; these services say what is *served*. Putting
the two side by side is what answers "how many published layers does a metadata
record cover?" — see `gpf_catalogue.coverage`.

Like `csw.py`, this module only touches the network and returns **raw bytes**:
what lands in `data/services/` stays byte identical to what the service sent, and
every interpretation happens in `gpf_catalogue.inventory`, which is pure.

The three inventories are not the same document, and only one of them is an OGC
capabilities:

- the WFS and the WMTS answer a `GetCapabilities` in a single response, 5.2 MB and
  2.9 MB respectively,
- the download service answers an INSPIRE Atom feed, paginated ten entries at a
  time — `pagesize` is fixed server side, so the pages have to be walked.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from gpf_catalogue.csw import USER_AGENT

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when a service answers something that is not its inventory.

    OWS services report errors as an `ows:ExceptionReport` body with a HTTP 200
    status, exactly like the CSW does, so the status alone is not enough.
    """


@dataclass(frozen=True)
class ServiceSource:
    """Where one inventory is fetched from, and how it is paged.

    Attributes:
        name: Short name of the service, used as a file name and as a link type.
        url: Endpoint answering the inventory.
        params: Query parameters of the first request.
        page_param: Query parameter carrying the page number, for a paginated
            inventory. `None` when the service answers in one response.
        label: How the service is named in a report.
    """

    name: str
    url: str
    params: dict[str, str] = field(default_factory=dict)
    page_param: str | None = None
    label: str = ""


#: The three inventories, keyed by the link type of the pivot model they are
#: compared against. `download` is the odd one: an Atom feed, not a capabilities.
SERVICES: dict[str, ServiceSource] = {
    "wfs": ServiceSource(
        name="wfs",
        url="https://data.geopf.fr/wfs",
        params={"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetCapabilities"},
        label="WFS feature types",
    ),
    "wmts": ServiceSource(
        name="wmts",
        url="https://data.geopf.fr/wmts",
        params={"SERVICE": "WMTS", "VERSION": "1.0.0", "REQUEST": "GetCapabilities"},
        label="WMTS layers",
    ),
    "download": ServiceSource(
        name="download",
        url="https://data.geopf.fr/telechargement/capabilities",
        page_param="page",
        label="download resources",
    ),
}

#: Refuses to walk a feed forever, whatever the page count it declares.
MAX_PAGES = 200


class ServiceClient:
    """Read-only client for the inventory of one Géoplateforme service.

    Attributes:
        timeout: Per request timeout in seconds. The WFS capabilities is 5.2 MB,
            so the default is generous.
    """

    def __init__(self, timeout: float = 180.0, max_retries: int = 3) -> None:
        """Build a client with a session retrying on transient server errors.

        Args:
            timeout: Per request timeout in seconds.
            max_retries: Number of retries on connection errors and 5xx responses.
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        retry = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def fetch(self, source: ServiceSource) -> list[bytes]:
        """Fetch the whole inventory of one service.

        Args:
            source: The service to read.

        Returns:
            One body per page, in order. A single element for the two
            capabilities documents.

        Raises:
            ServiceError: If the service reports an error or declares a page count
                that cannot be walked.
            requests.RequestException: On network or HTTP level failures.
        """
        if source.page_param is None:
            return [self.get(source)]

        bodies: list[bytes] = []
        page = 1
        while True:
            body = self.get(source, page=page)
            bodies.append(body)
            total = page_count(body)
            logger.info("%s: page %d/%s", source.name, page, total or "?")
            # A feed that stops declaring its page count is the end of the walk,
            # rather than a reason to keep asking for pages that do not exist.
            if not total or page >= total:
                return bodies
            if page >= MAX_PAGES:
                raise ServiceError(
                    f"{source.name}: more than {MAX_PAGES} pages, refusing to walk on"
                )
            page += 1

    def get(self, source: ServiceSource, page: int | None = None) -> bytes:
        """Fetch one page of an inventory, failing on service level errors.

        Args:
            source: The service to read.
            page: Page number, for a paginated inventory.

        Returns:
            The raw response body.

        Raises:
            ServiceError: If the service answers with an `ows:ExceptionReport`.
        """
        params = dict(source.params)
        if page is not None and source.page_param:
            params[source.page_param] = str(page)
        logger.debug("GET %s %s", source.url, params)
        response = self.session.get(source.url, params=params, timeout=self.timeout)
        response.raise_for_status()
        _raise_on_exception_report(response.content)
        return response.content


def page_count(body: bytes) -> int:
    """Return the number of pages an Atom download feed declares.

    The count is carried as a `gpf_dl:pagecount` attribute on the feed element —
    the service also declares `gpf_dl:pagesize`, but it ignores the parameter, so
    the page count is the only thing that says how long the walk is.

    Args:
        body: One page of the feed.

    Returns:
        The declared page count, or 0 when the document declares none.
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError as cause:
        raise ServiceError(f"invalid XML returned by the service: {cause}") from cause
    for name, value in root.attrib.items():
        if name.endswith("pagecount") and value.isdigit():
            return int(value)
    return 0


def _raise_on_exception_report(body: bytes) -> None:
    """Raise a `ServiceError` if the body is an OWS exception report.

    The pre-check on the first bytes keeps this cheap: the WFS capabilities is
    5.2 MB and parsing it twice on every request would be wasteful.
    """
    if b"ExceptionReport" not in body[:2048]:
        return
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return
    if not root.tag.endswith("ExceptionReport"):
        return
    texts = [(element.text or "").strip() for element in root.iter() if element.text]
    raise ServiceError("; ".join(text for text in texts if text) or "unknown exception")
