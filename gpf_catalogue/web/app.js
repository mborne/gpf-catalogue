/* Author: Claude (Anthropic) — this file is AI generated, see docs/init.md. */

/* The page reads two documents written beside it and does everything else in the
   browser. At 326 records and 860 KB there is nothing to page, index or serve; when
   the catalogue outgrows that, it is a search index that is needed, not a bigger
   page (ROADMAP phase 4).

   Nothing here re-derives a value: the publisher, the licence family and the
   publication year of each record are read from `stats.json`, where
   `gpf_catalogue/stats.py` computed them. Two implementations of one rule would be
   two rules. */

"use strict";

const state = {
  stats: null,
  records: [],
  facets: new Map(),
  index: new Map(),
};

/** Values of a long tailed aggregate shown before the "show all" button. */
const TOP_N = 12;

// --- small helpers ---------------------------------------------------------

/** Create an element, with text and attributes, never with markup. */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

/** Format an integer the way the documentation writes it: 1 530, not 1,530. */
function fmt(value) {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/** Share of a total, as a percentage with one decimal. */
function share(count, total) {
  return total ? `${((100 * count) / total).toFixed(1)} %` : "—";
}

function fetchJSON(path) {
  return fetch(path).then((response) => {
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  });
}

// --- charts ----------------------------------------------------------------

/**
 * Render a ranked horizontal bar chart into a <figure>.
 *
 * One series, so one colour and no legend: the heading says what is plotted.
 * Every value is labelled at the bar end, which doubles as the table view, so no
 * number is reachable through the tooltip alone.
 */
function barChart(figure, counts, options) {
  const settings = Object.assign({ limit: 0, total: 0, unit: "records", scale: 0 }, options);
  const bars = el("div", "bars");
  // `scale` pins the axis to a known whole — the catalogue, for a coverage chart —
  // so a bar reads as a share. Without it the longest bar would be full width even
  // when no value comes close to the whole.
  const max =
    settings.scale || counts.reduce((best, item) => Math.max(best, item.count), 0) || 1;
  const limited = settings.limit > 0 && counts.length > settings.limit;
  let shown = limited ? settings.limit : counts.length;

  const draw = () => {
    bars.replaceChildren();
    for (const item of counts.slice(0, shown)) {
      const row = el("div", "bar-row");
      const label = el("span", "bar-label", item.value);
      label.title = item.value;
      const track = el("span", "bar-track");
      const fill = el("span", "bar-fill");
      fill.style.width = `${(100 * item.count) / max}%`;
      track.appendChild(fill);
      const value = el("span", "bar-value", item.label || fmt(item.count));
      row.title = settings.total
        ? `${item.value} — ${fmt(item.count)} ${settings.unit}, ${share(item.count, settings.total)} of the catalogue`
        : `${item.value} — ${fmt(item.count)} ${settings.unit}`;
      row.append(label, track, value);
      bars.appendChild(row);
    }
  };

  draw();
  figure.appendChild(bars);

  if (limited) {
    const button = el("button", "ghost chart-more", `Show all ${counts.length}`);
    button.type = "button";
    button.addEventListener("click", () => {
      const expanded = shown === counts.length;
      shown = expanded ? settings.limit : counts.length;
      button.textContent = expanded ? `Show all ${counts.length}` : "Show fewer";
      draw();
    });
    figure.appendChild(button);
  }
}

/** Render a chronological column chart. Time is the one axis that is not ranked. */
function columnChart(figure, counts) {
  const max = counts.reduce((best, item) => Math.max(best, item.count), 0) || 1;
  figure.appendChild(el("div", "axis-max", `${fmt(max)} records`));

  const plot = el("div", "columns");
  const axis = el("div", "column-axis");
  // One tick every few columns, so year labels never collide.
  const step = Math.ceil(counts.length / 12);

  counts.forEach((item, position) => {
    const column = el("div", "column");
    const fill = el("div", "column-fill");
    fill.style.height = `${(100 * item.count) / max}%`;
    // A year with no record draws nothing: the 2px minimum that keeps small bars
    // visible would otherwise make zero look like one.
    if (!item.count) fill.style.minHeight = "0";
    column.title = `${item.value} — ${fmt(item.count)} records`;
    column.appendChild(fill);
    plot.appendChild(column);
    axis.appendChild(
      el("div", "column-tick", position % step === 0 ? item.value : "")
    );
  });

  figure.append(plot, axis);
}

// --- overview --------------------------------------------------------------

function renderOverview(stats) {
  const quality = stats.quality;
  document.getElementById("hero-count").textContent = fmt(stats.count);
  document.getElementById("hero-note").textContent =
    `${fmt(quality.linksTotal)} access links, ` +
    `${fmt(quality.linksDistinctUrls)} distinct endpoints behind them.`;

  const tiles = [
    ["Access links", fmt(quality.linksTotal), `${fmt(quality.linksDistinctUrls)} distinct URLs`],
    ["Publishers", fmt(stats.byPublisher.length), "distinct contact email domains"],
    ["INSPIRE themes", fmt(stats.byInspireTheme.length), "declared across the catalogue"],
    ["Topic categories", fmt(stats.byTopicCategory.length), "values of the ISO code list in use"],
    ["Without a licence", fmt(quality.undeclaredLicence), share(quality.undeclaredLicence, stats.count) + " of records"],
    ["Suspected tests", fmt(quality.suspectedTests.length), "flagged, not dropped"],
  ];
  const container = document.getElementById("tiles");
  for (const [label, value, note] of tiles) {
    const tile = el("div", "tile");
    tile.append(el("div", "tile-label", label), el("div", "tile-value", value), el("div", "tile-note", note));
    container.appendChild(tile);
  }

  barChart(document.getElementById("chart-type"), stats.byType, { total: stats.count });
  barChart(document.getElementById("chart-link"), stats.recordsByLinkType, { total: stats.count });
  barChart(document.getElementById("chart-topic"), stats.byTopicCategory, { total: stats.count });
  barChart(document.getElementById("chart-theme"), stats.byInspireTheme, { total: stats.count, limit: TOP_N });
  barChart(document.getElementById("chart-scope"), stats.bySpatialScope, { total: stats.count });
  barChart(document.getElementById("chart-publisher"), stats.byPublisher, { total: stats.count, limit: TOP_N });
  barChart(document.getElementById("chart-licence"), stats.byLicenceFamily, { total: stats.count });
  columnChart(document.getElementById("chart-year"), stats.byYear);
  barChart(document.getElementById("chart-keywords"), stats.topKeywords, { total: stats.count, limit: TOP_N });
}

// --- records ---------------------------------------------------------------

const FILTERS = [
  ["f-type", "byType"],
  ["f-topic", "byTopicCategory"],
  ["f-theme", "byInspireTheme"],
  ["f-scope", "bySpatialScope"],
  ["f-link", "recordsByLinkType"],
  ["f-publisher", "byPublisher"],
  ["f-licence", "byLicenceFamily"],
  ["f-year", "byYear"],
];

function fillFilters(stats) {
  for (const [id, key] of FILTERS) {
    const select = document.getElementById(id);
    for (const item of stats[key]) {
      const option = el("option", null, `${item.value} (${fmt(item.count)})`);
      option.value = item.value;
      select.appendChild(option);
    }
  }
}

// --- markdown ---------------------------------------------------------------

/* Abstracts are written in Markdown — 94 of the 326 use `**bold**`, 36 carry a
   list, 16 a link — and showing the asterisks is showing the source's markup
   rather than its text. Only abstracts: link names and descriptions are left
   alone, because 155 of them contain `*` or `_` inside a layer name such as
   `trichls_s_d51_gpkg_07-10-2024_wfs`, which any renderer would mangle, and the
   links table is meant to show the data raw.

   The text comes from a third party service, so nothing here ever builds HTML
   from it: every branch produces DOM nodes, and anything unrecognised stays a
   text node. A `<` in an abstract is displayed, never parsed. */

/** The HTML escapes the catalogue leaves behind in its own text. */
const ENTITIES = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  "#39": "'",
  nbsp: "\u00a0",
};

