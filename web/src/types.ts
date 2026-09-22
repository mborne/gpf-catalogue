// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/* The shapes of the documents the site reads. They mirror
   `gpf_catalogue/model.py` and `gpf_catalogue/stats.py`, whose exported schema —
   `docs/pivot-schema.json` — is the contract; these declarations are the reader's
   side of it, and adding a field to the model means adding it here too.

   Everything optional is `| null` rather than `?`, because the pipeline writes
   `null` for what the catalogue does not carry: a missing value is a published
   fact, not an absent key. */

export type ResourceType = "dataset" | "series" | "service";

export type SpatialScope =
  | "global"
  | "european"
  | "national"
  | "regional"
  | "local";

export type LinkType =
  | "wfs"
  | "wms"
  | "wmts"
  | "tms"
  | "download"
  | "capabilities"
  | "documentation"
  | "other";

export interface Link {
  type: LinkType;
  url: string;
  /** The layer, machine readable: `BDTOPO_V3:batiment`. */
  name: string | null;
  /** The same entry, human readable: "BD TOPO® V3 batiment". */
  description: string | null;
}

/** One zone a record declares, with the name the catalogue gave it. A record
    covering several territories publishes one of these per territory; their
    union is `CatalogueRecord.bbox`, which is far coarser. */
export interface Extent {
  /** "Guadeloupe", or null on the 167 extents naming nothing. */
  name: string | null;
  /** "GLP". */
  code: string | null;
  /** "ISO 3166 alpha 3". */
  codeSpace: string | null;
  bbox: [number, number, number, number];
}

export interface CatalogueRecord {
  fileIdentifier: string;
  type: ResourceType;
  title: string | null;
  abstract: string | null;
  edition: string | null;
  producer: string | null;
  contactEmail: string | null;
  keywords: string[];
  inspireThemes: string[];
  topicCategories: string[];
  purpose: string | null;
  spatialScope: SpatialScope | null;
  /** The union of `extents`: a cheap first filter, but a coarse one. */
  bbox: [number, number, number, number] | null;
  extents: Extent[];
  temporalStart: string | null;
  temporalEnd: string | null;
  created: string | null;
  published: string | null;
  revised: string | null;
  /** The `MD_MaintenanceFrequencyCode` value as published, `quaterly` included. */
  updateFrequency: string | null;
  lineage: string | null;
  licence: string | null;
  accessConstraint: string | null;
  links: Link[];
  thumbnailUrl: string | null;
  suspectedTest: boolean;
}

export interface Catalogue {
  source: string;
  count: number;
  records: CatalogueRecord[];
}

export interface Count {
  value: string;
  count: number;
}

export interface FieldCoverage {
  field: string;
  count: number;
  share: number;
}

/** The publisher, licence family and year of one record, derived by `stats.py`. */
export interface RecordFacets {
  fileIdentifier: string;
  publisher: string | null;
  licenceFamily: string;
  year: string | null;
}

export interface QualityStats {
  records: number;
  missingTitle: number;
  missingAbstract: number;
  suspectedTests: string[];
  linksTotal: number;
  linksDistinctUrls: number;
  linksWithoutName: number;
  linksWithoutDescription: number;
  recordsWithoutLinks: number;
  distinctProducers: number;
  undeclaredLicence: number;
  undeclaredAccessConstraint: number;
  undeclaredSpatialScope: number;
}

export interface CatalogueStats {
  source: string;
  count: number;
  byType: Count[];
  byTopicCategory: Count[];
  byInspireTheme: Count[];
  bySpatialScope: Count[];
  byPublisher: Count[];
  byLicenceFamily: Count[];
  byYear: Count[];
  byLinkType: Count[];
  recordsByLinkType: Count[];
  topKeywords: Count[];
  recordFacets: RecordFacets[];
  coverage: FieldCoverage[];
  quality: QualityStats;
}

/* The coverage document, written by `gpf_catalogue/coverage.py`. It is the one the
   site may legitimately not carry: measuring it needs the inventories of three
   services other than the CSW, so `coverage` is `null` on a build that never
   fetched them — which the page says, rather than drawing zeroes. */

/** One resource a service says it serves, as `gpf_catalogue/inventory.py` read it. */
export interface PublishedResource {
  /** What a record has to cite: a `typeName`, a layer identifier, a resource name. */
  key: string;
  /** The label the service gives it, null when it publishes none. */
  title: string | null;
}

/** A key the catalogue cites and the service does not publish. */
export interface UnknownClaim {
  key: string;
  /** The records citing it, truncated; `citing` is how many there really are. */
  records: string[];
  citing: number;
}

export interface ServiceCoverage {
  service: string;
  /** What this service calls its resources: "feature types", "layers". */
  label: string;
  endpoint: string;
  published: number;
  covered: number;
  uncovered: PublishedResource[];
  claimed: number;
  unknown: UnknownClaim[];
  links: number;
  linksWithoutKey: number;
  records: number;
}

export interface CatalogueCoverage {
  records: number;
  services: ServiceCoverage[];
}
