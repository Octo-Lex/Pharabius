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
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  readiness_status: string;
  gate_result: string;
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
  locations: string[];
  evidence_ids: string[];
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
  params?: { severity?: string; category?: string; page?: number },
): Promise<FindingsResponse> {
  const sp = new URLSearchParams();
  if (params?.severity) sp.set("severity", params.severity);
  if (params?.category) sp.set("category", params.category);
  if (params?.page) sp.set("page", String(params.page));
  const qs = sp.toString();
  return fetchJSON(`${BASE}/repositories/${repoId}/findings${qs ? `?${qs}` : ""}`);
}

export function getFinding(
  repoId: string,
  findingId: string,
): Promise<Finding> {
  return fetchJSON(`${BASE}/repositories/${repoId}/findings/${findingId}`);
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
