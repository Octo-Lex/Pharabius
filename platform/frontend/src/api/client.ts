/** API client for Pharabius Platform backend. */

const BASE = "/api/v1";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

// --- Types ---

export interface Repository {
  id: string;
  name: string;
  slug: string;
  vcs_url: string;
  last_uploaded_at: string | null;
  latest_run: RunSummary | null;
}

export interface RunSummary {
  id: string;
  run_id: string;
  pharabius_version: string;
  run_timestamp: string;
  commit_sha: string;
  branch_name: string;
  analysis_mode: string;
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  readiness_status: string;
  gate_result: string;
  evidence_count: number;
  work_package_count: number;
  has_evidence_store: boolean;
  has_work_packages: boolean;
  warning_count: number;
  is_latest: boolean;
}

export interface EvidenceReference {
  evidence_id: string;
  status: "resolved" | "missing" | "legacy_no_evidence_store" | "stale" | "malformed_reference" | "unavailable";
  reason?: string;
  evidence?: EvidenceRecord;
}

export interface EvidenceRecord {
  evidence_id: string;
  source: string;
  type: string;
  category: string;
  summary: string;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  subject: string;
  object: string;
  confidence: string;
  collected_at: string | null;
  metadata: Record<string, unknown>;
}

export interface Finding {
  id: string;
  finding_id: string;
  category: string;
  issue_type: string;
  title: string;
  description: string;
  severity: string;
  confidence: string;
  risk_score: number;
  priority: string;
  locations: string[] | null;
  evidence_ids: string[] | null;
  evidence_references: EvidenceReference[];
}

export interface FindingsResponse {
  findings: Finding[];
  total: number;
  page: number;
  page_size: number;
}

export interface PortfolioData {
  total_repositories: number;
  total_findings: number;
  severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  repositories: Array<{
    id: string;
    name: string;
    latest_gate_result: string;
  }>;
}

export interface RiskRollup {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface UploadResult {
  bundle_id: string;
  repository_id: string;
  run_id: string | null;
  created_at: string | null;
  is_latest: boolean;
  content_hash: string;
  file_size_bytes: number;
  is_valid: boolean;
  validation: {
    is_valid: boolean;
    missing_required: string[];
    found_required: string[];
    found_optional: string[];
    extra_files: string[];
  };
  parse_errors: string[];
  parser_version: string;
  findings_count: number;
  evidence_count: number;
  work_package_count: number;
  evidence_warnings: Array<{ code: string; message: string }>;
  work_package_warnings: Array<{ code: string; message: string }>;
  warnings: string[];
}

// --- Work Package types ---

export interface WorkPackageSummary {
  package_id: string;
  title: string;
  status: string;
  estimated_effort: string;
  linked_finding_count: number;
  resolved_finding_count: number;
  missing_finding_count: number;
  declared_evidence_count: number;
}

export interface CompactFinding {
  finding_id: string;
  title: string;
  severity: string;
  confidence: string;
  category: string;
}

export interface LinkedFinding {
  debt_item_id: string;
  status: "resolved" | "missing" | "malformed_reference" | "unavailable";
  reason?: string;
  finding: CompactFinding | null;
  evidence_references: EvidenceReference[];
}

export interface WorkPackageDetail extends WorkPackageSummary {
  objective: string;
  current_risk: string;
  recommended_engineering_approach: string[];
  expected_affected_areas: string[];
  preconditions: string[];
  verification_recommendations: string[];
  risks_and_cautions: string[];
  definition_of_done: string[];
  expected_risk_reduction: string;
  suggested_owner_area: string;
  declared_evidence_ids: string[];
  linked_findings: LinkedFinding[];
}

// --- Review types ---

export type DecisionStatus =
  | "accepted"
  | "rejected"
  | "deferred"
  | "needs-investigation"
  | "duplicate"
  | "already-fixed"
  | "risk-accepted";

export interface ReviewDecision {
  id: string;
  repository_id: string;
  run_id: string | null;
  finding_id: string;
  status: DecisionStatus;
  previous_status: string;
  reviewer: string;
  rationale: string;
  ticket_url: string;
  owner_area: string;
  target_release: string;
  notes: string;
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
  deleted_by: string;
  delete_reason: string;
}

export interface ReviewSummary {
  total_decisions: number;
  status_counts: Record<DecisionStatus, number>;
}

export interface BulkReviewResult {
  created: number;
  updated: number;
  total: number;
  warnings: string[];
}

export interface AuditLogEntry {
  id: string;
  finding_id: string;
  status: string;
  previous_status: string;
  reviewer: string;
  created_at: string | null;
  updated_at: string | null;
  is_deleted: boolean;
  deleted_at?: string;
  deleted_by?: string;
  delete_reason?: string;
}

// --- API functions ---

export function listRepositories(): Promise<{ repositories: Repository[]; total: number }> {
  return fetchJSON(`${BASE}/repositories`);
}

export function getRepository(repoId: string): Promise<Repository> {
  return fetchJSON(`${BASE}/repositories/${repoId}`);
}

export function listFindings(
  repoId: string,
  params?: { severity?: string; category?: string; page?: number; runId?: string },
): Promise<FindingsResponse> {
  const sp = new URLSearchParams();
  if (params?.severity) sp.set("severity", params.severity);
  if (params?.category) sp.set("category", params.category);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.runId) sp.set("run_id", params.runId);
  const qs = sp.toString();
  return fetchJSON(`${BASE}/repositories/${repoId}/findings${qs ? `?${qs}` : ""}`);
}

