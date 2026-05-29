import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  listFindings,
  listReviewDecisions,
  createReviewDecision,
  type Finding,
  type ReviewDecision,
  type DecisionStatus,
  type EvidenceReference,
} from "../api/client";
import { LoadingSpinner, ErrorMessage, EmptyState } from "../components/UI";

const SEVERITIES = ["", "Critical", "High", "Medium", "Low"];
const CATEGORIES = [
  "", "TD-DEP", "TD-ARCH", "TD-CODE", "TD-TEST", "TD-DOCS", "TD-CONFIG",
  "TD-SEC", "TD-OBS", "TD-OPS", "TD-DATA", "TD-PROCESS", "TD-COMP", "TD-PERF",
];

const REVIEW_STATUSES: DecisionStatus[] = [
  "accepted", "rejected", "deferred", "needs-investigation",
  "duplicate", "already-fixed", "risk-accepted",
];

function severityColor(sev: string): string {
  switch (sev) {
    case "Critical": return "bg-red-100 text-red-700";
    case "High": return "bg-orange-100 text-orange-700";
    case "Medium": return "bg-yellow-100 text-yellow-700";
    case "Low": return "bg-blue-100 text-blue-700";
    default: return "bg-gray-100 text-gray-700";
  }
}

function reviewBadgeColor(status: string): string {
  switch (status) {
    case "accepted": return "bg-green-100 text-green-700";
    case "rejected": return "bg-red-100 text-red-700";
    case "deferred": return "bg-yellow-100 text-yellow-700";
    case "risk-accepted": return "bg-orange-100 text-orange-700";
    case "already-fixed": return "bg-blue-100 text-blue-700";
    case "duplicate": return "bg-gray-100 text-gray-700";
    case "needs-investigation": return "bg-purple-100 text-purple-700";
    default: return "bg-gray-50 text-gray-400";
  }
}

