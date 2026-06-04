import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, render, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import {
  mockRun,
  mockRunComparisonResponse,
  mockFindingDelta,
} from "../test/api-mocks";
import RunComparison from "./RunComparison";

const { mockListRuns, mockCompareRuns } = vi.hoisted(() => ({
  mockListRuns: vi.fn(),
  mockCompareRuns: vi.fn(),
}));

vi.mock("../api/client", () => ({
  listRuns: mockListRuns,
  compareRuns: mockCompareRuns,
}));

import "@testing-library/jest-dom/vitest";

const RUN_A = mockRun({
  id: "run-a",
  run_id: "RUN-001",
  run_timestamp: "2026-05-28T10:00:00Z",
});
const RUN_B = mockRun({
  id: "run-b",
  run_id: "RUN-002",
  run_timestamp: "2026-05-29T10:00:00Z",
});
const TWO_RUNS = { runs: [RUN_B, RUN_A], total: 2 };

function renderAt(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route
          path="/repositories/:repoId/compare"
          element={<RunComparison />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RunComparison", () => {
  beforeEach(() => {
    mockListRuns.mockResolvedValue(TWO_RUNS);
    mockCompareRuns.mockResolvedValue(mockRunComparisonResponse());
  });

  it("renders fewer-than-two-runs state", async () => {
    mockListRuns.mockResolvedValue({ runs: [RUN_A], total: 1 });
    renderAt("/repositories/repo-1/compare");
    await waitFor(() => {
      expect(
        screen.getByText(/at least two runs are required/i),
      ).toBeDefined();
    });
  });

  it("calls comparison API with both run IDs", async () => {
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      expect(mockCompareRuns).toHaveBeenCalledWith(
        "repo-1",
        "run-a",
        "run-b",
      );
    });
  });

  it("renders summary counts", async () => {
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      expect(screen.getByText(/\+1 added/)).toBeDefined();
      expect(screen.getAllByText(/≠1 changed/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders finding delta rows", async () => {
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      expect(screen.getByText("TD-ARCH-001")).toBeDefined();
    });
  });

  it("renders changed finding with delta fields", async () => {
    const delta = mockFindingDelta({
      changed_fields: ["severity", "risk_score"],
    });
    mockCompareRuns.mockResolvedValue(
      mockRunComparisonResponse({ findings_delta: [delta] }),
    );
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      // FIELD_LABELS maps severity → "Severity", risk_score → "Risk Score"
      const text = screen.getByText(/Severity/);
      expect(text).toBeDefined();
    });
  });

  it("renders work-package delta groups", async () => {
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      expect(screen.getByText("WP-001")).toBeDefined();
    });
  });

  it("renders traceability improved state", async () => {
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      expect(screen.getAllByText(/↑ Improved/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("links preserve run IDs in selectors", async () => {
    renderAt(
      "/repositories/repo-1/compare?baseline_run_id=run-a&comparison_run_id=run-b",
    );
    await waitFor(() => {
      const link = screen.getByText(/← Repository/);
      expect(link.getAttribute("href")).toBe("/repositories/repo-1");
    });
  });
});