export function getFinding(
  repoId: string,
  findingId: string,
  params?: { runId?: string; includeEvidence?: boolean },
): Promise<Finding> {
  const sp = new URLSearchParams();
  if (params?.runId) sp.set("run_id", params.runId);
  if (params?.includeEvidence) sp.set("include_evidence", "true");
  const qs = sp.toString();
  return fetchJSON(`${BASE}/repositories/${repoId}/findings/${findingId}${qs ? `?${qs}` : ""}`);
}

export function getPortfolio(): Promise<PortfolioData> {
  return fetchJSON(`${BASE}/portfolio`);
}

export function getRiskRollup(): Promise<RiskRollup> {
  return fetchJSON(`${BASE}/portfolio/risk-rollup`);
}

export async function uploadBundle(
  file: File,
  repositoryName: string,
  token: string,
  onProgress?: (pct: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/bundles`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.responseType = "json";

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as UploadResult);
      } else {
        reject(new Error(`Upload failed (${xhr.status}): ${JSON.stringify(xhr.response).slice(0, 200)}`));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));

    const form = new FormData();
    form.append("file", file);
    form.append("repository_name", repositoryName);
    xhr.send(form);
  });
}

// --- Review API ---

export async function listReviewDecisions(
  repoId: string,
  token?: string,
): Promise<{ decisions: ReviewDecision[]; total: number }> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetchJSON(`${BASE}/repositories/${repoId}/reviews`);
}

export function getReviewSummary(repoId: string): Promise<ReviewSummary> {
  return fetchJSON(`${BASE}/repositories/${repoId}/reviews/summary`);
}

export async function createReviewDecision(
  repoId: string,
  decision: {
    finding_id: string;
    status: DecisionStatus;
    reviewer?: string;
    rationale?: string;
    ticket_url?: string;
    owner_area?: string;
    target_release?: string;
    notes?: string;
  },
  token: string,
): Promise<ReviewDecision> {
  const res = await fetch(`${BASE}/repositories/${repoId}/reviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(decision),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

export function getAuditLog(
  repoId: string,
  limit = 50,
): Promise<{ entries: AuditLogEntry[]; total: number }> {
  return fetchJSON(`${BASE}/repositories/${repoId}/reviews/audit-log?limit=${limit}`);
}

// --- Work Package API ---

export function listWorkPackages(
  repoId: string,
  runId?: string,
): Promise<{ work_packages: WorkPackageSummary[]; total: number }> {
  const sp = new URLSearchParams();
  if (runId) sp.set("run_id", runId);
  const qs = sp.toString();
  return fetchJSON(`${BASE}/repositories/${repoId}/work-packages${qs ? `?${qs}` : ""}`);
}

export function getWorkPackageDetail(
  repoId: string,
  packageId: string,
  options?: { runId?: string; includeFindings?: boolean; includeEvidence?: boolean },
): Promise<WorkPackageDetail> {
  const sp = new URLSearchParams();
  if (options?.runId) sp.set("run_id", options.runId);
  if (options?.includeFindings) sp.set("include_findings", "true");
  if (options?.includeEvidence) sp.set("include_evidence", "true");
  const qs = sp.toString();
  return fetchJSON(`${BASE}/repositories/${repoId}/work-packages/${packageId}${qs ? `?${qs}` : ""}`);
}

// --- Run API ---

export function listRuns(repoId: string): Promise<{ runs: RunSummary[]; total: number }> {
  return fetchJSON(`${BASE}/repositories/${repoId}/runs`);
}

export function getRunDetail(repoId: string, runId: string): Promise<Record<string, unknown>> {
  return fetchJSON(`${BASE}/repositories/${repoId}/runs/${runId}`);
}

export function getLatestRun(repoId: string): Promise<{ run: RunSummary | null }> {
  return fetchJSON(`${BASE}/repositories/${repoId}/latest-run`);
}

// --- Run Comparison ---

export interface FindingDelta {
  finding_id: string;
  status: "added" | "removed" | "changed" | "unchanged";
  baseline: Record<string, unknown> | null;
  comparison: Record<string, unknown> | null;
  changed_fields: string[];
  traceability_change: {
    baseline_evidence_ids: number;
    comparison_evidence_ids: number;
    status: "improved" | "regressed" | "unchanged";
  } | null;
}

export interface WorkPackageDelta {
  package_id: string;
  status: "added" | "removed" | "changed" | "unchanged";
  baseline: Record<string, unknown> | null;
  comparison: Record<string, unknown> | null;
  changed_fields: string[];
  traceability_change: {
    baseline_resolved_links: number;
    comparison_resolved_links: number;
    baseline_missing_links: number;
    comparison_missing_links: number;
    status: "improved" | "regressed" | "unchanged";
  } | null;
}

export interface TraceabilityDelta {
  evidence: {
    status: "improved" | "regressed" | "unchanged" | "unavailable";
    baseline_unique_total: number;
    baseline_unique_resolved: number;
    baseline_unique_unresolved: number;
    comparison_unique_total: number;
    comparison_unique_resolved: number;
    comparison_unique_unresolved: number;
  };
  work_package_links: {
    status: "improved" | "regressed" | "unchanged" | "unavailable";
    baseline_total: number;
    baseline_resolved: number;
    baseline_missing: number;
    comparison_total: number;
    comparison_resolved: number;
    comparison_missing: number;
  };
}

export interface ComparisonSummary {
  findings: { added: number; removed: number; changed: number; unchanged: number };
  work_packages: { added: number; removed: number; changed: number; unchanged: number };
}

export interface RunComparisonResponse {
  baseline_run: { id: string; run_id: string; timestamp: string };
  comparison_run: { id: string; run_id: string; timestamp: string };
  summary: ComparisonSummary;
  findings_delta: FindingDelta[];
  work_packages_delta: WorkPackageDelta[];
  traceability_delta: TraceabilityDelta;
}

export function compareRuns(
  repoId: string,
  baselineRunId: string,
  comparisonRunId: string,
): Promise<RunComparisonResponse> {
  const params = new URLSearchParams({
    baseline_run_id: baselineRunId,
    comparison_run_id: comparisonRunId,
  });
  return fetchJSON(
    `${BASE}/repositories/${repoId}/runs/compare?${params}`,
  );
}
