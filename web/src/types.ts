// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/* The shapes of the two documents the site reads. They mirror
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

export interface CatalogueRecord {
  fileIdentifier: string;
  type: ResourceType;
  title: string | null;
  abstract: string | null;
  producer: string | null;
  contactEmail: string | null;
  keywords: string[];
  inspireThemes: string[];
  topicCategories: string[];
  spatialScope: SpatialScope | null;
  bbox: [number, number, number, number] | null;
  temporalStart: string | null;
  temporalEnd: string | null;
  created: string | null;
  published: string | null;
  revised: string | null;
  licence: string | null;
  accessConstraint: string | null;
  links: Link[];
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
