// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/* The filters live in the query string, so a search is a URL: `/records?theme=
   Altitude&link=wfs` is something to paste into an issue. That is the same reason
   a record has a route — the previous site kept all of this in the DOM, where
   nothing could be referred to.

   Which facets exist was measured, not assumed (ROADMAP phase 3): `type` has 3
   values, `topicCategories` 19, link types 8, and `keywords` — 638 distinct
   values, 432 of them used once — is searched rather than faceted. */

import type { CatalogueRecord, CatalogueStats, RecordFacets } from "./types";

/** Query parameter of the free text search. */
export const TEXT_PARAM = "q";

/** Query parameter of the "include suspected test records" toggle. */
export const TESTS_PARAM = "tests";

/* Value of the "not stated" option of the spatial scope filter. The parentheses
   cannot collide with a code list value, which is a bare lowercase word, and an
   absent parameter already means "any". */
export const UNSTATED = "(not stated)";

export interface FacetFilter {
  /** Query parameter carrying it. */
  param: string;
  label: string;
  /** Aggregate of `stats.json` the options are read from. */
  options: keyof CatalogueStats & string;
  /** Label of the empty option. */
  any: string;
  /** Whether a record passes the filter, for a non-empty value. */
  matches: (
    record: CatalogueRecord,
    value: string,
    facets: RecordFacets | undefined,
  ) => boolean;
}

export const FACETS: FacetFilter[] = [
  {
    param: "type",
    label: "Type",
    options: "byType",
    any: "Any",
    matches: (record, value) => record.type === value,
  },
  {
    param: "topic",
    label: "Topic category",
    options: "byTopicCategory",
    any: "Any",
    matches: (record, value) => record.topicCategories.includes(value),
  },
  {
    param: "theme",
    label: "INSPIRE theme",
    options: "byInspireTheme",
    any: "Any",
    matches: (record, value) => record.inspireThemes.includes(value),
  },
  {
    param: "scope",
    label: "Spatial scope",
    options: "bySpatialScope",
    any: "Any",
    matches: (record, value) =>
      value === UNSTATED ? !record.spatialScope : record.spatialScope === value,
  },
  {
    param: "link",
    label: "Offers",
    options: "recordsByLinkType",
    any: "Any link",
    matches: (record, value) => record.links.some((link) => link.type === value),
  },
  {
    param: "publisher",
    label: "Publisher",
    options: "byPublisher",
    any: "Any",
    matches: (_record, value, facets) => facets?.publisher === value,
  },
  {
    param: "licence",
    label: "Licence",
    options: "byLicenceFamily",
    any: "Any",
    matches: (_record, value, facets) => facets?.licenceFamily === value,
  },
  {
    param: "year",
    label: "Published",
    options: "byYear",
    any: "Any year",
    matches: (_record, value, facets) => facets?.year === value,
  },
];

/** Whether a record passes every filter carried by the URL. */
export function matches(
  record: CatalogueRecord,
  params: URLSearchParams,
  haystack: string,
  facets: RecordFacets | undefined,
): boolean {
  const text = (params.get(TEXT_PARAM) ?? "").trim().toLowerCase();
  if (text && !haystack.includes(text)) return false;
  if (params.get(TESTS_PARAM) !== "1" && record.suspectedTest) return false;

  for (const facet of FACETS) {
    const value = params.get(facet.param);
    if (value && !facet.matches(record, value, facets)) return false;
  }
  return true;
}

/** The `/records` URL filtered on one facet value, for a bar of the overview. */
export function recordsPath(param: string, value: string): string {
  return `/records?${new URLSearchParams({ [param]: value }).toString()}`;
}
