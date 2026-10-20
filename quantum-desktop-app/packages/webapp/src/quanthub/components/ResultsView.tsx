import { formatDate, formatProbability } from "../client";
import type { DecoderResult, RunDetail } from "../types";
import { RunStatusPill } from "./ui";

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return formatProbability(value);
}

function DecoderRow({ row }: { row: DecoderResult }): JSX.Element {
  return (
    <tr>
      <td className="qh-mono">{row.decoder}</td>
      <td className="text-right">{row.trials?.toLocaleString() ?? "—"}</td>
      <td className="text-right">{row.operational_failures?.toLocaleString() ?? "—"}</td>
      <td className="text-right">{row.logical_failures?.toLocaleString() ?? "—"}</td>
      <td className="text-right font-semibold text-[#e6edf3]">{pct(row.probability)}</td>
      <td className="text-right text-[#9198a1]">
        {row.interval_low !== null && row.interval_high !== null
          ? `${pct(row.interval_low)} – ${pct(row.interval_high)}`
          : row.zero_failure_upper_bound !== null
            ? `≤ ${pct(row.zero_failure_upper_bound)} (0 failures)`
            : "—"}
      </td>
      <td className="text-[11px] text-[#8b949e]">
        {row.method ? `${row.method}${row.confidence_level ? ` ${(row.confidence_level * 100).toFixed(0)}%` : ""}` : "—"}
      </td>
    </tr>
  );
}

function ComparisonRow({ comparison }: { comparison: Record<string, unknown> }): JSX.Element {
  const first = String(comparison.first ?? "?");
  const second = String(comparison.second ?? "?");
  const difference = comparison.difference_first_minus_second;
  const mcnemar = comparison.mcnemar as Record<string, unknown> | undefined;
  const pValue = typeof mcnemar?.p_value === "number" ? (mcnemar.p_value as number) : null;
  return (
    <tr>
      <td className="qh-mono">
        {first} vs {second}
      </td>
      <td className="text-right">
        {typeof difference === "number"
          ? `${difference > 0 ? "+" : ""}${(difference * 100).toFixed(3)} pp`
          : "—"}
      </td>
      <td className="text-right">{String(comparison.first_only ?? "—")}</td>
      <td className="text-right">{String(comparison.second_only ?? "—")}</td>
      <td className="text-right">{pValue === null ? "—" : pValue.toExponential(2)}</td>
    </tr>
  );
}

