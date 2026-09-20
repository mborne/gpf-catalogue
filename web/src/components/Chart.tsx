// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

/* Every chart on this site plots a single series, so there is a single bar colour
   and no legend: the heading says what is plotted. Colouring each bar by its own
   value would double-encode bar length as hue and spend the only free channel on
   what the chart already shows. */

import { useState, type JSX, type ReactNode } from "react";
import { Link } from "react-router";

import { fmt, share } from "../format";
import type { Count } from "../types";

/** Values of a long tailed aggregate shown before the "show all" button. */
export const TOP_N = 12;

export function ChartCard({
  title,
  caption,
  wide,
  children,
}: {
  title: string;
  caption?: ReactNode;
  wide?: boolean;
  children: ReactNode;
}): JSX.Element {
  return (
    <figure className={wide ? "card chart wide" : "card chart"}>
      <figcaption>
        <h2>{title}</h2>
        {caption ? <p className="caption">{caption}</p> : null}
      </figcaption>
      {children}
    </figure>
  );
}

/** A counted value, with the label drawn at the bar end when it is not the count. */
export type Bar = Count & { label?: string };

export interface BarChartProps {
  counts: Bar[];
  /** Catalogue size, so a bar can be read as a share in its tooltip. */
  total?: number;
  /** Show this many bars before the "show all" button. 0 shows every bar. */
  limit?: number;
  /** Pin the axis to a known whole, for a coverage chart. */
  scale?: number;
  unit?: string;
  /** Route a bar leads to, when the value is one the records page can filter on. */
  linkTo?: (value: string) => string;
}

/**
 * A ranked horizontal bar chart.
 *
 * Every value is labelled at the bar end, which doubles as the table view, so no
 * number is reachable through the tooltip alone.
 */
export function BarChart({
  counts,
  total = 0,
  limit = 0,
  scale = 0,
  unit = "records",
  linkTo,
}: BarChartProps): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  // `scale` pins the axis to a known whole — the catalogue, for a coverage chart —
  // so a bar reads as a share. Without it the longest bar would be full width even
  // when no value comes close to the whole.
  const max = scale || counts.reduce((best, item) => Math.max(best, item.count), 0) || 1;
  const limited = limit > 0 && counts.length > limit;
  const shown = limited && !expanded ? limit : counts.length;

  return (
    <>
      <div className="bars">
        {counts.slice(0, shown).map((item) => {
          const title = total
            ? `${item.value} — ${fmt(item.count)} ${unit}, ${share(item.count, total)} of the catalogue`
            : `${item.value} — ${fmt(item.count)} ${unit}`;
          const label = <span className="bar-label">{item.value}</span>;
          return (
            <div className="bar-row" key={item.value} title={title}>
              {linkTo ? (
                <Link className="bar-link" to={linkTo(item.value)} title={title}>
                  {label}
                </Link>
              ) : (
                label
              )}
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{ width: `${(100 * item.count) / max}%` }}
                />
              </span>
              <span className="bar-value">{item.label ?? fmt(item.count)}</span>
            </div>
          );
        })}
      </div>
      {limited ? (
        <button
          type="button"
          className="ghost chart-more"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show fewer" : `Show all ${counts.length}`}
        </button>
      ) : null}
    </>
  );
}

/** A chronological column chart. Time is the one axis that is not ranked. */
export function ColumnChart({ counts }: { counts: Count[] }): JSX.Element {
  const max = counts.reduce((best, item) => Math.max(best, item.count), 0) || 1;
  // One tick every few columns, so year labels never collide.
  const step = Math.ceil(counts.length / 12) || 1;

  return (
    <>
      <div className="axis-max">{`${fmt(max)} records`}</div>
      <div className="columns">
        {counts.map((item) => (
          <div
            className="column"
            key={item.value}
            title={`${item.value} — ${fmt(item.count)} records`}
          >
            <div
              className="column-fill"
              style={{
                height: `${(100 * item.count) / max}%`,
                // A year with no record draws nothing: the 2px minimum that keeps
                // small bars visible would otherwise make zero look like one.
                ...(item.count ? {} : { minHeight: 0 }),
              }}
            />
          </div>
        ))}
      </div>
      <div className="column-axis">
        {counts.map((item, position) => (
          <div className="column-tick" key={item.value}>
            {position % step === 0 ? item.value : ""}
          </div>
        ))}
      </div>
    </>
  );
}
