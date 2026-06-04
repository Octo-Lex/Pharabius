import { useState } from "react";
import type { EvidenceReference } from "../api/client";

export function EvidenceChip({ reference }: { reference: EvidenceReference }) {
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
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded font-mono ${
            statusColor[reference.status] || "bg-gray-50"
          }`}
        >
          {reference.evidence_id}
        </span>
        <span
          className={`text-xs ${
            reference.status === "resolved" ? "text-green-600" : "text-gray-400"
          }`}
        >
          {statusLabel[reference.status] || reference.status}
        </span>
      </button>
      {expanded && reference.evidence && (
        <div className="mt-2 ml-1 space-y-1 text-xs border-t pt-2">
          {reference.evidence.summary && (
            <div>
              <span className="font-medium text-gray-600">Summary:</span>{" "}
              <span className="text-gray-800">{reference.evidence.summary}</span>
            </div>
          )}
          {reference.evidence.file_path && (
            <div>
              <span className="font-medium text-gray-600">Location:</span>{" "}
              <span className="font-mono text-muted">
                {reference.evidence.file_path}
                {reference.evidence.line_start
                  ? `:${reference.evidence.line_start}${
                      reference.evidence.line_end
                        ? `-${reference.evidence.line_end}`
                        : ""
                    }`
                  : ""}
              </span>
            </div>
          )}
          <div>
            <span className="font-medium text-gray-600">Source:</span>{" "}
            {reference.evidence.source}
          </div>
          <div>
            <span className="font-medium text-gray-600">Type:</span>{" "}
            {reference.evidence.type} / {reference.evidence.category}
          </div>
          <div>
            <span className="font-medium text-gray-600">Confidence:</span>{" "}
            {reference.evidence.confidence}
          </div>
        </div>
      )}
      {expanded && !reference.evidence && reference.reason && (
        <p className="mt-1 text-gray-400 italic">{reference.reason}</p>
      )}
    </div>
  );
}
