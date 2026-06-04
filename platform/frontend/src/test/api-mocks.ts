import type {
  Repository,
  RunSummary,
  WorkPackageSummary,
  WorkPackageDetail,
  LinkedFinding,
  EvidenceReference,
  EvidenceRecord,
  UploadResult,
} from "../api/client";

// --- Base factories ---

export function mockRun(overrides: Partial<RunSummary> = {}): RunSummary {
  return {
    id: "run-001",
    run_id: "RUN-20260529-120000",
    pharabius_version: "2.9.0",
    run_timestamp: "2026-05-29T12:00:00Z",
    commit_sha: "abc1234",
    branch_name: "main",
    analysis_mode: "baseline",
    total_findings: 5,
    critical: 1,
    high: 2,
    medium: 1,
    low: 1,
    readiness_status: "review_required",
    gate_result: "fail",
    evidence_count: 3,
    work_package_count: 2,
    has_evidence_store: true,
    has_work_packages: true,
    warning_count: 0,
    is_latest: true,
    ...overrides,
  };
}

export function mockRepository(overrides: Partial<Repository> = {}): Repository {
  return {
    id: "repo-001",
    name: "test-repo",
    slug: "test-repo",
    vcs_url: "https://github.com/example/test-repo",
    last_uploaded_at: "2026-05-29T12:00:00Z",
    latest_run: null,
    ...overrides,
  };
}

export function mockWorkPackageSummary(
  overrides: Partial<WorkPackageSummary> = {},
): WorkPackageSummary {
  return {
    package_id: "WP-001",
    title: "Stabilize Authorization Boundary",
    status: "Ready for PET review",
    estimated_effort: "Medium",
    linked_finding_count: 3,
    resolved_finding_count: 2,
    missing_finding_count: 1,
    declared_evidence_count: 5,
    ...overrides,
  };
}

export function mockWorkPackageDetail(
  overrides: Partial<WorkPackageDetail> = {},
): WorkPackageDetail {
  return {
    ...mockWorkPackageSummary(),
    objective: "Reduce authorization boundary drift across service mesh.",
    current_risk: "High — stale service tokens may allow privilege escalation.",
    recommended_engineering_approach: [
      "Audit all service token TTLs",
      "Implement token rotation policy",
      "Add boundary validation middleware",
    ],
    expected_affected_areas: [
      "auth-service",
      "api-gateway",
      "token-rotation-cron",
    ],
    preconditions: ["Service mesh version >= 2.1"],
    verification_recommendations: [
      "Run boundary conformance test suite",
      "Verify token rotation log entries",
    ],
    risks_and_cautions: [
      "Token rotation may cause brief service disruption",
    ],
    definition_of_done: [
      "All service tokens rotate within 24h TTL",
      "Boundary test suite passes",
      "No stale tokens in production logs",
    ],
    expected_risk_reduction: "High",
    suggested_owner_area: "Platform Security",
    declared_evidence_ids: ["EV-001", "EV-002"],
    linked_findings: [],
    ...overrides,
  };
}

export function mockLinkedFinding(
  overrides: Partial<LinkedFinding> = {},
): LinkedFinding {
  return {
    debt_item_id: "TD-ARCH-001",
    status: "resolved",
    reason: undefined,
    finding: {
      finding_id: "TD-ARCH-001",
      title: "Authorization boundary drift",
      severity: "High",
      confidence: "Medium",
      category: "TD-ARCH",
    },
    evidence_references: [],
    ...overrides,
  };
}

export function mockEvidenceRecord(
  overrides: Partial<EvidenceRecord> = {},
): EvidenceRecord {
  return {
    evidence_id: "EV-001",
    source: "static-analysis",
    type: "observation",
    category: "architecture",
    summary: "Service token TTL exceeds 72h threshold",
    file_path: "src/auth/token_config.yaml",
    line_start: 14,
    line_end: 18,
    subject: "token_config",
    object: "ttl",
    confidence: "High",
    collected_at: "2026-05-29T12:00:00Z",
    metadata: {},
    ...overrides,
  };
}

export function mockEvidenceReference(
  overrides: Partial<EvidenceReference> = {},
): EvidenceReference {
  return {
    evidence_id: "EV-001",
    status: "resolved",
    reason: undefined,
    evidence: mockEvidenceRecord(),
    ...overrides,
  };
}

export function mockUploadResult(
  overrides: Partial<UploadResult> = {},
): UploadResult {
  return {
    bundle_id: "bundle-001",
    repository_id: "repo-001",
    run_id: "run-001",
    created_at: "2026-05-29T12:00:00Z",
    is_latest: true,
    content_hash: "sha256:abcdef1234567890",
    file_size_bytes: 4096,
    is_valid: true,
    validation: {
      is_valid: true,
      missing_required: [],
      found_required: ["debt_register.json"],
      found_optional: ["evidence_store.json"],
      extra_files: [],
    },
    parse_errors: [],
    parser_version: "2.9.0",
    findings_count: 5,
    evidence_count: 3,
    work_package_count: 2,
    evidence_warnings: [],
    work_package_warnings: [],
    warnings: [],
    ...overrides,
  };
}

// --- Run Comparison factories ---

export function mockFindingDelta(
  overrides: Partial<FindingDelta> = {},
): FindingDelta {
  return {
    finding_id: "TD-ARCH-001",
    status: "changed",
    baseline: { title: "Old", severity: "Medium" },
    comparison: { title: "New", severity: "High" },
    changed_fields: ["title", "severity"],
    traceability_change: {
      baseline_evidence_ids: 2,
      comparison_evidence_ids: 3,
      status: "improved",
    },
    ...overrides,
  };
}

export function mockWorkPackageDelta(
  overrides: Partial<WorkPackageDelta> = {},
): WorkPackageDelta {
  return {
    package_id: "WP-001",
    status: "changed",
    baseline: { title: "Old WP" },
    comparison: { title: "New WP" },
    changed_fields: ["title"],
    traceability_change: {
      baseline_resolved_links: 1,
      comparison_resolved_links: 2,
      baseline_missing_links: 1,
      comparison_missing_links: 0,
      status: "improved",
    },
    ...overrides,
  };
}

export function mockTraceabilityDelta(
  overrides: Partial<TraceabilityDelta> = {},
): TraceabilityDelta {
  return {
    evidence: {
      status: "improved",
      baseline_unique_total: 3,
      baseline_unique_resolved: 1,
      baseline_unique_unresolved: 2,
      comparison_unique_total: 3,
      comparison_unique_resolved: 3,
      comparison_unique_unresolved: 0,
    },
    work_package_links: {
      status: "improved",
      baseline_total: 3,
      baseline_resolved: 1,
      baseline_missing: 2,
      comparison_total: 3,
      comparison_resolved: 3,
      comparison_missing: 0,
    },
    ...overrides,
  };
}

export function mockRunComparisonResponse(
  overrides: Partial<RunComparisonResponse> = {},
): RunComparisonResponse {
  return {
    baseline_run: {
      id: "run-a",
      run_id: "RUN-001",
      timestamp: "2026-05-28T10:00:00Z",
    },
    comparison_run: {
      id: "run-b",
      run_id: "RUN-002",
      timestamp: "2026-05-29T10:00:00Z",
    },
    summary: {
      findings: { added: 1, removed: 0, changed: 1, unchanged: 0 },
      work_packages: { added: 0, removed: 0, changed: 1, unchanged: 0 },
    },
    findings_delta: [mockFindingDelta()],
    work_packages_delta: [mockWorkPackageDelta()],
    traceability_delta: mockTraceabilityDelta(),
    ...overrides,
  };
}