/** Inline constructs, tried in this order: code wins over emphasis, bold over italic. */
const INLINE =
  /`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|\*([^*\n]+)\*|(https?:\/\/[^\s<>()]+)/g;

/** Undo what the source escaped twice, and turn its stray <br> into line breaks. */
function normalise(text) {
  return text
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/&(amp|lt|gt|quot|apos|#39|nbsp);/g, (whole, name) =>
      name in ENTITIES ? ENTITIES[name] : whole
    );
}

/** An external link, built rather than written: only http(s) URLs reach here. */
function externalLink(href, text) {
  const anchor = el("a", null, text);
  anchor.href = href;
  anchor.rel = "noopener noreferrer";
  anchor.target = "_blank";
  return anchor;
}

/** Turn one line of Markdown into text nodes and the few elements it allows. */
function inlineNodes(text) {
  const nodes = [];
  let last = 0;
  let match;
  INLINE.lastIndex = 0;
  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(document.createTextNode(text.slice(last, match.index)));
    }
    if (match[1] !== undefined) nodes.push(el("code", null, match[1]));
    else if (match[2] !== undefined) nodes.push(el("strong", null, match[2]));
    else if (match[3] !== undefined) nodes.push(externalLink(match[4], match[3]));
    else if (match[5] !== undefined) nodes.push(el("em", null, match[5]));
    else nodes.push(externalLink(match[6], match[6]));
    last = match.index + match[0].length;
  }
  if (last < text.length) nodes.push(document.createTextNode(text.slice(last)));
  return nodes;
}

/**
 * Render an abstract, as a fragment of paragraphs, lists and headings.
 *
 * Blank lines separate blocks, consecutive lines join into one paragraph, and
 * consecutive bullets into one list — which is what the catalogue writes: BD
 * TOPO lists its themes as seven ` - ` lines in a row.
 */
function renderMarkdown(text) {
  const fragment = document.createDocumentFragment();
  let paragraph = [];
  let list = null;
  let listTag = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const block = el("p");
    block.append(...inlineNodes(paragraph.join(" ")));
    fragment.appendChild(block);
    paragraph = [];
  };
  const flushList = () => {
    if (list) fragment.appendChild(list);
    list = null;
    listTag = null;
  };

  for (const raw of normalise(text).split("\n")) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    const bullet = line.match(/^[-*+]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);

    if (heading) {
      flushParagraph();
      flushList();
      const title = el("h4", "md-heading");
      title.append(...inlineNodes(heading[1]));
      fragment.appendChild(title);
    } else if (bullet || numbered) {
      flushParagraph();
      const tag = bullet ? "ul" : "ol";
      if (listTag !== tag) {
        flushList();
        list = el(tag, "md-list");
        listTag = tag;
      }
      const item = document.createElement("li");
      item.append(...inlineNodes((bullet || numbered)[1]));
      list.appendChild(item);
    } else {
      flushList();
      paragraph.push(line);
    }
  }
  flushParagraph();
  flushList();
  return fragment;
}

/** Order two possibly missing strings, empty last, for a stable table order. */
function cmp(a, b) {
  return String(a || "\uffff").localeCompare(String(b || "\uffff"));
}

/** Lowercased haystack of everything the search box searches. */
function haystackOf(record) {
  return [
    record.title,
    record.abstract,
    record.fileIdentifier,
    ...(record.keywords || []),
    // The layer names and their labels are where a theme is often actually
    // written: BD TOPO never says "batiment" in its abstract, only in its layers.
    ...(record.links || []).flatMap((link) => [link.name, link.description]),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function matches(record) {
  const facet = state.facets.get(record.fileIdentifier) || {};
  const text = document.getElementById("f-text").value.trim().toLowerCase();
  if (text && !state.index.get(record.fileIdentifier).includes(text)) return false;
  if (!document.getElementById("f-tests").checked && record.suspectedTest) return false;

  const type = document.getElementById("f-type").value;
  if (type && record.type !== type) return false;
  const topic = document.getElementById("f-topic").value;
  if (topic && !(record.topicCategories || []).includes(topic)) return false;
  const theme = document.getElementById("f-theme").value;
  if (theme && !(record.inspireThemes || []).includes(theme)) return false;
  const scope = document.getElementById("f-scope").value;
  if (scope && record.spatialScope !== scope) return false;
  const link = document.getElementById("f-link").value;
  if (link && !(record.links || []).some((item) => item.type === link)) return false;
  const publisher = document.getElementById("f-publisher").value;
  if (publisher && facet.publisher !== publisher) return false;
  const licence = document.getElementById("f-licence").value;
  if (licence && facet.licenceFamily !== licence) return false;
  const year = document.getElementById("f-year").value;
  if (year && facet.year !== year) return false;
  return true;
}

function pair(list, term, value) {
  if (!value) return;
  const block = el("div", "pair");
  const dt = el("dt", null, term);
  const dd = el("dd", null, value);
  block.append(dt, dd);
  list.appendChild(block);
}

function recordCard(record) {
  const facet = state.facets.get(record.fileIdentifier) || {};
  const card = el("details", "record");
  const summary = document.createElement("summary");

  const title = el("span", "record-title", record.title || "(no title published)");
  if (!record.title) title.classList.add("untitled");
  summary.append(title, el("span", "badge", record.type));
  if (record.suspectedTest) summary.appendChild(el("span", "badge warn", "suspected test"));
  summary.appendChild(el("span", "record-id", record.fileIdentifier));
  card.appendChild(summary);

  const body = el("div", "record-body");

  // Right under the title: the two places the record itself lives, so anything
  // below can be checked against the source without hunting for it.
  const sources = el("p", "sources");
  const page = el("a", null, "cartes.gouv.fr");
  const kind = record.type === "service" ? "service" : "dataset";
  page.href = `https://cartes.gouv.fr/rechercher-une-donnee/${kind}/${encodeURIComponent(record.fileIdentifier)}`;
  page.rel = "noopener noreferrer";
  page.target = "_blank";
  const xml = el("a", null, "metadata record (XML)");
  xml.href =
    "https://data.geopf.fr/csw?REQUEST=GetRecordById&SERVICE=CSW&VERSION=2.0.2" +
    "&OUTPUTSCHEMA=http://standards.iso.org/iso/19115/-3/mdb/2.0&elementSetName=full&ID=" +
    encodeURIComponent(record.fileIdentifier);
  xml.rel = "noopener noreferrer";
  xml.target = "_blank";
  sources.append(el("span", "badge", "source"), page, xml);
  body.appendChild(sources);

  if (record.abstract) {
    const abstract = el("div", "abstract");
    abstract.appendChild(renderMarkdown(record.abstract));
    body.appendChild(abstract);
  }

  const pairs = el("dl", "pairs");
  pair(pairs, "Producer, as published", record.producer);
  pair(pairs, "Contact", record.contactEmail);
  pair(pairs, "Publisher (email domain)", facet.publisher);
  pair(pairs, "Licence", record.licence);
  pair(pairs, "Licence family", facet.licenceFamily);
  pair(pairs, "Access constraint", record.accessConstraint);
  pair(pairs, "Created", record.created);
  pair(pairs, "Published", record.published);
  pair(pairs, "Revised", record.revised);
  if (record.temporalStart || record.temporalEnd) {
    pair(pairs, "Covers", `${record.temporalStart || "?"} → ${record.temporalEnd || "?"}`);
  }
  pair(pairs, "Spatial scope", record.spatialScope);
  if (record.bbox) pair(pairs, "Bounding box (W, S, E, N)", record.bbox.join(", "));
  if ((record.topicCategories || []).length) {
    pair(pairs, "Topic categories", record.topicCategories.join(", "));
  }
  if ((record.inspireThemes || []).length) {
    pair(pairs, "INSPIRE themes", record.inspireThemes.join(", "));
  }
  if ((record.keywords || []).length) pair(pairs, "Keywords", record.keywords.join(", "));
  body.appendChild(pairs);

  // The links are shown raw, one row per entry the catalogue published, sorted by
  // protocol then URL then name. Grouping or tidying them here would hide what the
  // source actually looks like — the repetition, the empty names, the same endpoint
  // under four spellings — and that mess is worth seeing.
  const entries = [...(record.links || [])].sort(
    (a, b) =>
      cmp(a.type, b.type) || cmp(a.url, b.url) || cmp(a.name, b.name) ||
      cmp(a.description, b.description)
  );

  if (entries.length) {
    const table = el("table", "table links-table");
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    for (const column of ["Protocol", "URL", "Name", "Description"]) {
      const cell = el("th", null, column);
      cell.scope = "col";
      headRow.appendChild(cell);
    }
    head.appendChild(headRow);
    table.appendChild(head);

    const rows = document.createElement("tbody");
    for (const link of entries) {
      const row = document.createElement("tr");
      const url = document.createElement("td");
      const anchor = el("a", null, link.url);
      anchor.href = link.url;
      anchor.rel = "noopener noreferrer";
      anchor.target = "_blank";
      url.className = "url";
      url.appendChild(anchor);
      row.append(
        el("td", "protocol", link.type),
        url,
        el("td", "name", link.name || "—"),
        el("td", null, link.description || "—")
      );
      rows.appendChild(row);
    }
    table.appendChild(rows);
    const heading = el("h3", "section-title", `Access links (${fmt(entries.length)})`);
    const wrap = el("div", "table-wrap");
    wrap.appendChild(table);
    body.append(heading, wrap);
  }

  card.appendChild(body);
  return card;
}