export function ResultsView({ run }: { run: RunDetail }): JSX.Element {
  const results = run.results;
  const summary = run.summary as Record<string, unknown> | null;
  const provenance = (summary?.provenance ?? {}) as Record<string, unknown>;
  const scientificStatus =
    run.scientific_status ?? (summary?.scientific_status as string | undefined) ?? null;

  return (
    <div className="space-y-4">
      <div className="qh-card">
        <div className="qh-card-header flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 text-[14px] font-semibold">Execution</h2>
          <RunStatusPill status={run.status} />
        </div>
        <div className="qh-card-body">
          <dl className="grid gap-x-6 gap-y-2 text-[12px] sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="text-[#6e7681]">Run</dt>
              <dd className="qh-mono m-0">{run.id}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Started</dt>
              <dd className="m-0">{formatDate(run.started_at ?? run.created_at)}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Finished</dt>
              <dd className="m-0">{formatDate(run.finished_at)}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Config hash</dt>
              <dd className="qh-mono m-0 truncate" title={run.config_hash ?? undefined}>
                {run.config_hash ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Project revision</dt>
              <dd className="qh-mono m-0">{run.project_revision?.slice(0, 12) ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Engine revision</dt>
              <dd className="qh-mono m-0">{run.software_revision?.slice(0, 12) ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Backend</dt>
              <dd className="m-0">{results?.backend ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Shots</dt>
              <dd className="m-0">{results?.shots?.toLocaleString() ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[#6e7681]">Scientific status</dt>
              <dd className="m-0">{scientificStatus ?? "not assessed"}</dd>
            </div>
            {run.reproduction_of && (
              <div>
                <dt className="text-[#6e7681]">Reproduction of</dt>
                <dd className="qh-mono m-0">{run.reproduction_of}</dd>
              </div>
            )}
          </dl>

          {run.error && (
            <div className="qh-form-error mt-3" role="alert">
              <strong>Run failed:</strong> {run.error}
            </div>
          )}

          {run.status === "failed" && !run.results && (
            <p className="qh-help mb-0 mt-3">
              No result table is shown because the engine did not produce a summary. The log and
              any partial artifacts are preserved for diagnosis.
            </p>
          )}
          {!run.results && (run.status === "queued" || run.status === "running") && (
            <p className="qh-help mb-0 mt-3">
              This run is still {run.status}. Results appear only after the engine writes and
              verifies its artifact directory.
            </p>
          )}
        </div>
      </div>

      {results && results.decoders.length > 0 && (
        <div className="qh-card overflow-hidden">
          <div className="qh-card-header">
            <h2 className="m-0 text-[14px] font-semibold">Failure probabilities by decoder</h2>
            <span className="text-[11px] text-[#6e7681]">
              Operational failure counts include wrong logical outcomes, invalid residuals and
              decoder errors. Computed by the engine; QuantHub does not recalculate them.
            </span>
          </div>
          <table className="qh-data">
            <thead>
              <tr>
                <th scope="col">Decoder</th>
                <th scope="col" className="text-right">Trials</th>
                <th scope="col" className="text-right">Operational failures</th>
                <th scope="col" className="text-right">Logical failures</th>
                <th scope="col" className="text-right">Operational failure p</th>
                <th scope="col" className="text-right">Interval</th>
                <th scope="col">Method</th>
              </tr>
            </thead>
            <tbody>
              {results.decoders.map((row) => (
                <DecoderRow key={row.decoder} row={row} />
              ))}
            </tbody>
          </table>
          {results.decoders.some((row) => row.interpretation) && (
            <ul className="m-0 border-t border-[#21262d] px-4 py-2 text-[11px] text-[#8b949e]">
              {results.decoders
                .filter((row) => row.interpretation)
                .map((row) => (
                  <li key={`note-${row.decoder}`}>
                    <span className="qh-mono">{row.decoder}</span>: {row.interpretation}
                  </li>
                ))}
            </ul>
          )}
          {results.decoder_limits && (
            <p className="m-0 border-t border-[#21262d] px-4 py-2 text-[11px] text-[#e3b341]">
              {results.decoder_limits}
            </p>
          )}
        </div>
      )}

      {results && results.comparisons.length > 0 && (
        <div className="qh-card overflow-hidden">
          <div className="qh-card-header">
            <h2 className="m-0 text-[14px] font-semibold">Paired comparisons</h2>
            <span className="text-[11px] text-[#6e7681]">Exact McNemar on paired shots</span>
          </div>
          <table className="qh-data">
            <thead>
              <tr>
                <th scope="col">Comparison</th>
                <th scope="col" className="text-right">Δ (first − second)</th>
                <th scope="col" className="text-right">First only</th>
                <th scope="col" className="text-right">Second only</th>
                <th scope="col" className="text-right">p</th>
              </tr>
            </thead>
            <tbody>
              {results.comparisons.map((comparison, index) => (
                <ComparisonRow key={index} comparison={comparison} />
              ))}
            </tbody>
          </table>
          <p className="m-0 border-t border-[#21262d] px-4 py-2 text-[11px] text-[#8b949e]">
            No multiplicity correction is applied. Treat exploratory p-values accordingly.
          </p>
        </div>
      )}

      {results && (results.code || results.noise) && (
        <div className="qh-card">
          <div className="qh-card-header">
            <h2 className="m-0 text-[14px] font-semibold">Code and noise</h2>
          </div>
          <div className="qh-card-body grid gap-4 sm:grid-cols-2">
            <div>
              <h3 className="qh-side-title">Code</h3>
              <pre className="qh-code m-0 max-h-56 overflow-auto">
                {JSON.stringify(results.code ?? {}, null, 2)}
              </pre>
            </div>
            <div>
              <h3 className="qh-side-title">Noise model</h3>
              <pre className="qh-code m-0 max-h-56 overflow-auto">
                {JSON.stringify(results.noise ?? {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {Object.keys(provenance).length > 0 && (
        <div className="qh-card">
          <div className="qh-card-header">
            <h2 className="m-0 text-[14px] font-semibold">Provenance</h2>
          </div>
          <pre className="qh-code m-0 max-h-64 overflow-auto border-0">
            {JSON.stringify(provenance, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
