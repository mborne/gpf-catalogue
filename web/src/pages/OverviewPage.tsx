// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import type { JSX } from "react";

import { useCatalogue } from "../catalogue";
import { BarChart, ChartCard, ColumnChart, TOP_N } from "../components/Chart";
import { fmt, share } from "../format";
import { UNSTATED, recordsPath } from "../filters";
import { usePageTitle } from "../title";

export function OverviewPage(): JSX.Element {
  const { stats } = useCatalogue();
  const quality = stats.quality;
  usePageTitle("Overview");

  const tiles: [string, string, string][] = [
    [
      "Access links",
      fmt(quality.linksTotal),
      `${fmt(quality.linksDistinctUrls)} distinct URLs`,
    ],
    ["Publishers", fmt(stats.byPublisher.length), "distinct contact email domains"],
    [
      "INSPIRE themes",
      fmt(stats.byInspireTheme.length),
      "declared across the catalogue",
    ],
    [
      "Topic categories",
      fmt(stats.byTopicCategory.length),
      "values of the ISO code list in use",
    ],
    [
      "Without a licence",
      fmt(quality.undeclaredLicence),
      `${share(quality.undeclaredLicence, stats.count)} of records`,
    ],
    ["Suspected tests", fmt(quality.suspectedTests.length), "flagged, not dropped"],
  ];

  return (
    <>
      <section className="hero card">
        <p className="hero-label">Resources in the pivot catalogue</p>
        <p className="hero-value">{fmt(stats.count)}</p>
        <p className="hero-note">
          {`${fmt(quality.linksTotal)} access links, ${fmt(quality.linksDistinctUrls)} distinct endpoints behind them.`}
        </p>
      </section>

      <div className="tiles">
        {tiles.map(([label, value, note]) => (
          <div className="tile" key={label}>
            <div className="tile-label">{label}</div>
            <div className="tile-value">{value}</div>
            <div className="tile-note">{note}</div>
          </div>
        ))}
      </div>

      {/* Every bar whose value is a facet leads to the records it counts. That is
          what routing bought: a number on a chart is now a question the search
          answers, rather than something to reproduce by hand in the filters. */}
      <div className="grid">
        <ChartCard title="By resource type">
          <BarChart
            counts={stats.byType}
            total={stats.count}
            linkTo={(value) => recordsPath("type", value)}
          />
        </ChartCard>

        <ChartCard
          title="Access protocols offered"
          caption="Records offering at least one link of each type. A record usually offers several."
        >
          <BarChart
            counts={stats.recordsByLinkType}
            total={stats.count}
            linkTo={(value) => recordsPath("link", value)}
          />
        </ChartCard>

        <ChartCard
          title="By ISO topic category"
          wide
          caption="A closed code list of 19 values. A record may declare several, so the bars sum to more than the catalogue."
        >
          <BarChart
            counts={stats.byTopicCategory}
            total={stats.count}
            linkTo={(value) => recordsPath("topic", value)}
          />
        </ChartCard>

        <ChartCard
          title="By INSPIRE theme"
          caption="From the GEMET thesaurus, declared by 56.4 % of the records."
        >
          <BarChart
            counts={stats.byInspireTheme}
            total={stats.count}
            limit={TOP_N}
            linkTo={(value) => recordsPath("theme", value)}
          />
        </ChartCard>

        <ChartCard
          title="By INSPIRE spatial scope"
          caption="Read from the code each record cites rather than from its label — the two disagree on 6 records. Not stated closes the chart: it is the complement of the five codes, not one of them, and it is the largest group."
        >
          {/* The five codes stay ranked among themselves, and the records citing
              none close the chart rather than topping it. The count is
              `quality.undeclaredSpatialScope`, measured by `stats.py` like every
              other number here — the page does not subtract it from the bars. */}
          <BarChart
            counts={[
              ...stats.bySpatialScope,
              {
                value: "Not stated",
                count: stats.quality.undeclaredSpatialScope,
                aside: true,
              },
            ]}
            total={stats.count}
            linkTo={(value) =>
              recordsPath("scope", value === "Not stated" ? UNSTATED : value)
            }
          />
        </ChartCard>

        <ChartCard
          title="By publisher"
          caption={
            <>
              The domain of the contact email, not <code>producer</code>, which is
              spelled 134 different ways. See <code>docs/overview.md</code>.
            </>
          }
        >
          <BarChart
            counts={stats.byPublisher}
            total={stats.count}
            limit={TOP_N}
            linkTo={(value) => recordsPath("publisher", value)}
          />
        </ChartCard>

        <ChartCard
          title="By licence family"
          caption="Grouped by a published mapping. Undeclared means the record states no licence — never that the data is open."
        >
          <BarChart
            counts={stats.byLicenceFamily}
            total={stats.count}
            linkTo={(value) => recordsPath("licence", value)}
          />
        </ChartCard>

        <ChartCard
          title="By publication year"
          wide
          caption={
            <>
              From <code>published</code>, falling back on <code>created</code>. Records
              carrying neither date are left out.
            </>
          }
        >
          <ColumnChart counts={stats.byYear} />
        </ChartCard>

        <ChartCard
          title="Keywords shared by at least five records"
          wide
          caption="The catalogue publishes 638 distinct keywords, 432 of them used once. Keywords are searched on the Records page, not faceted."
        >
          <BarChart
            counts={stats.topKeywords}
            total={stats.count}
            limit={TOP_N}
            linkTo={(value) => `/records?q=${encodeURIComponent(value)}`}
          />
        </ChartCard>
      </div>
    </>
  );
}
