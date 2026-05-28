import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getReviewSummary as fetchSummary,
  getAuditLog,
  listReviewDecisions,
  type ReviewSummary as ReviewSummaryData,
  type AuditLogEntry,
  type ReviewDecision,
} from "../api/client";
import { LoadingSpinner, ErrorMessage, EmptyState } from "../components/UI";

function statusColor(status: string): string {
  switch (status) {
    case "accepted":
      return "bg-green-100 text-green-700";
    case "rejected":
      return "bg-red-100 text-red-700";
    case "deferred":
      return "bg-yellow-100 text-yellow-700";
    case "risk-accepted":
      return "bg-orange-100 text-orange-700";
    case "already-fixed":
      return "bg-blue-100 text-blue-700";
    case "duplicate":
      return "bg-gray-100 text-gray-700";
    case "needs-investigation":
      return "bg-purple-100 text-purple-700";
    default:
      return "bg-gray-100 text-gray-600";
  }
}

export default function ReviewSummary() {
  const { repoId } = useParams<{ repoId: string }>();
  const [summary, setSummary] = useState<ReviewSummaryData | null>(null);
  const [decisions, setDecisions] = useState<ReviewDecision[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"summary" | "decisions" | "audit">("summary");

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    Promise.all([fetchSummary(repoId), listReviewDecisions(repoId), getAuditLog(repoId)])
      .then(([s, d, a]) => {
        setSummary(s);
        setDecisions(d.decisions);
        setAuditLog(a.entries);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!summary) return <EmptyState message="No review data available." />;

  const counts = summary.status_counts;
  const total = summary.total_decisions;

  return (
    <div>
      <div className="flex items-center gap-2 mb-6 text-sm text-muted">
        <Link to="/" className="hover:text-primary">Repositories</Link>
        <span>/</span>
        <Link to={`/repositories/${repoId}`} className="hover:text-primary">Detail</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Reviews</span>
      </div>

      <h2 className="text-xl font-semibold text-gray-900 mb-4">Review Summary</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Total Decisions</p>
          <p className="text-2xl font-bold mt-1">{total}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Accepted</p>
          <p className="text-2xl font-bold mt-1 text-green-600">{counts.accepted}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Rejected</p>
          <p className="text-2xl font-bold mt-1 text-red-600">{counts.rejected}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Deferred</p>
          <p className="text-2xl font-bold mt-1 text-yellow-600">{counts.deferred}</p>
        </div>
      </div>

      {/* Status breakdown */}
      <div className="bg-card rounded-lg border border-gray-200 p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Status Breakdown</h3>
        <div className="flex flex-wrap gap-3">
          {Object.entries(counts).map(([status, count]) =>
            count > 0 ? (
              <span key={status} className={`inline-flex items-center px-3 py-1 rounded text-sm font-medium ${statusColor(status)}`}>
                {status.replace(/-/g, " ")}: {count}
              </span>
            ) : null,
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {(["summary", "decisions", "audit"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-primary text-primary"
                : "border-transparent text-muted hover:text-gray-700"
            }`}
          >
            {t === "summary" ? "Summary" : t === "decisions" ? "Decisions" : "Audit Log"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "summary" && (
        <div className="text-sm text-muted">
          <p>
            {total} finding{total !== 1 ? "s" : ""} reviewed.{" "}
            {counts.accepted} accepted, {counts.rejected} rejected,{" "}
            {counts.deferred} deferred,{" "}
            {counts["risk-accepted"]} risk-accepted,{" "}
            {counts["already-fixed"]} already-fixed,{" "}
            {counts.duplicate} duplicate,{" "}
            {counts["needs-investigation"]} needs investigation.
          </p>
          {total === 0 && (
            <p className="mt-2">
              No reviews yet.{" "}
              <Link to={`/repositories/${repoId}/findings`} className="text-primary hover:underline">
                Go to findings →
              </Link>
            </p>
          )}
        </div>
      )}

      {tab === "decisions" && (
        decisions.length === 0 ? (
          <EmptyState message="No review decisions recorded yet." />
        ) : (
          <div className="bg-card rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Finding</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Reviewer</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Rationale</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {decisions.map((d) => (
                  <tr key={d.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{d.finding_id}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColor(d.status)}`}>
                        {d.status}
                      </span>
                      {d.previous_status && (
                        <span className="text-xs text-muted ml-1">← {d.previous_status}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">{d.reviewer || "—"}</td>
                    <td className="px-4 py-3 text-sm max-w-xs truncate">{d.rationale || "—"}</td>
                    <td className="px-4 py-3 text-xs text-muted">
                      {d.updated_at ? new Date(d.updated_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {tab === "audit" && (
        auditLog.length === 0 ? (
          <EmptyState message="No audit history yet." />
        ) : (
          <div className="bg-card rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Time</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Finding</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Reviewer</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Event</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditLog.map((e) => (
                  <tr key={e.id} className={`hover:bg-gray-50 ${e.is_deleted ? "opacity-60" : ""}`}>
                    <td className="px-4 py-3 text-xs text-muted">
                      {e.updated_at ? new Date(e.updated_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{e.finding_id}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColor(e.status)}`}>
                        {e.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">{e.reviewer || "—"}</td>
                    <td className="px-4 py-3 text-sm">
                      {e.is_deleted ? (
                        <span className="text-red-600">Deleted by {e.deleted_by}</span>
                      ) : e.previous_status ? (
                        <span className="text-muted">{e.previous_status} → {e.status}</span>
                      ) : (
                        <span className="text-green-600">Created</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
