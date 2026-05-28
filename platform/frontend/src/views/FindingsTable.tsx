import { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { listFindings, type Finding } from "../api/client";
import { LoadingSpinner, ErrorMessage, EmptyState } from "../components/UI";

const SEVERITIES = ["", "Critical", "High", "Medium", "Low"];
const CATEGORIES = [
  "",
  "TD-DEP",
  "TD-ARCH",
  "TD-CODE",
  "TD-TEST",
  "TD-DOCS",
  "TD-CONFIG",
  "TD-SEC",
  "TD-OBS",
  "TD-OPS",
  "TD-DATA",
  "TD-PROCESS",
  "TD-COMP",
  "TD-PERF",
];

function severityColor(sev: string): string {
  switch (sev) {
    case "Critical":
      return "bg-red-100 text-red-700";
    case "High":
      return "bg-orange-100 text-orange-700";
    case "Medium":
      return "bg-yellow-100 text-yellow-700";
    case "Low":
      return "bg-blue-100 text-blue-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

export default function FindingsTable() {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const severity = searchParams.get("severity") || "";
  const category = searchParams.get("category") || "";

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    setError("");
    listFindings(repoId, {
      severity: severity || undefined,
      category: category || undefined,
    })
      .then((data) => {
        setFindings(data.findings);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId, severity, category]);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-6 text-sm text-muted">
        <Link to="/" className="hover:text-primary">Repositories</Link>
        <span>/</span>
        <Link to={`/repositories/${repoId}`} className="hover:text-primary">Detail</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Findings</span>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          Findings <span className="text-muted font-normal text-base">({total})</span>
        </h2>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={severity}
          onChange={(e) => setFilter("severity", e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s || "All severities"}
            </option>
          ))}
        </select>
        <select
          value={category}
          onChange={(e) => setFilter("category", e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c || "All categories"}
            </option>
          ))}
        </select>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} />}
      {!loading && !error && findings.length === 0 && (
        <EmptyState message="No findings match the current filters." />
      )}

      {!loading && !error && findings.length > 0 && (
        <div className="bg-card rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">ID</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Title</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Severity</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {findings.map((f) => (
                <tr key={f.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-muted">{f.finding_id}</td>
                  <td className="px-4 py-3">{f.title}</td>
                  <td className="px-4 py-3 font-mono text-xs">{f.category}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${severityColor(f.severity)}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">{f.risk_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
