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
  severity: string;
  confidence: string;
  risk_score: number;
  priority: string;
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
