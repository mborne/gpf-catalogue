// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/* The site reads the documents published beside it and does everything else in
   the browser. At 326 records and 1.2 MB there is nothing to page, index or
   serve; when the catalogue outgrows that, it is a search index that is needed,
   not a bigger page (ROADMAP phase 4).

   Nothing here re-derives a value: the publisher, the licence family and the
   publication year of each record are read from `stats.json`, where
   `gpf_catalogue/stats.py` computed them. Two implementations of one rule would
   be two rules.

   They are loaded once, at the root, rather than per route: moving from the
   search to a record must not refetch 1.2 MB, and the record page needs the same
   catalogue the search page filtered.

   `coverage.json` is the one that may be absent. It is measured against three
   services other than the CSW, so a build that never mirrored their inventories
   publishes a correct site without it — and a 404 on it is that build, not a
   broken one. It is the only document whose absence is not an error. */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { haystackOf } from "./format";
import type {
  Catalogue,
  CatalogueCoverage,
  CatalogueRecord,
  CatalogueStats,
  RecordFacets,
} from "./types";

export interface CatalogueData {
  stats: CatalogueStats;
  /** Null when the build measured no coverage; see the module comment. */
  coverage: CatalogueCoverage | null;
  records: CatalogueRecord[];
  /** Records by identifier, for `/records/{fileIdentifier}`. */
  byId: Map<string, CatalogueRecord>;
  /** Derived facets by identifier, as computed by `stats.py`. */
  facetsById: Map<string, RecordFacets>;
  /** Lowercased searchable text by identifier, built once. */
  haystack: Map<string, string>;
}

export interface CatalogueState {
  data: CatalogueData | null;
  error: string | null;
}

const CatalogueContext = createContext<CatalogueState>({ data: null, error: null });

/** The documents live next to the entry page, under the deployment prefix. */
const base = import.meta.env.BASE_URL;

async function fetchJSON<T>(name: string): Promise<T> {
  const response = await fetch(`${base}${name}`);
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  return (await response.json()) as T;
}

/** Like `fetchJSON`, but a document the build may not have written is not an error. */
async function fetchOptionalJSON<T>(name: string): Promise<T | null> {
  const response = await fetch(`${base}${name}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
  return (await response.json()) as T;
}

function index(
  stats: CatalogueStats,
  catalogue: Catalogue,
  coverage: CatalogueCoverage | null,
): CatalogueData {
  const records = catalogue.records || [];
  return {
    stats,
    coverage,
    records,
    byId: new Map(records.map((record) => [record.fileIdentifier, record])),
    facetsById: new Map(
      (stats.recordFacets || []).map((facet) => [facet.fileIdentifier, facet]),
    ),
    haystack: new Map(
      records.map((record) => [record.fileIdentifier, haystackOf(record)]),
    ),
  };
}

export function CatalogueProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CatalogueState>({ data: null, error: null });

  useEffect(() => {
    let live = true;
    Promise.all([
      fetchJSON<CatalogueStats>("stats.json"),
      fetchJSON<Catalogue>("catalogue.json"),
      fetchOptionalJSON<CatalogueCoverage>("coverage.json"),
    ])
      .then(([stats, catalogue, coverage]) => {
        if (live) setState({ data: index(stats, catalogue, coverage), error: null });
      })
      .catch((reason: unknown) => {
        if (live) {
          setState({ data: null, error: String((reason as Error)?.message ?? reason) });
        }
      });
    return () => {
      live = false;
    };
  }, []);

  return (
    <CatalogueContext.Provider value={state}>{children}</CatalogueContext.Provider>
  );
}

/** What the chrome needs: it renders before the catalogue has arrived. */
export function useCatalogueState(): CatalogueState {
  return useContext(CatalogueContext);
}

/** The catalogue, guaranteed loaded: pages render only once it is. */
export function useCatalogue(): CatalogueData {
  const { data } = useContext(CatalogueContext);
  if (!data) throw new Error("useCatalogue() used before the catalogue was loaded");
  return data;
}

/** One record, or null when the identifier in the URL matches none. */
export function useRecord(fileIdentifier: string | undefined) {
  const { byId, facetsById } = useCatalogue();
  return useMemo(() => {
    if (!fileIdentifier) return null;
    const record = byId.get(fileIdentifier);
    if (!record) return null;
    return { record, facets: facetsById.get(fileIdentifier) ?? null };
  }, [byId, facetsById, fileIdentifier]);
}
