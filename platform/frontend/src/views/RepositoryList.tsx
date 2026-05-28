import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRepositories, type Repository } from "../api/client";
import { LoadingSpinner, ErrorMessage, EmptyState } from "../components/UI";

function severityBadge(count: number, label: string, color: string) {
  if (count === 0) return null;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {count} {label}
    </span>
  );
}

export default function RepositoryList() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listRepositories()
      .then((data) => setRepos(data.repositories))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (repos.length === 0) return <EmptyState message="No repositories yet. Upload an artifact bundle to get started." />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Repositories</h2>
        <Link
          to="/upload"
          className="px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary-dark transition-colors"
        >
          Upload Bundle
        </Link>
      </div>

      <div className="bg-card rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Repository</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Last Upload</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Findings</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Severity</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Gate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {repos.map((repo) => (
              <tr key={repo.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link to={`/repositories/${repo.id}`} className="text-primary hover:underline font-medium">
                    {repo.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">
                  {repo.last_uploaded_at
                    ? new Date(repo.last_uploaded_at).toLocaleDateString()
                    : "—"}
                </td>
                <td className="px-4 py-3 text-center">
                  {repo.latest_run?.total_findings ?? "—"}
                </td>
                <td className="px-4 py-3 space-x-1">
                  {repo.latest_run && (
                    <>
                      {severityBadge(repo.latest_run.critical, "Critical", "bg-red-100 text-red-700")}
                      {severityBadge(repo.latest_run.high, "High", "bg-orange-100 text-orange-700")}
                      {severityBadge(repo.latest_run.medium, "Med", "bg-yellow-100 text-yellow-700")}
                      {severityBadge(repo.latest_run.low, "Low", "bg-blue-100 text-blue-700")}
                    </>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      repo.latest_run?.gate_result === "pass"
                        ? "bg-green-100 text-green-700"
                        : repo.latest_run?.gate_result === "warn"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {repo.latest_run?.gate_result ?? "unknown"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
