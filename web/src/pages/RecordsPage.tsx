// Author: Claude (Anthropic) — this file is AI generated, see ../../../docs/init.md.

import { useMemo, type JSX } from "react";
import { useSearchParams } from "react-router";

import { useCatalogue } from "../catalogue";
import { RecordSummary } from "../components/RecordSummary";
import { FACETS, TESTS_PARAM, TEXT_PARAM, UNSTATED, matches } from "../filters";
import { fmt } from "../format";
import { usePageTitle } from "../title";
import type { Count } from "../types";

export function RecordsPage(): JSX.Element {
  const { stats, records, facetsById, haystack } = useCatalogue();
  const [params, setParams] = useSearchParams();
  usePageTitle("Records");

  /* Every filter change replaces the history entry rather than pushing one.
     Typing eight characters is one search, not eight, and Back has to lead out of
     the page — to the chart the filter came from, or to the record just closed —
     not through a transcript of keystrokes. The URL still carries the current
     state, so it can be copied at any point. */
  const update = (param: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(param, value);
    else next.delete(param);
    setParams(next, { replace: true });
  };

  const visible = useMemo(
    () =>
      records.filter((record) =>
        matches(
          record,
          params,
          haystack.get(record.fileIdentifier) ?? "",
          facetsById.get(record.fileIdentifier),
        ),
      ),
    [records, params, haystack, facetsById],
  );

  const hidden = records.length - visible.length;

  return (
    <>
      <form className="filters card" role="search" onSubmit={(e) => e.preventDefault()}>
        <div className="field grow">
          <label htmlFor="f-text">Search</label>
          <input
            type="search"
            id="f-text"
            autoComplete="off"
            placeholder="title, abstract, identifier, keyword…"
            value={params.get(TEXT_PARAM) ?? ""}
            onChange={(event) => update(TEXT_PARAM, event.target.value)}
          />
        </div>

        {FACETS.map((facet) => {
          const options = (stats[facet.options] as Count[]).slice();
          // Only the spatial scope offers it. *Which records did not say?* is a
          // question about that facet — 190 of 326 cite nothing — where an
          // unstated publisher or licence is already visible as its own value.
          // The count comes from `stats.json` rather than from subtracting bars.
          if (facet.param === "scope") {
            options.push({
              value: UNSTATED,
              count: stats.quality.undeclaredSpatialScope,
            });
          }
          return (
            <div className="field" key={facet.param}>
              <label htmlFor={`f-${facet.param}`}>{facet.label}</label>
              <select
                id={`f-${facet.param}`}
                value={params.get(facet.param) ?? ""}
                onChange={(event) => update(facet.param, event.target.value)}
              >
                <option value="">{facet.any}</option>
                {options.map((item) => (
                  <option value={item.value} key={item.value}>
                    {item.value === UNSTATED
                      ? `Not stated (${fmt(item.count)})`
                      : `${item.value} (${fmt(item.count)})`}
                  </option>
                ))}
              </select>
            </div>
          );
        })}

        <div className="field check">
          <label>
            <input
              type="checkbox"
              checked={params.get(TESTS_PARAM) === "1"}
              onChange={(event) => update(TESTS_PARAM, event.target.checked ? "1" : "")}
            />{" "}
            Include suspected test records
          </label>
        </div>

        <button
          type="button"
          className="ghost"
          onClick={() => setParams(new URLSearchParams(), { replace: true })}
        >
          Reset
        </button>
      </form>

      <p className="result-count">
        {`${fmt(visible.length)} of ${fmt(records.length)} records`}
        {hidden ? ` — ${fmt(hidden)} filtered out` : ""}
      </p>

      <div>
        {visible.map((record) => (
          <RecordSummary key={record.fileIdentifier} record={record} />
        ))}
      </div>
    </>
  );
}
