import { describe, it, expect, beforeEach } from "vitest";
import { screen, render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EvidenceChip } from "./EvidenceChip";
import {
  mockEvidenceReference,
  mockEvidenceRecord,
} from "../test/api-mocks";

describe("EvidenceChip", () => {
  beforeEach(() => {
    // Clean DOM between tests
    document.body.innerHTML = "";
  });

  it("expands resolved reference and shows safe fields", async () => {
    const ref = mockEvidenceReference();
    render(<EvidenceChip reference={ref} />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));

    expect(screen.getByText(/Service token TTL exceeds 72h threshold/)).toBeInTheDocument();
    expect(screen.getByText(/token_config.yaml/)).toBeInTheDocument();
    expect(screen.getByText(/static-analysis/)).toBeInTheDocument();
    expect(screen.getByText(/observation \/ architecture/)).toBeInTheDocument();
    expect(screen.getByText(/High/)).toBeInTheDocument();
  });

  it("shows reason for missing evidence", async () => {
    const ref = mockEvidenceReference({
      status: "missing",
      reason: "Evidence record not found in this run.",
      evidence: undefined,
    });
    render(<EvidenceChip reference={ref} />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));

    expect(screen.getByText(/Evidence record not found in this run/)).toBeInTheDocument();
  });

  it("shows degraded state for legacy_no_evidence_store", () => {
    const ref = mockEvidenceReference({
      status: "legacy_no_evidence_store",
      reason: "This run does not include an evidence store.",
      evidence: undefined,
    });
    render(<EvidenceChip reference={ref} />);

    expect(screen.getByText(/legacy/)).toBeInTheDocument();
  });

  it("shows warning state for malformed_reference", () => {
    const ref = mockEvidenceReference({
      status: "malformed_reference",
      reason: "Evidence ID is empty or invalid.",
      evidence: undefined,
    });
    render(<EvidenceChip reference={ref} />);

    expect(screen.getByText(/malformed/)).toBeInTheDocument();
  });

  it("shows unavailable state", () => {
    const ref = mockEvidenceReference({
      status: "unavailable",
      reason: "Evidence lookup failed.",
      evidence: undefined,
    });
    render(<EvidenceChip reference={ref} />);

    expect(screen.getByText(/unavailable/)).toBeInTheDocument();
  });

  it("does not render raw_observation", async () => {
    const record = mockEvidenceRecord({
      // @ts-expect-error — testing that unknown fields don't leak
      raw_observation: "SENSITIVE DATA HERE",
    });
    const ref = mockEvidenceReference({ evidence: record });

    render(<EvidenceChip reference={ref} />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));

    expect(screen.queryByText(/SENSITIVE DATA HERE/)).not.toBeInTheDocument();
  });
});
