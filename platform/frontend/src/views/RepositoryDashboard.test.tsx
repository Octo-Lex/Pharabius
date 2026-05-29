import { describe, it, expect, vi } from "vitest";
import { screen, render, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import {
  mockRepository,
  mockRun,
} from "../test/api-mocks";

const { mockGetRepo, mockListRuns, mockListWP, mockListFindings } = vi.hoisted(() => ({
  mockGetRepo: vi.fn(),
  mockListRuns: vi.fn(),
  mockListWP: vi.fn(),
  mockListFindings: vi.fn(),
}));

vi.mock("../api/client", () => ({
  getRepository: mockGetRepo,
  listRuns: mockListRuns,
  listWorkPackages: mockListWP,
  listFindings: mockListFindings,
  getFinding: vi.fn(),
}));

import RepositoryDashboard from "./RepositoryDashboard";
import FindingsTable from "./FindingsTable";
import WorkPackages from "./WorkPackages";

const repo = mockRepository();
const run1 = mockRun({ id: "run-1", is_latest: true });

function renderAtRoute(element: React.ReactElement, route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/repositories/:repoId" element={element} />
        <Route path="/repositories/:repoId/findings" element={element} />
        <Route path="/repositories/:repoId/work-packages" element={element} />
      </Routes>
    </MemoryRouter>
  );
}

describe("RepositoryDashboard", () => {
  it("renders selected run from URL", async () => {
    mockGetRepo.mockResolvedValue(repo);
    mockListRuns.mockResolvedValue({ runs: [run1], total: 1 });

    renderAtRoute(<RepositoryDashboard />, "/repositories/repo-001?run_id=run-1");

    await waitFor(() => {
      expect(screen.getByText(/RUN-20260529-120000/)).toBeInTheDocument();
    });
  });

  it("preserves run_id in Work Packages link", async () => {
    mockGetRepo.mockResolvedValue(repo);
    mockListRuns.mockResolvedValue({ runs: [run1], total: 1 });

    renderAtRoute(<RepositoryDashboard />, "/repositories/repo-001?run_id=run-1");

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /Work Packages/ });
      expect(link).toHaveAttribute(
        "href",
        "/repositories/repo-001/work-packages?run_id=run-1",
      );
    });
  });

  it("preserves run_id in Findings link", async () => {
    mockGetRepo.mockResolvedValue(repo);
    mockListRuns.mockResolvedValue({ runs: [run1], total: 1 });

    renderAtRoute(<RepositoryDashboard />, "/repositories/repo-001?run_id=run-1");

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /View Findings/ });
      expect(link).toHaveAttribute(
        "href",
        "/repositories/repo-001/findings?run_id=run-1",
      );
    });
  });
});

describe("WorkPackages run-context", () => {
  it("calls listWorkPackages with runId from URL", async () => {
    mockListWP.mockResolvedValue({ work_packages: [], total: 0 });

    render(
      <MemoryRouter initialEntries={["/repositories/repo-001/work-packages?run_id=run-1"]}>
        <Routes>
          <Route path="/repositories/:repoId/work-packages" element={<WorkPackages />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockListWP).toHaveBeenCalledWith("repo-001", "run-1");
    });
  });

  it("shows latest-run notice when no run_id provided", async () => {
    mockListWP.mockResolvedValue({ work_packages: [], total: 0 });

    render(
      <MemoryRouter initialEntries={["/repositories/repo-001/work-packages"]}>
        <Routes>
          <Route path="/repositories/:repoId/work-packages" element={<WorkPackages />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Viewing latest run/i)).toBeInTheDocument();
    });
  });
});

describe("FindingsTable run-context", () => {
  it("calls listFindings with runId from URL", async () => {
    mockListFindings.mockResolvedValue({
      findings: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(
      <MemoryRouter initialEntries={["/repositories/repo-001/findings?run_id=run-1"]}>
        <Routes>
          <Route path="/repositories/:repoId/findings" element={<FindingsTable />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockListFindings).toHaveBeenCalledWith(
        "repo-001",
        expect.objectContaining({ runId: "run-1" }),
      );
    });
  });
});