function renderRecords() {
  const visible = state.records.filter(matches);
  const container = document.getElementById("records");
  const fragment = document.createDocumentFragment();
  for (const record of visible) fragment.appendChild(recordCard(record));
  container.replaceChildren(fragment);

  const hidden = state.records.length - visible.length;
  document.getElementById("result-count").textContent =
    `${fmt(visible.length)} of ${fmt(state.records.length)} records` +
    (hidden ? ` — ${fmt(hidden)} filtered out` : "");
}

// --- quality ---------------------------------------------------------------

function renderQuality(stats) {
  const quality = stats.quality;
  barChart(
    document.getElementById("chart-coverage"),
    stats.coverage.map((item) => ({
      value: item.field,
      count: item.count,
      label: `${item.share.toFixed(1)} %`,
    })),
    { total: stats.count, scale: stats.count }
  );

  const rows = [
    ["Records declaring no licence", quality.undeclaredLicence],
    ["Records declaring no limitation on public access", quality.undeclaredAccessConstraint],
    ["Links carrying neither a name nor a description", `${fmt(quality.linksWithoutName)} of ${fmt(quality.linksTotal)}`],
    ["Links carrying no description", `${fmt(quality.linksWithoutDescription)} of ${fmt(quality.linksTotal)}`],
    ["Distinct spellings of producer, for far fewer organisations", quality.distinctProducers],
    ["Records offering no access link at all", quality.recordsWithoutLinks],
    ["Records flagged as test publications", quality.suspectedTests.length],
    ["Records published with no title", quality.missingTitle],
    ["Records published with no abstract", quality.missingAbstract],
  ];
  const body = document.querySelector("#anomalies tbody");
  for (const [label, value] of rows) {
    const row = document.createElement("tr");
    const cell = el("td", null, typeof value === "number" ? fmt(value) : value);
    cell.className = "num";
    row.append(el("td", null, label), cell);
    body.appendChild(row);
  }

  const tests = document.getElementById("tests");
  for (const identifier of quality.suspectedTests) {
    tests.appendChild(el("li", null, identifier));
  }
}

