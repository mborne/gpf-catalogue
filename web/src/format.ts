// Author: Claude (Anthropic) — this file is AI generated, see ../../docs/init.md.

/** Format an integer the way the documentation writes it: 1 530, not 1,530. */
export function fmt(value: number): string {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/** Share of a total, as a percentage with one decimal. */
export function share(count: number, total: number): string {
  return total ? `${((100 * count) / total).toFixed(1)} %` : "—";
}

/** Order two possibly missing strings, empty last, for a stable table order. */
export function cmp(a: string | null, b: string | null): number {
  return String(a || "￿").localeCompare(String(b || "￿"));
}

/** Lowercased haystack of everything the search box searches. */
export function haystackOf(record: {
  title: string | null;
  abstract: string | null;
  fileIdentifier: string;
  keywords: string[];
  extents: { name: string | null }[];
  links: { name: string | null; description: string | null }[];
}): string {
  return [
    record.title,
    record.abstract,
    record.fileIdentifier,
    ...record.keywords,
    // The only place a territory is named: "Guadeloupe" appears in an extent, not
    // in the abstract. `lineage` and `purpose` are deliberately left out — they are
    // long prose, and a substring match over them answers far more than it should.
    ...record.extents.map((extent) => extent.name),
    // The layer names and their labels are where a theme is often actually
    // written: BD TOPO never says "batiment" in its abstract, only in its layers.
    ...record.links.flatMap((link) => [link.name, link.description]),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

/** The record's page on the official catalogue, which is the authoritative one. */
export function cartesGouvUrl(fileIdentifier: string, type: string): string {
  const kind = type === "service" ? "service" : "dataset";
  return `https://cartes.gouv.fr/rechercher-une-donnee/${kind}/${encodeURIComponent(fileIdentifier)}`;
}

/** The ISO 19115-3 record itself, as the CSW service serves it. */
export function cswUrl(fileIdentifier: string): string {
  return (
    "https://data.geopf.fr/csw?REQUEST=GetRecordById&SERVICE=CSW&VERSION=2.0.2" +
    "&OUTPUTSCHEMA=http://standards.iso.org/iso/19115/-3/mdb/2.0&elementSetName=full&ID=" +
    encodeURIComponent(fileIdentifier)
  );
}

/** The route of one service's coverage. Service names are `wfs`, `wmts`, `download`. */
export function coveragePath(service: string): string {
  return `/coverage/${encodeURIComponent(service)}`;
}

/** The route of one record. Identifiers carry spaces and accents; none carries a `/`. */
export function recordPath(fileIdentifier: string): string {
  return `/records/${encodeURIComponent(fileIdentifier)}`;
}
