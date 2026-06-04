import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import {
  compareRuns,
  listRuns,
  type RunSummary,
  type RunComparisonResponse,
  type FindingDelta,
  type WorkPackageDelta,
} from "../api/client";

/** Human-readable labels for delta fields. */
const FIELD_LABELS: Record<string, string> = {
  title: "Title",
  category: "Category",
  issue_type: "Issue Type",
  description: "Description",
  severity: "Severity",
  confidence: "Confidence",
  risk_score: "Risk Score",
  priority: "Priority",
  locations: "Locations",
  evidence_ids: "Evidence IDs",
  objective: "Objective",
  current_risk: "Current Risk",
  estimated_effort: "Estimated Effort",
  expected_risk_reduction: "Expected Risk Reduction",
  suggested_owner_area: "Suggested Owner Area",
  status: "Status",
  recommended_engineering_approach: "Recommended Approach",
  expected_affected_areas: "Affected Areas",
  preconditions: "Preconditions",
  verification_recommendations: "Verification",
  risks_and_cautions: "Risks & Cautions",
  definition_of_done: "Definition of Done",
  declared_evidence_ids: "Evidence IDs",
  linked_debt_item_ids: "Linked Findings",
};

function statusColor(s: string): string {
  switch (s) {
    case "added":
      return "text-green-700 bg-green-100";
    case "removed":
      return "text-red-700 bg-red-100";
    case "changed":
      return "text-amber-700 bg-amber-100";
    case "unchanged":
      return "text-gray-600 bg-gray-100";
    case "improved":
      return "text-green-700";
    case "regressed":
      return "text-red-700";
    case "unavailable":
      return "text-gray-500 italic";
    default:
      return "";
  }
}

function traceLabel(s: string): string {
  switch (s) {
    case "improved":
      return "↑ Improved";
    case "regressed":
      return "↓ Regressed";
    case "unchanged":
      return "— Unchanged";
    case "unavailable":
      return "N/A";
    default:
      return s;
  }
}

function FindingDeltaRow({ delta }: { delta: FindingDelta }) {
  return (
    <tr className="border-b last:border-b-0">
      <td className="px-3 py-2 font-mono text-sm">{delta.finding_id}</td>
      <td className="px-3 py-2">
        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${statusColor(delta.status)}`}>
          {delta.status}
        </span>
      </td>
      <td className="px-3 py-2 text-sm">
        {delta.changed_fields.length > 0
          ? delta.changed_fields.map((f) => FIELD_LABELS[f] ?? f).join(", ")
          : "—"}
      </td>
      <td className="px-3 py-2 text-sm">
        {delta.traceability_change ? (
          <span className={statusColor(delta.traceability_change.status)}>
            {traceLabel(delta.traceability_change.status)}
          </span>
        ) : (
          "—"
        )}
      </td>
    </tr>
  );
}

function WpDeltaRow({ delta }: { delta: WorkPackageDelta }) {
  return (
    <tr className="border-b last:border-b-0">
      <td className="px-3 py-2 font-mono text-sm">{delta.package_id}</td>
      <td className="px-3 py-2">
        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${statusColor(delta.status)}`}>
          {delta.status}
        </span>
      </td>
      <td className="px-3 py-2 text-sm">
        {delta.changed_fields.length > 0
          ? delta.changed_fields.map((f) => FIELD_LABELS[f] ?? f).join(", ")
          : "—"}
      </td>
      <td className="px-3 py-2 text-sm">
        {delta.traceability_change ? (
          <span className={statusColor(delta.traceability_change.status)}>
            {traceLabel(delta.traceability_change.status)}
          </span>
        ) : (
          "—"
        )}
      </td>
    </tr>
  );
}