// --- chrome ----------------------------------------------------------------

function setUpTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      for (const other of tabs) {
        const selected = other === tab;
        other.setAttribute("aria-selected", String(selected));
        document.getElementById(`panel-${other.dataset.tab}`).hidden = !selected;
      }
    });
  }
}

function setUpTheme() {
  const button = document.getElementById("theme-toggle");
  // Browser storage can throw or come back empty (private window, blocked site
  // data), and the page must render either way.
  let stored = null;
  try {
    stored = localStorage.getItem("gpf-theme");
  } catch (error) {
    stored = null;
  }
  if (stored) document.documentElement.dataset.theme = stored;

  button.addEventListener("click", () => {
    const dark =
      document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("gpf-theme", next);
    } catch (error) {
      /* A remembered theme is a convenience, never a requirement. */
    }
  });
}

function setUpFilters() {
  const form = document.getElementById("filters");
  form.addEventListener("input", renderRecords);
  form.addEventListener("change", renderRecords);
  form.addEventListener("submit", (event) => event.preventDefault());
  form.addEventListener("reset", () => window.setTimeout(renderRecords, 0));
}

function fail(message) {
  const notice = document.getElementById("error");
  notice.textContent = `${message} — the page reads catalogue.json and stats.json next to it, over HTTP. Try: uv run python -m http.server -d site 8000`;
  notice.hidden = false;
}

async function main() {
  setUpTabs();
  setUpTheme();
  setUpFilters();

  let stats;
  let catalogue;
  try {
    [stats, catalogue] = await Promise.all([fetchJSON("stats.json"), fetchJSON("catalogue.json")]);
  } catch (error) {
    fail(String(error.message || error));
    return;
  }

  state.stats = stats;
  state.records = catalogue.records || [];
  for (const facet of stats.recordFacets || []) {
    state.facets.set(facet.fileIdentifier, facet);
  }
  for (const record of state.records) {
    state.index.set(record.fileIdentifier, haystackOf(record));
  }

  document.getElementById("subtitle").textContent =
    `${fmt(stats.count)} resources harvested from ${stats.source}`;
  document.getElementById("source-url").textContent = stats.source;

  renderOverview(stats);
  fillFilters(stats);
  renderRecords();
  renderQuality(stats);
}

main();
