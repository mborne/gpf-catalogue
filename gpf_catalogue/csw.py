"""Client for the Géoplateforme CSW service (https://data.geopf.fr/csw).

Only the two operations needed to mirror the catalogue are implemented:

- `list_identifiers()` to enumerate the records,
- `get_record()` to fetch one full ISO 19115-3 record.

Responses are returned as raw bytes so that what we store on disk stays byte
identical to what the service sent.
"""

import logging
import xml.etree.ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from gpf_catalogue.namespaces import CSW, NAMESPACES, OUTPUT_SCHEMA

logger = logging.getLogger(__name__)

#: Public endpoint of the Géoplateforme metadata discovery service.
DEFAULT_CSW_URL = "https://data.geopf.fr/csw"

#: Records requested per `GetRecords` call. The service honours at least 336.
DEFAULT_PAGE_SIZE = 100

#: Sent so that the Géoplateforme can identify (and contact us about) this client.
USER_AGENT = "gpf-catalogue (+https://github.com/ignfab/gpf-catalogue)"


class CswError(Exception):
    """Raised when the CSW service reports an error or answers something unexpected.

    Note that CSW reports errors as an `ows:ExceptionReport` body with a HTTP 200
    status, so the HTTP status alone is not enough to detect a failure.
    """


class CswClient:
    """Minimal read-only client for a CSW 2.0.2 service.

    Attributes:
        url: Base URL of the CSW endpoint.
        timeout: Per request timeout in seconds.
    """

    def __init__(
        self,
        url: str = DEFAULT_CSW_URL,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        """Build a client with a session retrying on transient server errors.

        Args:
            url: Base URL of the CSW endpoint.
            timeout: Per request timeout in seconds.
            max_retries: Number of retries on connection errors and 5xx responses.
        """
        self.url = url
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

    def list_identifiers(self, page_size: int = DEFAULT_PAGE_SIZE) -> list[str]:
        """List the identifiers of every record published by the service.

        Uses `elementSetName=brief` on `csw:Record`: the full ISO records are not
        needed here, only their identifiers.

        Returns:
            The record identifiers, in the order returned by the service.

        Raises:
            CswError: If the service reports an error or returns an unexpected body.
        """
        identifiers: list[str] = []
        start_position = 1
        while True:
            body = self._get(
                {
                    "SERVICE": "CSW",
                    "VERSION": "2.0.2",
                    "REQUEST": "GetRecords",
                    "resultType": "results",
                    "typeNames": "csw:Record",
                    "outputSchema": CSW,
                    "elementSetName": "brief",
                    "startPosition": str(start_position),
                    "maxRecords": str(page_size),
                }
            )
            root = _parse(body)
            results = root.find("csw:SearchResults", NAMESPACES)
            if results is None:
                raise CswError("GetRecords response without csw:SearchResults")

            page = [
                element.text.strip()
                for element in results.iterfind(".//dc:identifier", NAMESPACES)
                if element.text and element.text.strip()
            ]
            identifiers.extend(page)
            logger.info(
                "listed %d identifiers (%d/%s)",
                len(page),
                len(identifiers),
                results.get("numberOfRecordsMatched", "?"),
            )

            next_record = int(results.get("nextRecord", "0"))
            # The service returns nextRecord="0" on the last page. An empty page is
            # also treated as the end, to never loop forever on a misbehaving server.
            if next_record <= 0 or not page:
                return identifiers
            start_position = next_record

    def get_record(self, identifier: str) -> bytes:
        """Fetch one full ISO 19115-3 record.

        Args:
            identifier: The record identifier, as returned by `list_identifiers()`.

        Returns:
            The raw `csw:GetRecordByIdResponse` body.

        Raises:
            CswError: If the service reports an error or returns no record.
        """
        body = self._get(
            {
                "SERVICE": "CSW",
                "VERSION": "2.0.2",
                "REQUEST": "GetRecordById",
                "outputSchema": OUTPUT_SCHEMA,
                "elementSetName": "full",
                "ID": identifier,
            }
        )
        root = _parse(body)
        metadata = root.find(".//mdb:MD_Metadata", NAMESPACES)
        if metadata is None:
            raise CswError(f"no mdb:MD_Metadata returned for {identifier}")

        returned = metadata.findtext(
            "mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code/gco:CharacterString",
            default="",
            namespaces=NAMESPACES,
        ).strip()
        if returned and returned != identifier:
            # Not fatal: the record is stored under the identifier we asked for,
            # but a mismatch means the catalogue is not self consistent.
            logger.warning(
                "requested record %s, service returned %s", identifier, returned
            )
        return body

    def _get(self, params: dict[str, str]) -> bytes:
        """Perform a GET request and fail on CSW level errors.

        Raises:
            CswError: If the service answers with an `ows:ExceptionReport`.
            requests.RequestException: On network or HTTP level failures.
        """
        logger.debug("GET %s %s", self.url, params)
        response = self.session.get(self.url, params=params, timeout=self.timeout)
        response.raise_for_status()
        _raise_on_exception_report(response.content)
        return response.content


def _parse(body: bytes) -> ET.Element:
    """Parse a response body, turning malformed XML into a `CswError`."""
    try:
        return ET.fromstring(body)
    except ET.ParseError as cause:
        raise CswError(f"invalid XML returned by the service: {cause}") from cause


def _raise_on_exception_report(body: bytes) -> None:
    """Raise a `CswError` if the body is an OWS exception report.

    CSW returns those with a HTTP 200 status, so they have to be detected here.
    """
    # Cheap pre-check: parsing every multi-hundred kilobyte record twice is wasteful.
    if b"ExceptionReport" not in body[:2048]:
        return
    root = _parse(body)
    if not root.tag.endswith("ExceptionReport"):
        return
    texts = [
        (element.text or "").strip() for element in root.iter() if element.text
    ]
    raise CswError("; ".join(text for text in texts if text) or "unknown CSW exception")
