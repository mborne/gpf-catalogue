"""XML namespaces used by the Géoplateforme CSW service.

The catalogue answers with CSW 2.0.2 envelopes containing ISO 19115-3 (`mdb` 2.0)
records. ISO 19115-3 splits what ISO 19139 kept in a single `gmd` namespace into a
dozen of them, hence this map.
"""
# Author: Claude (Anthropic) — this file is AI generated, see docs/init.md.

# CSW 2.0.2 envelope and the Dublin Core records it embeds.
CSW = "http://www.opengis.net/cat/csw/2.0.2"
DC = "http://purl.org/dc/elements/1.1/"
OWS = "http://www.opengis.net/ows"

# ISO 19115-3 (the `mdb` 2.0 output schema).
MDB = "http://standards.iso.org/iso/19115/-3/mdb/2.0"
MCC = "http://standards.iso.org/iso/19115/-3/mcc/1.0"
MRI = "http://standards.iso.org/iso/19115/-3/mri/1.0"
SRV = "http://standards.iso.org/iso/19115/-3/srv/2.0"
CIT = "http://standards.iso.org/iso/19115/-3/cit/2.0"
LAN = "http://standards.iso.org/iso/19115/-3/lan/1.0"
GCO = "http://standards.iso.org/iso/19115/-3/gco/1.0"
GCX = "http://standards.iso.org/iso/19115/-3/gcx/1.0"
MRD = "http://standards.iso.org/iso/19115/-3/mrd/1.0"
MRL = "http://standards.iso.org/iso/19115/-3/mrl/2.0"
MMI = "http://standards.iso.org/iso/19115/-3/mmi/1.0"
MCO = "http://standards.iso.org/iso/19115/-3/mco/1.0"
GEX = "http://standards.iso.org/iso/19115/-3/gex/1.0"

# Not ISO 19115-3: the extent uses GML for time, and links may be xlink references.
GML = "http://www.opengis.net/gml/3.2"
XLINK = "http://www.w3.org/1999/xlink"

#: Prefix to namespace map, to be passed to `ElementTree.find()` and friends.
NAMESPACES = {
    "csw": CSW,
    "dc": DC,
    "ows": OWS,
    "mdb": MDB,
    "mcc": MCC,
    "mri": MRI,
    "srv": SRV,
    "cit": CIT,
    "lan": LAN,
    "gco": GCO,
    "gcx": GCX,
    "mrd": MRD,
    "mrl": MRL,
    "mmi": MMI,
    "mco": MCO,
    "gex": GEX,
    "gml": GML,
    "xlink": XLINK,
}

#: Output schema requested to the CSW service.
OUTPUT_SCHEMA = MDB
