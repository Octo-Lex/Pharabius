"_timestamp": run.run_timestamp.isoformat() if run.run_timestamp else None,
        "total_findings": run.total_findings,
        "critical": run.critical,
        "high": run.high,
        "medium": run.medium,
        "low": run.low,
        "readiness_status": run.readiness_status,
        "gate_result": run.gate_result,
    }


@router.get("/api/v1/repositories/{repo_id}/findings/{finding_id}")
async def get_finding(
    repo_id: str,
    finding_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_evidence: bool = False,
) -> dict[str, object]:
    """Get a single finding by finding_id for a repository's latest run.

    ?include_evidence=true adds resolved evidence records.
    Evidence resolution always uses the finding's own run_id.
    """
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_id", "message": "Invalid repository ID"},
        ) from None

    # Get latest run for this repo
    run_result = await session.execute(
        select(Run)
        .where(Run.repository_id == repo_uuid)
        .order_by(Run.run_timestamp.desc())
        .limit(1)
    )
    latest_run = run_result.scalar_one_or_none()
    if latest_run is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "No runs found for repository"},
        )

    # Find by finding_id (not UUID)
    result = await session.execute(
        select(Finding).where(
            Finding.run_id == latest_run.id,
            Finding.finding_id == finding_id,
        )
    )
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "finding_not_found",
                "message": f"Finding {finding_id} not found.",
                "finding_id": finding_id,
            },
        )

    # Resolve evidence references (always using finding's run_id)
    evidence_references = await _resolve_evidence(
        session, repo_uuid, finding.run_id, finding.evidence_ids, include_evidence
    )

    return {
        "id": str(finding.id),
        "finding_id": finding.finding_id,
        "category": finding.category,
        "issue_type": finding.issue_type,
        "title": finding.title,
        "description": finding.description or "",
        "severity": finding.severity,
        "confidence": finding.confidence,
        "risk_score": finding.risk_score,
        "priority": finding.priority,
        "locations": finding.locations,
        "evidence_ids": finding.evidence_ids,
        "evidence_references": evidence_references,
    }


@router.get("/api/v1/repositories/{repo_id}/evidence/{evidence_id}")
async def get_evidence(
    repo_id: str,
    evidence_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    run_id: str | None = None,
) -> dict[str, object]:
    """Get a single evidence record by evidence_id.

    By default scopes to latest run. Optional ?run_id= scopes to specific run.
    """
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_id", "message": "Invalid repository ID"},
        ) from None

    # Determine run scope
    if run_id:
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_id", "message": "Invalid run ID"},
            ) from None
        scope_run_id = run_uuid
    else:
        # Default: latest run
        run_result = await session.execute(
            select(Run)
            .where(Run.repository_id == repo_uuid)
            .order_by(Run.run_timestamp.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()
        if latest_run is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "No runs found for repository"},
            )
        scope_run_id = latest_run.id

    result = await session.execute(
        select(EvidenceRecord).where(
            EvidenceRecord.repository_id == repo_uuid,
            EvidenceRecord.run_id == scope_run_id,
            EvidenceRecord.evidence_id == evidence_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "evidence_not_found",
                "message": "Evidence record not found.",
                "evidence_id": evidence_id,
            },
        )

    return _evidence_record_response(record)


async def _resolve_evidence(
    session: AsyncSession,
    repo_id: object,
    run_id: object,
    evidence_ids: list[str] | None,
    include_body: bool = False,
) -> list[dict[str, object]]:
    """Resolve evidence_ids into evidence reference objects.

    Always uses the finding's own run_id, not the repo's latest run.
    """
    if not evidence_ids:
        return []

    # Check if any evidence records exist for this run
    count_result = await session.execute(
        select(func.count())
        .select_from(EvidenceRecord)
        .where(
            EvidenceRecord.repository_id == repo_id,
            EvidenceRecord.run_id == run_id,
        )
    )
    total_evidence = count_result.scalar() or 0

    references: list[dict[str, object]] = []
    for eid in evidence_ids:
        if not eid or not isinstance(eid, str):
            references.append(
                {
                    "evidence_id": str(eid) if eid else "",
                    "status": "malformed_reference",
                    "reason": "Evidence ID is empty or not a valid string.",
                }
            )
            continue

        result = await session.execute(
            select(EvidenceRecord).where(
                EvidenceRecord.repository_id == repo_id,
                EvidenceRecord.run_id == run_id,
                EvidenceRecord.evidence_id == eid,
            )
        )
        record = result.scalar_one_or_none()

        if record is not None:
            ref: dict[str, object] = {
                "evidence_id": eid,
                "status": "resolved",
            }
            if include_body:
                ref["evidence"] = _evidence_record_response(record)
            references.append(ref)
        elif total_evidence > 0:
            references.append(
                {
                    "evidence_id": eid,
                    "status": "missing",
                    "reason": "Evidence ID referenced by finding but not found in this upload's evidence store.",
                }
            )
        else:
            references.append(
                {
                    "evidence_id": eid,
                    "status": "legacy_no_evidence_store",
                    "reason": "This upload does not include an evidence store.",
                }
            )

    return references


def _evidence_record_response(record: EvidenceRecord) -> dict[str, object]:
    """Convert an EvidenceRecord ORM object to an API response dict.

    Excludes raw_observation by default.
    Exposes evidence_metadata as 'metadata' in the response.
    """
    return {
        "evidence_id": record.evidence_id,
        "source": record.source,
        "type": record.type,
        "category": record.category,
        "summary": record.summary,
        "file_path": record.file_path or None,
        "line_start": record.line_start,
        "line_end": record.line_end,
        "subject": record.subject,
        "object": record.object,
        "confidence": record.confidence,
        "collected_at": record.collected_at or None,
        "metadata": record.evidence_metadata or {},
    }
