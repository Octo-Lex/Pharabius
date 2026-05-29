import { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  getRepository,
  listRuns,
  type Repository,
  type RunSummary,
} from "../api/client";
import { LoadingSpinner, ErrorMessage } from "../components/UI";

export default function RepositoryDashboard() {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectorOpen, setSelectorOpen] = useState(false);

  const runIdParam = searchParams.get("run_id");

  useEffect(() => {
    if (!repoId) return;
    Promise.all([getRepository(repoId), listRuns(repoId)])
      .then(([repoData, runsData]) => {
        setRepo(repoData);
        setRuns(runsData.runs);

        // Resolve selected run
        if (runIdParam) {
          const found = runsData.runs.find((r) => r.id === runIdParam);
          if (found) {
            setSelectedRun(found);
          } else {
            // run_id not found, fall back to latest
            const latest = runsData.runs.find((r) => r.is_latest) || runsData.runs[0] || null;
            setSelectedRun(latest);
          }
        } else {
          // Default to latest
          const latest = runsData.runs.find((r) => r.is_latest) || runsData.runs[0] || null;
          setSelectedRun(latest);
          if (latest) {
            setSearchParams({ run_id: latest.id }, { replace: true });
          }
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRunSelect = (run: RunSummary) => {
    setSelectedRun(run);
    setSearchParams({ run_id: run.id }, { replace: true });
    setSelectorOpen(false);
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!repo) return <ErrorMessage message="Repository not found" />;

  const run = selectedRun || repo.latest_run;

  // Build child links preserving selected run
  const runQs = selectedRun ? `?run_id=${selectedRun.id}` : "";

  return (
    <div>
      <div className="flex items-center gap-2 mb-6 text-sm text-muted">
        <Link to="/" className="hover:text-primary">Repositories</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">{repo.name}</span>
      </div>

      <h2 className="text-xl font-semibold text-gray-900 mb-4">{repo.name}</h2>

      {/* Run selector */}
      {runs.length > 0 && (
        <div className="bg-card rounded-lg border border-gray-200 p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted uppercase tracking-wide mb-1">Selected Run</p>
              <p className="text-sm font-medium text-gray-900">
                {run?.run_id || "No runs"}
                {run?.branch_name ? ` · ${run.branch_name}` : ""}
                {run?.commit_sha ? ` · ${run.commit_sha.slice(0, 7)}` : ""}
                {run ? ` · ${run.total_findings} findings` : ""}
                {run && run.work_package_count > 0 ? ` · ${run.work_package_count} work packages` : ""}
              </p>
            </div>
            {runs.length > 1 && (
              <div className="relative">
                <button
                  onClick={() => setSelectorOpen(!selectorOpen)}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors flex items-center gap-1"
                >
                  Switch run
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {selectorOpen && (
                  <div className="absolute right-0 top-full mt-1 w-96 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-80 overflow-y-auto">
                    {runs.map((r) => (
                      <button
                        key={r.id}
                        onClick={() => handleRunSelect(r)}
                        className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0 ${
                          r.id === selectedRun?.id ? "bg-blue-50" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{r.run_id}</span>
                          <div className="flex items-center gap-2">
                            {r.is_latest && (
                              <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Latest</span>
                            )}
                            {r.warning_count > 0 && (
                              <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                                {r.warning_count} warning{r.warning_count !== 1 ? "s" : ""}
                              </span>
                            )}
                          </div>
                        </div>
                        <p className="text-xs text-muted mt-0.5">
                          {r.branch_name ? `${r.branch_name} · ` : ""}
                          {r.commit_sha ? `${r.commit_sha.slice(0, 7)} · ` : ""}
                          {r.total_findings} findings
                          {r.work_package_count > 0 ? ` · ${r.work_package_count} work packages` : ""}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {runs.length === 0 && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 mb-6 text-center">
          <p className="text-gray-500">No audit runs uploaded yet.</p>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Total Findings</p>
          <p className="text-2xl font-bold mt-1">{run?.total_findings ?? 0}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Critical + High</p>
          <p className="text-2xl font-bold mt-1 text-red-600">
            {(run?.critical ?? 0) + (run?.high ?? 0)}
          </p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Gate Result</p>
          <p className="text-2xl font-bold mt-1">{run?.gate_result ?? "unknown"}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Run Timestamp</p>
          <p className="text-sm font-medium mt-2">
            {run?.run_timestamp
              ? new Date(run.run_timestamp).toLocaleString()
              : "Never"}
          </p>
        </div>
      </div>

      {/* Severity breakdown */}
      {run && (
        <div className="bg-card rounded-lg border border-gray-200 p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Severity Breakdown</h3>
          <div className="flex gap-4">
            {(["critical", "high", "medium", "low"] as const).map((sev) => {
              const val = run[sev];
              const colors: Record<string, string> = {
                critical: "bg-red-500",
                high: "bg-orange-500",
                medium: "bg-yellow-500",
                low: "bg-blue-500",
              };
              return (
                <div key={sev} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${colors[sev]}`} />
                  <span className="text-sm capitalize">{sev}</span>
                  <span className="font-bold text-sm">{val}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Link
          to={`/repositories/${repoId}/findings${runQs}`}
          className="px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary-dark transition-colors"
        >
          View Findings
        </Link>
        <Link
          to={`/repositories/${repoId}/reviews`}
          className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded hover:bg-gray-50 transition-colors"
        >
          Review Summary
        </Link>
      </div>
    </div>
  );
}