function EvidenceChip({ reference }: { reference: EvidenceReference }) {
  const [expanded, setExpanded] = useState(false);

  const statusColor: Record<string, string> = {
    resolved: "bg-green-100 text-green-700 border-green-200",
    missing: "bg-yellow-100 text-yellow-700 border-yellow-200",
    legacy_no_evidence_store: "bg-gray-100 text-gray-500 border-gray-200",
    stale: "bg-orange-100 text-orange-700 border-orange-200",
    malformed_reference: "bg-red-100 text-red-700 border-red-200",
    unavailable: "bg-gray-100 text-gray-400 border-gray-200",
  };

  const statusLabel: Record<string, string> = {
    resolved: "resolved",
    missing: "missing",
    legacy_no_evidence_store: "legacy",
    stale: "stale",
    malformed_reference: "malformed",
    unavailable: "unavailable",
  };

  return (
    <div className="border rounded p-2 text-xs">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 w-full text-left hover:opacity-80"
      >
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded font-mono ${statusColor[reference.status] || "bg-gray-50"}`}>
          {reference.evidence_id}
        </span>
        <span className={`text-xs ${reference.status === "resolved" ? "text-green-600" : "text-gray-400"}`}>
          {statusLabel[reference.status] || reference.status}
        </span>
      </button>
      {expanded && reference.evidence && (
        <div className="mt-2 ml-1 space-y-1 text-xs border-t pt-2">
          {reference.evidence.summary && (
            <div><span className="font-medium text-gray-600">Summary:</span> <span className="text-gray-800">{reference.evidence.summary}</span></div>
          )}
          {reference.evidence.file_path && (
            <div><span className="font-medium text-gray-600">Location:</span> <span className="font-mono text-muted">{reference.evidence.file_path}{reference.evidence.line_start ? `:${reference.evidence.line_start}${reference.evidence.line_end ? `-${reference.evidence.line_end}` : ""}` : ""}</span></div>
          )}
          <div><span className="font-medium text-gray-600">Source:</span> {reference.evidence.source}</div>
          <div><span className="font-medium text-gray-600">Type:</span> {reference.evidence.type} / {reference.evidence.category}</div>
          <div><span className="font-medium text-gray-600">Confidence:</span> {reference.evidence.confidence}</div>
        </div>
      )}
      {expanded && !reference.evidence && reference.reason && (
        <p className="mt-1 text-gray-400 italic">{reference.reason}</p>
      )}
    </div>
  );
}

interface ReviewModalProps {
  finding: Finding;
  existing: ReviewDecision | null;
  repoId: string;
  token: string;
  onClose: () => void;
  onSaved: () => void;
}

function ReviewModal({ finding, existing, repoId, token, onClose, onSaved }: ReviewModalProps) {
  const [status, setStatus] = useState<DecisionStatus>(existing?.status ?? "accepted");
  const [reviewer, setReviewer] = useState(existing?.reviewer ?? "");
  const [rationale, setRationale] = useState(existing?.rationale ?? "");
  const [ticketUrl, setTicketUrl] = useState(existing?.ticket_url ?? "");
  const [ownerArea, setOwnerArea] = useState(existing?.owner_area ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showContext, setShowContext] = useState(false);

  const hasDescription = finding.description && finding.description !== finding.title;
  const hasLocations = finding.locations != null && finding.locations.length > 0;
  const hasEvidence = finding.evidence_ids != null && finding.evidence_ids.length > 0;
  const hasEvidenceRefs = finding.evidence_references && finding.evidence_references.length > 0;
  const hasContext = hasDescription || hasLocations || hasEvidenceRefs;

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await createReviewDecision(
        repoId,
        {
          finding_id: finding.finding_id,
          status,
          reviewer,
          rationale,
          ticket_url: ticketUrl,
          owner_area: ownerArea,
        },
        token,
      );
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Review Finding</h3>
        <p className="text-sm text-muted mb-4">
          {finding.finding_id}: {finding.title}
        </p>

        {/* Finding context */}
        {hasContext && (
          <div className="mb-4 border border-gray-200 rounded p-3 bg-gray-50">
            <button
              type="button"
              onClick={() => setShowContext(!showContext)}
              className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-primary w-full text-left"
            >
              <span className={`transform transition-transform ${showContext ? "rotate-90" : ""}`}>&#9654;</span>
              Finding Detail
            </button>
            {showContext && (
              <div className="mt-2 space-y-3 text-sm">
                {hasDescription && (
                  <div>
                    <span className="font-medium text-gray-600">Description</span>
                    <p className="mt-1 text-gray-800 whitespace-pre-wrap break-words">
                      {finding.description}
                    </p>
                  </div>
                )}
                {!hasDescription && (
                  <p className="text-gray-400 italic">No description provided.</p>
                )}
                {hasLocations && (
                  <div>
                    <span className="font-medium text-gray-600">Locations</span>
                    <ul className="mt-1 ml-1 space-y-0.5">
                      {(finding.locations ?? []).map((loc, i) => (
                        <li
                          key={i}
                          className="font-mono text-xs text-muted break-all"
                          title={loc}
                        >
                          {loc}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {!hasLocations && (
                  <p className="text-gray-400 italic">No locations provided.</p>
                )}
                {hasEvidenceRefs && (
                  <div>
                    <span className="font-medium text-gray-600">Evidence References</span>
                    <div className="mt-1 space-y-1">
                      {finding.evidence_references.map((ref, i) => (
                        <EvidenceChip key={i} reference={ref} />
                      ))}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Only resolved evidence from the same upload can support a finding.
                    </p>
                  </div>
                )}
                {!hasEvidenceRefs && hasEvidence && (
                  <p className="text-gray-400 italic">No evidence references provided.</p>
                )}
              </div>
            )}
          </div>
        )}

        {error && <ErrorMessage message={error} />}

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as DecisionStatus)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm bg-white"
            >
              {REVIEW_STATUSES.map((s) => (
                <option key={s} value={s}>{s.replace(/-/g, " ")}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reviewer <span className="text-muted text-xs">(advisory, not verified identity)</span>
            </label>
            <input
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="Your name"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rationale</label>
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              placeholder="Why this decision?"
              rows={2}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ticket URL</label>
              <input
                type="text"
                value={ticketUrl}
                onChange={(e) => setTicketUrl(e.target.value)}
                placeholder="https://..."
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner area</label>
              <input
                type="text"
                value={ownerArea}
                onChange={(e) => setOwnerArea(e.target.value)}
                placeholder="Team name"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-muted hover:text-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !status}
            className="px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary-dark transition-colors disabled:opacity-50"
          >
            {saving ? "Saving…" : existing ? "Update" : "Save Decision"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function FindingsTable() {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [reviews, setReviews] = useState<Map<string, ReviewDecision>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewModal, setReviewModal] = useState<Finding | null>(null);
  const [token, setToken] = useState(() => localStorage.getItem("pharabius_token") ?? "");
  const [showTokenInput, setShowTokenInput] = useState(() => !localStorage.getItem("pharabius_token"));

  const severity = searchParams.get("severity") || "";
  const category = searchParams.get("category") || "";
  const runId = searchParams.get("run_id") || undefined;

  const loadReviews = useCallback(async () => {
    if (!repoId) return;
    try {
      const data = await listReviewDecisions(repoId);
      const map = new Map<string, ReviewDecision>();
      for (const d of data.decisions) {
        map.set(d.finding_id, d);
      }
      setReviews(map);
    } catch {
      // Reviews are optional — don't block
    }
  }, [repoId]);

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    setError("");
    listFindings(repoId, {
      severity: severity || undefined,
      category: category || undefined,
      runId,
    })
      .then((data) => {
        setFindings(data.findings);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId, severity, category, runId]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  const reviewed = findings.filter((f) => reviews.has(f.finding_id)).length;

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
        <Link
          to={`/repositories/${repoId}/reviews`}
          className="text-primary hover:underline text-sm"
        >
          Reviews ({reviewed}/{total})
        </Link>
      </div>

      {/* Review progress bar */}
      {reviewed > 0 && (
        <div className="mb-4 bg-gray-200 rounded-full h-2">
          <div
            className="bg-green-500 rounded-full h-2 transition-all"
            style={{ width: `${(reviewed / total) * 100}%` }}
          />
          <p className="text-xs text-muted mt-1">{reviewed} of {total} findings reviewed</p>
        </div>
      )}

      {/* Token input */}
      <div className="mb-4 flex items-center gap-2 text-sm">
        {showTokenInput || !token ? (
          <>
            <input
              type="password"
              placeholder="Enter admin token to review findings"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1 max-w-xs"
              onKeyDown={(e) => {
                if (e.key === "Enter" && token) {
                  localStorage.setItem("pharabius_token", token);
                  setShowTokenInput(false);
                }
              }}
            />
            {token && (
              <button
                onClick={() => {
                  localStorage.setItem("pharabius_token", token);
                  setShowTokenInput(false);
                }}
                className="px-3 py-1.5 bg-primary text-white text-sm rounded hover:bg-primary-dark"
              >
                Save
              </button>
            )}
            <span className="text-muted text-xs">
              Token stored locally in your browser. Not sent to any server except the Pharabius backend.
            </span>
          </>
        ) : (
          <>
            <span className="text-muted">Token: ••••••••••</span>
            <button
              onClick={() => setShowTokenInput(true)}
              className="text-primary hover:underline text-xs"
            >
              Change
            </button>
          </>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={severity}
          onChange={(e) => setFilter("severity", e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          {SEVERITIES.map((s) => <option key={s} value={s}>{s || "All severities"}</option>)}
        </select>
        <select
          value={category}
          onChange={(e) => setFilter("category", e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
        >
          {CATEGORIES.map((c) => <option key={c} value={c}>{c || "All categories"}</option>)}
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Review</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {findings.map((f) => {
                const review = reviews.get(f.finding_id);
                return (
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
                    <td className="px-4 py-3">
                      {review ? (
                        <button
                          onClick={() => setReviewModal(f)}
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium cursor-pointer hover:opacity-80 ${reviewBadgeColor(review.status)}`}
                        >
                          {review.status}
                        </button>
                      ) : (
                        <button
                          onClick={() => token ? setReviewModal(f) : undefined}
                          disabled={!token}
                          className="text-xs text-muted hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
                          title={!token ? "Enter admin token above to review" : "Click to review"}
                        >
                          Review
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Review modal */}
      {reviewModal && repoId && (
        <ReviewModal
          finding={reviewModal}
          existing={reviews.get(reviewModal.finding_id) ?? null}
          repoId={repoId}
          token={token}
          onClose={() => setReviewModal(null)}
          onSaved={loadReviews}
        />
      )}
    </div>
  );
}