export default function RunComparison() {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RunComparisonResponse | null>(null);

  const baselineId = searchParams.get("baseline_run_id") ?? "";
  const comparisonId = searchParams.get("comparison_run_id") ?? "";

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    listRuns(repoId)
      .then((data) => {
        setRuns(data.runs);
        // Auto-set defaults if both params missing and ≥2 runs
        if (!baselineId && !comparisonId && data.runs.length >= 2) {
          setSearchParams(
            {
              baseline_run_id: data.runs[1].id,
              comparison_run_id: data.runs[0].id,
            },
            { replace: true },
          );
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [repoId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!repoId || !baselineId || !comparisonId) return;
    setLoading(true);
    setError(null);
    compareRuns(repoId, baselineId, comparisonId)
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [repoId, baselineId, comparisonId]);

  const handleBaselineChange = (value: string) => {
    setSearchParams({ baseline_run_id: value, comparison_run_id: comparisonId });
  };

  const handleComparisonChange = (value: string) => {
    setSearchParams({ baseline_run_id: baselineId, comparison_run_id: value });
  };

  if (!repoId) return null;

  if (loading && !result) {
    return (
      <div className="p-6">
        <p className="text-gray-500">Loading comparison…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (runs.length < 2) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-semibold mb-4">Run Comparison</h1>
        <p className="text-gray-500">
          At least two runs are required to compare. This repository has{" "}
          {runs.length} run{runs.length === 1 ? "" : "s"}.
        </p>
        <Link
          to={`/repositories/${repoId}`}
          className="mt-4 inline-block text-blue-600 hover:underline"
        >
          ← Back to repository
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-xl font-semibold">Run Comparison</h1>
        <Link
          to={`/repositories/${repoId}`}
          className="text-blue-600 hover:underline text-sm"
        >
          ← Repository
        </Link>
      </div>

      {/* Run selectors */}
      <div className="flex gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Baseline
          </label>
          <select
            value={baselineId}
            onChange={(e) => handleBaselineChange(e.target.value)}
            className="border rounded px-3 py-2 text-sm min-w-[220px]"
          >
            <option value="">— Select baseline —</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.run_id} ({new Date(r.run_timestamp).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Comparison
          </label>
          <select
            value={comparisonId}
            onChange={(e) => handleComparisonChange(e.target.value)}
            className="border rounded px-3 py-2 text-sm min-w-[220px]"
          >
            <option value="">— Select comparison —</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.run_id} ({new Date(r.run_timestamp).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <p className="text-gray-500">Loading…</p>}

      {result && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="border rounded p-4">
              <h2 className="text-sm font-semibold text-gray-600 mb-2">
                Findings
              </h2>
              <div className="flex gap-4 text-sm">
                <span className="text-green-700">
                  +{result.summary.findings.added} added
                </span>
                <span className="text-red-700">
                  −{result.summary.findings.removed} removed
                </span>
                <span className="text-amber-700">
                  ≠{result.summary.findings.changed} changed
                </span>
                <span className="text-gray-500">
                  {result.summary.findings.unchanged} unchanged
                </span>
              </div>
            </div>
            <div className="border rounded p-4">
              <h2 className="text-sm font-semibold text-gray-600 mb-2">
                Work Packages
              </h2>
              <div className="flex gap-4 text-sm">
                <span className="text-green-700">
                  +{result.summary.work_packages.added} added
                </span>
                <span className="text-red-700">
                  −{result.summary.work_packages.removed} removed
                </span>
                <span className="text-amber-700">
                  ≠{result.summary.work_packages.changed} changed
                </span>
                <span className="text-gray-500">
                  {result.summary.work_packages.unchanged} unchanged
                </span>
              </div>
            </div>
          </div>

          {/* Traceability */}
          <div className="border rounded p-4 mb-6">
            <h2 className="text-sm font-semibold text-gray-600 mb-2">
              Traceability
            </h2>
            <div className="flex gap-8 text-sm">
              <div>
                <span className="font-medium">Evidence: </span>
                <span className={statusColor(result.traceability_delta.evidence.status)}>
                  {traceLabel(result.traceability_delta.evidence.status)}
                </span>
                {" ("}
                {result.traceability_delta.evidence.baseline_unique_resolved}/
                {result.traceability_delta.evidence.baseline_unique_total} →{" "}
                {result.traceability_delta.evidence.comparison_unique_resolved}/
                {result.traceability_delta.evidence.comparison_unique_total} resolved)
              </div>
              <div>
                <span className="font-medium">WP Links: </span>
                <span className={statusColor(result.traceability_delta.work_package_links.status)}>
                  {traceLabel(result.traceability_delta.work_package_links.status)}
                </span>
                {" ("}
                {result.traceability_delta.work_package_links.baseline_resolved}/
                {result.traceability_delta.work_package_links.baseline_total} →{" "}
                {result.traceability_delta.work_package_links.comparison_resolved}/
                {result.traceability_delta.work_package_links.comparison_total} resolved)
              </div>
            </div>
          </div>

          {/* Findings Delta Table */}
          {result.findings_delta.length > 0 && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-gray-600 mb-2">
                Findings Delta
              </h2>
              <table className="w-full border rounded text-left">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="px-3 py-2">ID</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Changed Fields</th>
                    <th className="px-3 py-2">Traceability</th>
                  </tr>
                </thead>
                <tbody>
                  {result.findings_delta.map((d) => (
                    <FindingDeltaRow key={d.finding_id} delta={d} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Work Packages Delta Table */}
          {result.work_packages_delta.length > 0 && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-gray-600 mb-2">
                Work Packages Delta
              </h2>
              <table className="w-full border rounded text-left">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="px-3 py-2">Package</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Changed Fields</th>
                    <th className="px-3 py-2">Traceability</th>
                  </tr>
                </thead>
                <tbody>
                  {result.work_packages_delta.map((d) => (
                    <WpDeltaRow key={d.package_id} delta={d} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
