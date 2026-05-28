import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getRepository, type Repository } from "../api/client";
import { LoadingSpinner, ErrorMessage } from "../components/UI";

export default function RepositoryDashboard() {
  const { repoId } = useParams<{ repoId: string }>();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!repoId) return;
    getRepository(repoId)
      .then(setRepo)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!repo) return <ErrorMessage message="Repository not found" />;

  const run = repo.latest_run;

  return (
    <div>
      <div className="flex items-center gap-2 mb-6 text-sm text-muted">
        <Link to="/" className="hover:text-primary">Repositories</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">{repo.name}</span>
      </div>

      <h2 className="text-xl font-semibold text-gray-900 mb-4">{repo.name}</h2>

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
          <p className="text-xs text-muted uppercase tracking-wide">Last Run</p>
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
          to={`/repositories/${repoId}/findings`}
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
