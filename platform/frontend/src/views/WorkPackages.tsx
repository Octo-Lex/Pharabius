import { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import {
  listWorkPackages,
  getWorkPackageDetail,
  type WorkPackageSummary,
  type WorkPackageDetail,
  type LinkedFinding,
} from "../api/client";
import { LoadingSpinner, ErrorMessage, EmptyState } from "../components/UI";
import { EvidenceChip } from "../components/EvidenceChip";

function LinkedFindingCard({ linked }: { linked: LinkedFinding }) {
  const statusStyles: Record<string, string> = {
    resolved: "border-green-200 bg-green-50/50",
    missing: "border-yellow-200 bg-yellow-50/50",
    malformed_reference: "border-red-200 bg-red-50/50",
    unavailable: "border-gray-200 bg-gray-50/50",
  };

  const statusBadge: Record<string, string> = {
    resolved: "bg-green-100 text-green-700",
    missing: "bg-yellow-100 text-yellow-700",
    malformed_reference: "bg-red-100 text-red-700",
    unavailable: "bg-gray-100 text-gray-500",
  };

  return (
    <div className={`border rounded p-3 ${statusStyles[linked.status] || "border-gray-200"}`}>
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`text-xs px-1.5 py-0.5 rounded ${
            statusBadge[linked.status] || "bg-gray-100"
          }`}
        >
          {linked.status}
        </span>
      </div>

      {linked.status === "resolved" && linked.finding ? (
        <div>
          <p className="text-sm font-medium text-gray-900">
            {linked.finding.finding_id} · {linked.finding.title}
          </p>
          <p className="text-xs text-muted mt-0.5">
            Severity: {linked.finding.severity} · Confidence:{" "}
            {linked.finding.confidence} · Category: {linked.finding.category}
          </p>
          {linked.evidence_references.length > 0 && (
            <div className="mt-2 space-y-1">
              <p className="text-xs font-medium text-gray-600">
                Evidence references ({linked.evidence_references.length})
              </p>
              {linked.evidence_references.map((ref) => (
                <EvidenceChip key={ref.evidence_id} reference={ref} />
              ))}
            </div>
          )}
        </div>
      ) : linked.status === "missing" ? (
        <div>
          <p className="text-sm font-medium text-gray-700">
            {linked.debt_item_id} · Missing linked finding
          </p>
          <p className="text-xs text-muted mt-0.5">
            This work package references a finding that was not found in this
            run.
          </p>
          {linked.reason && (
            <p className="text-xs text-gray-400 italic mt-1">{linked.reason}</p>
          )}
        </div>
      ) : linked.status === "malformed_reference" ? (
        <div>
          <p className="text-sm font-medium text-gray-700">
            Malformed linked finding reference
          </p>
          <p className="text-xs text-muted mt-0.5">
            The linked debt item is empty or invalid.
          </p>
          {linked.reason && (
            <p className="text-xs text-gray-400 italic mt-1">
              {linked.reason}
            </p>
          )}
        </div>
      ) : (
        <div>
          <p className="text-sm text-gray-500">
            {linked.debt_item_id} · Unavailable
          </p>
          {linked.reason && (
            <p className="text-xs text-gray-400 italic mt-1">
              {linked.reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SectionList({
  label,
  items,
}: {
  label: string;
  items: string[];
}) {
  if (!items.length) {
    return (
      <div>
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
          {label}
        </p>
        <p className="text-sm text-muted">None provided.</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
        {label}
      </p>
      <ul className="list-disc ml-4 text-sm text-gray-700 space-y-0.5">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function ChecklistItems({
  label,
  items,
}: {
  label: string;
  items: string[];
}) {
  if (!items.length) {
    return (
      <div>
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
          {label}
        </p>
        <p className="text-sm text-muted">None provided.</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
        {label}
      </p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
            <span className="text-gray-400 mt-0.5">☐</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WorkPackageCard({
  summary,
  repoId,
  runId,
}: {
  summary: WorkPackageSummary;
  repoId: string;
  runId: string | undefined;
}) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<WorkPackageDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleExpand() {
    if (expanded) {
      setExpanded(false);
      return;
    }

    if (detail) {
      setExpanded(true);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const d = await getWorkPackageDetail(repoId, summary.package_id, {
        runId,
        includeFindings: true,
        includeEvidence: true,
      });
      setDetail(d);
      setExpanded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load detail");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-card rounded-lg border border-gray-200">
      {/* Collapsed header */}
      <button
        type="button"
        onClick={handleExpand}
        className="w-full text-left px-4 py-3 hover:bg-gray-50 rounded-lg transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-mono font-semibold text-gray-900">
              {summary.package_id}
            </span>
            <span className="text-sm text-gray-700">{summary.title}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted">
            {summary.status && (
              <span className="px-1.5 py-0.5 bg-gray-100 rounded">
                {summary.status}
              </span>
            )}
            {summary.estimated_effort && (
              <span>Effort: {summary.estimated_effort}</span>
            )}
            <span>
              {expanded ? "▲" : "▼"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 mt-1.5 text-xs text-muted">
          <span>
            Findings: {summary.linked_finding_count} linked ·{" "}
            {summary.resolved_finding_count} resolved ·{" "}
            {summary.missing_finding_count} missing
          </span>
          <span>Declared evidence: {summary.declared_evidence_count}</span>
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && detail && (
        <div className="px-4 pb-4 border-t border-gray-100">
          {error && <ErrorMessage message={error} />}

          <div className="mt-4 space-y-4">
            {/* Objective */}
            {detail.objective ? (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Objective
                </p>
                <p className="text-sm text-gray-800 whitespace-pre-line">
                  {detail.objective}
                </p>
              </div>
            ) : (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Objective
                </p>
                <p className="text-sm text-muted">Not provided.</p>
              </div>
            )}

            {/* Current risk */}
            {detail.current_risk && (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Current Risk
                </p>
                <p className="text-sm text-gray-800 whitespace-pre-line">
                  {detail.current_risk}
                </p>
              </div>
            )}

            {/* Linked findings */}
            {detail.linked_findings.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                  Linked Findings ({detail.linked_findings.length})
                </p>
                <div className="space-y-2">
                  {detail.linked_findings.map((lf) => (
                    <LinkedFindingCard
                      key={lf.debt_item_id}
                      linked={lf}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Engineering approach */}
            <SectionList
              label="Recommended Engineering Approach"
              items={detail.recommended_engineering_approach}
            />

            {/* Affected areas */}
            <SectionList
              label="Expected Affected Areas"
              items={detail.expected_affected_areas}
            />

            {/* Preconditions */}
            <SectionList
              label="Preconditions"
              items={detail.preconditions}
            />

            {/* Verification recommendations */}
            <SectionList
              label="Verification Recommendations"
              items={detail.verification_recommendations}
            />

            {/* Risks and cautions */}
            <SectionList
              label="Risks and Cautions"
              items={detail.risks_and_cautions}
            />

            {/* Expected risk reduction */}
            {detail.expected_risk_reduction && (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Expected Risk Reduction
                </p>
                <p className="text-sm text-gray-800">
                  {detail.expected_risk_reduction}
                </p>
              </div>
            )}

            {/* Suggested owner area */}
            {detail.suggested_owner_area && (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Suggested Owner Area
                </p>
                <p className="text-sm text-gray-800">
                  {detail.suggested_owner_area}
                </p>
              </div>
            )}

            {/* Definition of done */}
            <ChecklistItems
              label="Definition of Done"
              items={detail.definition_of_done}
            />
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="flex items-center justify-center py-6">
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-primary border-t-transparent" />
            <span className="ml-2 text-muted text-xs">Loading detail…</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function WorkPackages() {
  const { repoId } = useParams<{ repoId: string }>();
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id") ?? undefined;

  const [packages, setPackages] = useState<WorkPackageSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    setError("");
    listWorkPackages(repoId, runId)
      .then((res) => {
        setPackages(res.work_packages);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repoId, runId]);

  const runQs = runId ? `?run_id=${runId}` : "";

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!repoId) return <ErrorMessage message="Repository not found" />;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-6 text-sm text-muted">
        <Link to="/" className="hover:text-primary">
          Repositories
        </Link>
        <span>/</span>
        <Link
          to={`/repositories/${repoId}${runQs}`}
          className="hover:text-primary"
        >
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Work Packages</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          Work Packages
          {total > 0 && (
            <span className="text-muted font-normal text-base ml-2">
              {total} package{total !== 1 ? "s" : ""}
            </span>
          )}
        </h2>
      </div>

      {/* Run context notice */}
      {!runId && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-2 rounded text-sm mb-4">
          Viewing latest run. Select a specific run from the{" "}
          <Link
            to={`/repositories/${repoId}`}
            className="underline hover:text-blue-900"
          >
            repository dashboard
          </Link>{" "}
          for deterministic review links.
        </div>
      )}

      {/* Empty states */}
      {packages.length === 0 && runId && (
        <EmptyState message="No work packages included in this run." />
      )}
      {packages.length === 0 && !runId && total === 0 && (
        <EmptyState message="No audit runs uploaded yet." />
      )}

      {/* Work package cards */}
      <div className="space-y-3">
        {packages.map((wp) => (
          <WorkPackageCard
            key={wp.package_id}
            summary={wp}
            repoId={repoId}
            runId={runId}
          />
        ))}
      </div>

      {/* Back link */}
      <div className="mt-6">
        <Link
          to={`/repositories/${repoId}${runQs}`}
          className="text-primary hover:underline text-sm"
        >
          ← Back to repository dashboard
        </Link>
      </div>
    </div>
  );
}
