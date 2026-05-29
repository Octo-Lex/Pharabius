import { describe, it, expect, vi } from "vitest";
import { screen, render, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import {
  mockWorkPackageSummary,
  mockWorkPackageDetail,
  mockLinkedFinding,
} from "../test/api-mocks";

const { mockListWP, mockGetDetail } = vi.hoisted(() => ({
  mockListWP: vi.fn(),
  mockGetDetail: vi.fn(),
}));

vi.mock("../api/client", () => ({
  listWorkPackages: mockListWP,
  getWorkPackageDetail: mockGetDetail,
}));

import WorkPackages from "./WorkPackages";

function renderWP(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/repositories/:repoId/work-packages" element={<WorkPackages />} />
      </Routes>
    </MemoryRouter>
  );
}

function findWPCardButton() {
  return screen.getAllByRole("button").find(
    (b) => b.textContent?.includes("WP-001"),
  )!;
}

const wpSummary = mockWorkPackageSummary();

async function expandCard(detailOverrides = {}) {
  const detail = mockWorkPackageDetail(detailOverrides);
  mockListWP.mockResolvedValue({ work_packages: [wpSummary], total: 1 });
  mockGetDetail.mockResolvedValue(detail);

  renderWP("/repositories/repo-001/work-packages?run_id=run-1");

  // Wait for card to appear
  await waitFor(() => {
    expect(screen.getByText(/Stabilize Authorization Boundary/)).toBeInTheDocument();
  });

  // Click to expand
  fireEvent.click(findWPCardButton());
}

describe("WorkPackages view states", () => {
  it("renders empty state", async () => {
    mockListWP.mockResolvedValue({ work_packages: [], total: 0 });
    renderWP("/repositories/repo-001/work-packages?run_id=run-1");
    await waitFor(() => {
      expect(screen.getByText(/No work packages included in this run/i)).toBeInTheDocument();
    });
  });

  it("renders collapsed work-package card", async () => {
    mockListWP.mockResolvedValue({ work_packages: [wpSummary], total: 1 });
    renderWP("/repositories/repo-001/work-packages?run_id=run-1");
    await waitFor(() => {
      expect(screen.getByText(/Stabilize Authorization Boundary/)).toBeInTheDocument();
    });
  });

  it("lazy-fetches detail on expand", async () => {
    mockGetDetail.mockResolvedValue(mockWorkPackageDetail({ linked_findings: [] }));
    await expandCard();

    await waitFor(() => {
      expect(mockGetDetail).toHaveBeenCalledWith(
        "repo-001", "WP-001",
        expect.objectContaining({ runId: "run-1", includeFindings: true, includeEvidence: true }),
      );
    });
  });

  it("renders objective and current risk in expanded detail", async () => {
    await expandCard({ linked_findings: [] });
    await waitFor(() => {
      expect(screen.getByText(/Reduce authorization boundary drift/)).toBeInTheDocument();
      expect(screen.getByText(/stale service tokens/)).toBeInTheDocument();
    });
  });

  it("renders resolved linked finding", async () => {
    await expandCard({
      linked_findings: [mockLinkedFinding({ status: "resolved" })],
    });
    await waitFor(() => {
      expect(screen.getByText(/TD-ARCH-001/)).toBeInTheDocument();
    });
  });

  it("renders missing linked finding warning", async () => {
    await expandCard({
      linked_findings: [mockLinkedFinding({
        status: "missing", reason: "Finding not found in this run.",
        finding: null, debt_item_id: "TD-ARCH-999",
      })],
    });
    await waitFor(() => {
      expect(screen.getByText(/TD-ARCH-999/)).toBeInTheDocument();
      expect(screen.getByText(/Missing linked finding/)).toBeInTheDocument();
    });
  });

  it("renders malformed linked finding warning", async () => {
    await expandCard({
      linked_findings: [mockLinkedFinding({
        status: "malformed_reference", reason: "Empty debt_item_id",
        finding: null, debt_item_id: "",
      })],
    });
    await waitFor(() => {
      expect(screen.getByText(/Malformed linked finding reference/)).toBeInTheDocument();
      expect(screen.getByText(/Empty debt_item_id/)).toBeInTheDocument();
    });
  });
});
