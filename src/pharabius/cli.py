from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from pharabius.core.analyzer import write_debt_register
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.mapper import write_analysis_units
from pharabius.core.planner import write_plan
from pharabius.core.profiler import write_repository_profile
from pharabius.core.reporter import write_reports
from pharabius.core.run_metadata import execute_run
from pharabius.core.scanner import write_evidence_store

app = typer.Typer(
    name="ai-debt",
    help="Pharabius technical debt intelligence CLI.",
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show installed version and exit."),
    ] = False,
) -> None:
    """Pharabius technical debt intelligence CLI."""
    if version:
        from importlib.metadata import version as get_version

        try:
            v = get_version("pharabius")
        except Exception:
            v = "unknown"
        console.print(f"Pharabius {v}")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def init(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to initialize.",
        ),
    ] = Path.cwd(),  # noqa: B008
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite existing .ai-debt files.",
        ),
    ] = False,
) -> None:
    """
    Create the .ai-debt workspace and default output contract.
    """
    repository_root = repository_root.resolve()

    created_or_updated = initialize_workspace(
        repository_root=repository_root,
        force=force,
    )

    console.print("[bold green]Initialized Pharabius workspace[/bold green]")
    console.print(f"Repository: {repository_root}")
    console.print(f"Workspace:  {repository_root / '.ai-debt'}")
    console.print(f"Created/updated entries: {len(created_or_updated)}")


@app.command()
def profile(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to profile.",
        ),
    ] = Path.cwd(),  # noqa: B008
) -> None:
    """
    Detect repository structure, stack, tooling, tests, docs, and risk-sensitive areas.
    """
    repository_root = repository_root.resolve()

    profile_result = write_repository_profile(repository_root)

    console.print("[bold green]Generated repository profile[/bold green]")
    console.print(f"Repository: {repository_root}")
    console.print(f"Output:     {repository_root / '.ai-debt' / 'project-profile.json'}")
    console.print(f"Languages:  {', '.join(profile_result.detected_languages) or 'None detected'}")
    console.print(f"Frameworks: {', '.join(profile_result.detected_frameworks) or 'None detected'}")
    console.print(f"Confidence: {profile_result.analysis_confidence}")


@app.command()
def scan(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to scan.",
        ),
    ] = Path.cwd(),  # noqa: B008
) -> None:
    """Collect normalized repository evidence."""
    from pharabius.core.config import effective_exclude_paths, load_config

    repository_root = repository_root.resolve()
    config = load_config(repository_root)
    extra_excludes = effective_exclude_paths(config)

    evidence_store = write_evidence_store(
        repository_root,
        extra_exclude_paths=extra_excludes or None,
        max_file_size_kb=config.analysis.max_file_size_kb,
    )

    console.print("[bold green]Generated evidence store[/bold green]")
    console.print(f"Repository: {repository_root}")
    console.print(f"Output:     {repository_root / '.ai-debt' / 'evidence.json'}")
    console.print(f"Evidence:   {len(evidence_store.evidence)} items")


@app.command()
def map_units(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to map analysis units for.",
        ),
    ] = None,
) -> None:
    """Map repository evidence into analysis units."""
    resolved_root = (repository_root or Path.cwd()).resolve()

    unit_store = write_analysis_units(resolved_root)

    console.print("[bold green]Generated analysis units[/bold green]")
    console.print(f"Repository: {resolved_root}")
    console.print(f"Output:     {resolved_root / '.ai-debt' / 'analysis-units.json'}")
    console.print(f"Units:      {len(unit_store.units)}")

    # Print type breakdown
    type_counts: dict[str, int] = {}
    for u in unit_store.units:
        type_counts[u.unit_type] = type_counts.get(u.unit_type, 0) + 1
    for ut in sorted(type_counts):
        console.print(f"  {ut:.<30s} {type_counts[ut]}")


def _set_scoring_override(root: Path, enabled: bool) -> None:
    """Write a temporary scoring override that analyzer will pick up via config."""
    import yaml

    config_path = root / ".ai-debt" / "config.yaml"
    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    rs = data.get("risk_scoring", {})
    rs["enhanced"] = enabled
    rs["use_architecture_centrality"] = enabled
    rs["use_change_frequency"] = enabled
    data["risk_scoring"] = rs
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _run_scoring_preview(root: Path) -> None:
    """Run enhanced scoring as a preview without mutating canonical artifacts."""
    import hashlib
    import json

    from pharabius.core.config import load_config
    from pharabius.core.scoring import (
        ScoringDeltaConfig,
        ScoringDeltaFactorDetail,
        ScoringDeltaReport,
        ScoringDeltaRow,
        enhance_risk_breakdown,
        recalculate_risk_score,
        render_scoring_delta_markdown,
    )

    config = load_config(root)
    rs = config.risk_scoring

    # Temporarily enable for preview
    use_centrality = rs.use_architecture_centrality or rs.enhanced
    use_frequency = rs.use_change_frequency or rs.enhanced

    if not use_centrality and not use_frequency:
        # Force enable both for preview
        use_centrality = True
        use_frequency = True

    debt_path = root / ".ai-debt" / "debt-register.json"
    if not debt_path.exists():
        console.print("[bold red]No debt-register.json found. Run analyze first.[/bold red]")
        raise typer.Exit(code=1)

    register_data = json.loads(debt_path.read_text(encoding="utf-8"))
    hash_before = hashlib.sha256(debt_path.read_bytes()).hexdigest()

    delta_rows: list[ScoringDeltaRow] = []
    delta_factors: list[ScoringDeltaFactorDetail] = []
    warnings: list[str] = []
    changes_json: list[dict[str, Any]] = []
    total_findings = len(register_data.get("findings", []))

    for finding in register_data.get("findings", []):
        fid = finding["id"]
        old_score = finding["risk_score"]
        old_priority = finding["priority"]
        locations = finding.get("locations", [])

        enhanced = enhance_risk_breakdown(
            root,
            locations,
            use_centrality=use_centrality,
            use_frequency=use_frequency,
            max_git_commits=rs.max_git_commits,
            git_timeout=rs.git_timeout_seconds,
        )

        new_score = recalculate_risk_score(
            {
                "technical_severity": 1,
                "architecture_centrality": 1,
                "blast_radius": 1,
                "change_frequency": 1,
                "test_gap": 0,
                "security_exposure": 0,
                "compliance_exposure": 0,
                "dependency_risk": 0,
                "operational_exposure": 0,
                "business_critical_proxy": 1,
                "remediation_simplicity": -1,
                "confidence_modifier": 0,
            },
            enhanced,
        )

        # Determine new priority (use existing band logic)
        from pharabius.core.analyzer import _priority_for_score

        new_priority = _priority_for_score(new_score)

        # Track factor changes
        changed_factor_names: list[str] = []
        for factor_key in ("architecture_centrality", "change_frequency"):
            fdata = enhanced[factor_key]
            default_level = "Low"
            default_value = 1
            if fdata["level"] != default_level or fdata["value"] != default_value:
                changed_factor_names.append(factor_key)
                delta_factors.append(
                    ScoringDeltaFactorDetail(
                        finding_id=fid,
                        factor=factor_key,
                        before_level=default_level,
                        before_value=default_value,
                        after_level=fdata["level"],
                        after_value=fdata["value"],
                        source=fdata["source"],
                        reason=fdata["reason"],
                    )
                )
            if "fallback" in fdata.get("reason", "").lower():
                warnings.append(f"{fid}: {factor_key} — {fdata['reason']}")

        if new_score != old_score:
            delta_rows.append(
                ScoringDeltaRow(
                    finding_id=fid,
                    title=finding.get("title", ""),
                    category=finding.get("category", ""),
                    before_score=old_score,
                    after_score=new_score,
                    before_priority=old_priority,
                    after_priority=new_priority,
                    changed_factors=changed_factor_names,
                )
            )
            changes_json.append(
                {
                    "finding_id": fid,
                    "old_score": old_score,
                    "new_score": new_score,
                    "architecture_centrality": enhanced["architecture_centrality"],
                    "change_frequency": enhanced["change_frequency"],
                }
            )

    # Verify no mutation
    hash_after = hashlib.sha256(debt_path.read_bytes()).hexdigest()
    assert hash_before == hash_after, "Canonical artifact mutated during preview!"

    console.print("[bold green]Scoring Preview[/bold green]")
    console.print(f"Repository: {root}")
    console.print(f"Centrality: {'enabled' if use_centrality else 'disabled'}")
    console.print(f"Frequency:  {'enabled' if use_frequency else 'disabled'}")
    console.print(f"Total findings: {total_findings}")
    console.print(f"Scores would change: {len(delta_rows)}")
    if delta_rows:
        for c in changes_json:
            console.print(
                f"  {c['finding_id']}: {c['old_score']} -> {c['new_score']} "
                f"(centrality={c['architecture_centrality']['level']}, "
                f"frequency={c['change_frequency']['level']})"
            )
    else:
        console.print("  No score changes.")

    # Write JSON preview sidecar
    preview_path = root / ".ai-debt" / "reports" / "scoring-preview.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        json.dumps({"changes": changes_json}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Write Markdown delta report
    delta_report = ScoringDeltaReport(
        config=ScoringDeltaConfig(
            enhanced=use_centrality or use_frequency,
            use_centrality=use_centrality,
            use_frequency=use_frequency,
            git_cap=rs.max_git_commits,
            path_cap=rs.max_git_paths,
            git_timeout=rs.git_timeout_seconds,
            graph_timeout=rs.graph_timeout_seconds,
        ),
        rows=delta_rows,
        factor_details=delta_factors,
        warnings=warnings,
        total_findings=total_findings,
    )
    md_path = root / ".ai-debt" / "reports" / "scoring-delta.md"
    md_path.write_text(render_scoring_delta_markdown(delta_report), encoding="utf-8")

    console.print(f"Preview: {preview_path}")
    console.print(f"Delta:   {md_path}")


@app.command()
def analyze(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to analyze.",
        ),
    ] = None,
    no_ai: Annotated[
        bool,
        typer.Option(
            "--no-ai/--ai",
            help="Run deterministic analysis only. AI mode is not implemented yet.",
        ),
    ] = True,
    enhanced_scoring: Annotated[
        bool | None,
        typer.Option(
            "--enhanced-scoring/--no-enhanced-scoring",
            help="Override config enhanced scoring setting.",
        ),
    ] = None,
    scoring_preview: Annotated[
        bool,
        typer.Option(
            "--scoring-preview",
            help="Show projected scoring changes without mutating canonical artifacts.",
        ),
    ] = False,
) -> None:
    """
    Convert normalized evidence into deterministic technical debt findings.
    """
    if not no_ai:
        raise typer.BadParameter("AI analysis is not implemented yet. Use --no-ai.")

    resolved_root = (repository_root or Path.cwd()).resolve()

    # Apply CLI override for enhanced scoring
    if enhanced_scoring is not None:
        _set_scoring_override(resolved_root, enhanced_scoring)

    if scoring_preview:
        _run_scoring_preview(resolved_root)
        return

    register = write_debt_register(resolved_root)

    console.print("[bold green]Generated debt register[/bold green]")
    console.print(f"Repository: {resolved_root}")
    console.print(f"JSON:       {resolved_root / '.ai-debt' / 'debt-register.json'}")
    console.print(f"Markdown:   {resolved_root / '.ai-debt' / 'debt-register.md'}")
    console.print(f"Findings:   {register.summary.total_findings}")


@app.command()
def report(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to generate reports for.",
        ),
    ] = None,
) -> None:
    """
    Generate deterministic Markdown reports from profile, evidence, and findings.
    """
    resolved_root = (repository_root or Path.cwd()).resolve()

    result = write_reports(resolved_root)

    console.print("[bold green]Generated reports[/bold green]")
    console.print(f"Repository: {resolved_root}")

    for path in result.files_written:
        console.print(f"Wrote:      {path}")


@app.command()
def plan(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to generate a remediation plan for.",
        ),
    ] = None,
    top: Annotated[
        int,
        typer.Option(
            "--top",
            help="Maximum number of top findings to consider.",
            min=1,
        ),
    ] = 10,
    max_work_packages: Annotated[
        int,
        typer.Option(
            "--max-work-packages",
            help="Maximum number of work packages to generate.",
            min=0,
        ),
    ] = 10,
) -> None:
    """
    Generate remediation roadmap, work packages, and handoff summary.
    """
    resolved_root = (repository_root or Path.cwd()).resolve()

    result = write_plan(
        resolved_root,
        top=top,
        max_work_packages=max_work_packages,
    )

    console.print("[bold green]Generated remediation plan[/bold green]")
    console.print(f"Repository: {resolved_root}")
    console.print(f"Roadmap:    {result.remediation_roadmap_path}")
    console.print(f"Handoff:    {result.handoff_summary_path}")
    console.print(f"Packages:   {len(result.work_package_paths)}")

    for path in result.work_package_paths:
        console.print(f"Wrote:      {path}")


@app.command()
def verify(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to verify findings against current evidence.",
        ),
    ] = None,
) -> None:
    """
    Verify existing findings against current repository evidence.
    """
    from pharabius.core.verifier import write_verification_report

    resolved_root = (repository_root or Path.cwd()).resolve()

    try:
        report = write_verification_report(resolved_root)
    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[bold green]Generated verification report[/bold green]")
    console.print(f"Repository: {resolved_root}")
    console.print(f"Findings checked: {report.total_findings_checked}")
    console.print(f"  Still detected:     {report.still_detected_count}")
    console.print(f"  Likely remediated:  {report.likely_remediated_count}")
    console.print(f"  Evidence missing:   {report.evidence_missing_count}")
    console.print(f"  Partially supported: {report.partially_supported_count}")
    console.print(f"  Stale:              {report.stale_count}")
    console.print(f"  Uncertain:          {report.uncertain_count}")
    if report.work_package_results:
        console.print(
            f"Work packages: {report.work_packages_valid} valid, "
            f"{report.work_packages_stale} stale, "
            f"{report.work_packages_orphaned} orphaned"
        )


@app.command()
def status(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to show workspace status for.",
        ),
    ] = None,
) -> None:
    """
    Show current workspace status. Read-only.
    """
    from pharabius.core.status_reader import read_status

    resolved_root = (repository_root or Path.cwd()).resolve()
    console.print(read_status(resolved_root))


@app.command()
def graph(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to build architecture graph for.",
        ),
    ] = None,
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            "-s",
            help="Graph scope: package, analysis_unit, or both.",
        ),
    ] = "both",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path for architecture-graph.json.",
        ),
    ] = None,
    policy: Annotated[
        Path | None,
        typer.Option(
            "--policy",
            help="Path to architecture-policy.yaml.",
        ),
    ] = None,
) -> None:
    """
    Build import dependency graph from existing evidence.
    """
    from pharabius.core.grapher import build_graph

    if scope not in ("package", "analysis_unit", "both"):
        console.print(
            f"[bold red]Error:[/bold red] Invalid scope: {scope}. "
            "Use package, analysis_unit, or both."
        )
        raise typer.Exit(code=1)

    resolved_root = (repository_root or Path.cwd()).resolve()

    try:
        result = build_graph(
            resolved_root,
            scope=scope,
            policy_path=policy,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    graph = result.graph

    # Determine output path
    if output is not None:
        out_path = Path(output).resolve()
    else:
        out_path = resolved_root / ".ai-debt" / "architecture-graph.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write graph
    out_path.write_text(
        graph.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    # Print summary
    console.print("[bold green]Graph built[/bold green]")
    console.print(
        f"Nodes: {len(graph.nodes)}, "
        f"Edges: {len(graph.edges)}, "
        f"Cycles: {len(graph.cycles)}, "
        f"Violations: {len(graph.boundary_violations)}"
    )

    # Nodes by type
    type_counts: dict[str, int] = {}
    for n in graph.nodes:
        type_counts[n.node_type] = type_counts.get(n.node_type, 0) + 1
    if type_counts:
        console.print("\nNodes by type:")
        for t, c in sorted(type_counts.items()):
            console.print(f"  {t}: {c}")

    # Cycles
    if graph.cycles:
        console.print("\nCycles:")
        for cycle in graph.cycles:
            console.print(f"  {cycle.cycle_id}: {cycle.description}")

    # Top coupling
    sorted_metrics = sorted(
        graph.coupling_metrics,
        key=lambda m: m.fan_in + m.fan_out,
        reverse=True,
    )
    top = sorted_metrics[:3]
    if top:
        console.print("\nHigh-coupling nodes (top 3):")
        node_name_map = {n.node_id: n.name for n in graph.nodes}
        for m in top:
            name = node_name_map.get(m.node_id, m.node_id)
            console.print(
                f"  {name}: fan_in={m.fan_in}, fan_out={m.fan_out}, instability={m.instability}"
            )

    # Limitations
    if graph.limitations:
        console.print(f"\nLimitations: {len(graph.limitations)}")
        for lim in graph.limitations:
            console.print(f"  - {lim}")

    console.print(f"\nWritten: {out_path}")


@app.command()
def export(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to export findings from.",
        ),
    ] = None,
    export_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Export format: sarif, csv, jsonl, or all.",
        ),
    ] = "all",
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Output directory for export files.",
        ),
    ] = None,
) -> None:
    """
    Export findings to SARIF, CSV, or JSONL format.
    """
    from pharabius.core.exporter import export_findings

    resolved_root = (repository_root or Path.cwd()).resolve()

    formats = ["sarif", "csv", "jsonl"] if export_format == "all" else [export_format]
    for fmt in formats:
        if fmt not in ("sarif", "csv", "jsonl"):
            console.print(f"[bold red]Error:[/bold red] Unknown format: {fmt}")
            raise typer.Exit(code=1)

    try:
        result = export_findings(
            resolved_root,
            formats=formats,
            output_dir=output_dir,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[bold green]Export complete[/bold green]")
    console.print(f"Findings: {result.finding_count}")
    for f in result.files_written:
        console.print(f"  Written: {f}")
    for w in result.warnings:
        console.print(f"  [dim]Warning: {w}[/dim]")


@app.command()
def enrich(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to enrich.",
        ),
    ] = None,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            help="AI provider: disabled, mock, or openai-compatible.",
        ),
    ] = "disabled",
    max_findings: Annotated[
        int,
        typer.Option(
            "--max-findings",
            help="Maximum findings to enrich.",
            min=1,
        ),
    ] = 10,
    finding_id: Annotated[
        str | None,
        typer.Option(
            "--finding-id",
            help="Enrich a single finding by ID.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Assemble context and validate without writing files.",
        ),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Reject entire batch if any enrichment fails validation.",
        ),
    ] = False,
    context_preview: Annotated[
        bool,
        typer.Option(
            "--context-preview",
            help="Preview bounded context without calling any provider or writing files.",
        ),
    ] = False,
    allow_external: Annotated[
        bool,
        typer.Option(
            "--allow-external-provider",
            help="Consent to send repository evidence to an external AI provider.",
        ),
    ] = False,
    model_override: Annotated[
        str,
        typer.Option(
            "--model",
            help="Provider model name (required for openai-compatible if env var not set).",
        ),
    ] = "",
    timeout_seconds: Annotated[
        int,
        typer.Option(
            "--timeout-seconds",
            help="Provider call timeout in seconds.",
            min=1,
        ),
    ] = 30,
) -> None:
    """Enrich findings with AI-generated explanations and rationale."""
    from pharabius.ai.enricher import enrich_findings, format_context_preview, preview_context

    resolved_root = (repository_root or Path.cwd()).resolve()

    # Prerequisite checks
    debt_register = resolved_root / ".ai-debt" / "debt-register.json"
    evidence_file = resolved_root / ".ai-debt" / "evidence.json"

    if not debt_register.exists():
        console.print(
            "[bold red]Error:[/bold red] "
            "debt-register.json not found. Run 'ai-debt analyze --no-ai' first."
        )
        raise typer.Exit(code=1)

    if not evidence_file.exists():
        console.print(
            "[bold red]Error:[/bold red] evidence.json not found. Run 'ai-debt scan' first."
        )
        raise typer.Exit(code=1)

    # Context preview mode — skip provider validation and enrichment
    if context_preview:
        # Validate finding ID if specified
        if finding_id is not None:
            import json as _json

            try:
                register_data = _json.loads(debt_register.read_text(encoding="utf-8"))
            except (OSError, _json.JSONDecodeError):
                register_data = {}
            known_ids = {f.get("id", "") for f in register_data.get("findings", [])}
            if finding_id not in known_ids:
                console.print(
                    f"[bold red]Error:[/bold red] "
                    f"Finding ID '{finding_id}' was not found in debt-register.json."
                )
                raise typer.Exit(code=1)

        preview = preview_context(
            resolved_root,
            max_findings=max_findings,
            finding_id=finding_id,
        )
        console.print(format_context_preview(preview))
        return

    # Provider validation and consent gate
    known_providers = {"disabled", "mock", "openai-compatible"}
    if provider not in known_providers:
        console.print(
            f"[bold red]Error:[/bold red] "
            f"Provider '{provider}' is not available. "
            f"Available providers: {', '.join(sorted(known_providers))}."
        )
        raise typer.Exit(code=1)

    # External provider consent — must happen before provider import/init
    external_providers = {"openai-compatible"}
    if provider in external_providers and not allow_external:
        console.print(
            f"Provider '{provider}' may send repository evidence "
            "to an external AI service.\n"
            "  1. Review:   ai-debt enrich --provider openai-compatible "
            "--context-preview -r <repo>\n"
            "  2. Approve:  ai-debt enrich --provider openai-compatible "
            "--allow-external-provider -r <repo>\n"
            "\n"
            "No data was sent. No files were written."
        )
        raise typer.Exit(code=1)

    # Validate finding ID if specified
    if finding_id is not None:
        import json as _json

        try:
            register_data = _json.loads(debt_register.read_text(encoding="utf-8"))
        except (OSError, _json.JSONDecodeError):
            register_data = {}
        known_ids = {f.get("id", "") for f in register_data.get("findings", [])}
        if finding_id not in known_ids:
            console.print(
                f"[bold red]Error:[/bold red] "
                f"Finding ID '{finding_id}' was not found in debt-register.json."
            )
            raise typer.Exit(code=1)

    try:
        report = enrich_findings(
            resolved_root,
            provider_name=provider,
            max_findings=max_findings,
            finding_id=finding_id,
            dry_run=dry_run,
            strict=strict,
            model=model_override,
        )
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except ImportError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    # Handle disabled provider
    if provider == "disabled":
        for rej in report.rejections:
            console.print(f"[dim]{rej.reason}[/dim]")
        return

    # Handle empty register
    if not report.enrichments and not report.rejections:
        console.print("No findings to enrich. The debt register is empty.")
        return

    console.print("[bold green]AI enrichment complete[/bold green]")
    console.print(f"Provider:   {report.provider}")
    console.print(f"Enriched:   {len(report.enrichments)} finding(s)")
    console.print(f"Rejected:   {len(report.rejections)} output(s)")

    if not dry_run:
        ai_dir = resolved_root / ".ai-debt" / "ai"
        console.print(f"Output:     {ai_dir}")

    for rej in report.rejections:
        fid = rej.finding_id or "unknown"
        console.print(f"  [dim]Rejected {fid}: {rej.reason}[/dim]")


@app.command()
def ai_status(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to check AI sidecar status for.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output machine-readable JSON.",
        ),
    ] = False,
) -> None:
    """Show AI sidecar enrichment status. Read-only."""
    import json as _json

    from pharabius.ai.status_reader import read_ai_status

    resolved_root = (repository_root or Path.cwd()).resolve()

    status, exit_code = read_ai_status(resolved_root)

    if exit_code != 0:
        console.print(f"[bold red]Error:[/bold red] {status.error_message}")
        raise typer.Exit(code=exit_code)

    if not status.sidecar_present:
        console.print(status.error_message)
        return

    if json_output:
        console.print(_json.dumps(status.to_dict(), indent=2))
    else:
        console.print(status.to_human())


@app.command()
def run(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root to run the full deterministic pipeline on.",
        ),
    ] = None,
) -> None:
    """
    Run the full deterministic v1 pipeline and write run metadata.
    """
    resolved_root = (repository_root or Path.cwd()).resolve()

    metadata = execute_run(resolved_root)

    console.print("[bold green]Completed deterministic pipeline run[/bold green]")
    console.print(f"Repository: {resolved_root}")
    console.print(f"Run ID:     {metadata.run_id}")
    console.print(f"Evidence:   {metadata.summary.evidence_count} items")
    console.print(f"Findings:   {metadata.summary.finding_count}")
    console.print(f"Packages:   {metadata.summary.work_package_count}")
    console.print(
        f"Metadata:   {resolved_root / '.ai-debt' / 'runs' / (metadata.run_id + '.json')}"
    )


@app.command()
def review(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root.",
        ),
    ] = None,
    init: Annotated[
        bool,
        typer.Option(
            "--init",
            help="Initialize an empty review decision sidecar.",
        ),
    ] = False,
    show_status: Annotated[
        bool,
        typer.Option(
            "--status",
            help="Show review decision summary. Read-only.",
        ),
    ] = False,
    do_validate: Annotated[
        bool,
        typer.Option(
            "--validate",
            help="Validate review decisions against debt-register.",
        ),
    ] = False,
) -> None:
    """
    Manage non-canonical review decisions for findings.

    Review decisions are Product Engineering Team workflow state.
    They never modify canonical artifacts or affect finding generation.
    """
    from pharabius.core.review import (
        format_summary_text,
        init_review_sidecar,
        summarize_decisions,
        validate_decisions,
    )

    resolved_root = (repository_root or Path.cwd()).resolve()

    # Default to status if no mode specified
    modes = [init, show_status, do_validate]
    if not any(modes):
        show_status = True

    if init:
        try:
            path = init_review_sidecar(resolved_root)
            console.print("[bold green]Initialized review sidecar[/bold green]")
            console.print(f"Repository: {resolved_root}")
            console.print(f"Sidecar:    {path}")
        except FileExistsError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    if show_status:
        summary = summarize_decisions(resolved_root)
        text = format_summary_text(summary)
        console.print(text)

    if do_validate:
        result = validate_decisions(resolved_root)
        if not result.valid:
            console.print("[bold red]Validation failed[/bold red]")
            for notice in result.notices:
                if notice.level == "error":
                    console.print(f"  Error: {notice.message}")
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]Validation passed[/bold green]")
            console.print(f"Decisions: {result.total_decisions}")
            if result.unknown_finding_ids:
                console.print(f"Unknown findings: {', '.join(result.unknown_finding_ids)}")
            if result.duplicate_finding_ids:
                console.print(f"Duplicates: {', '.join(result.duplicate_finding_ids)}")
            if result.stale_finding_ids:
                console.print(f"Stale: {', '.join(result.stale_finding_ids)}")
            if result.undecided_finding_ids:
                console.print(f"Undecided: {len(result.undecided_finding_ids)}")
            for notice in result.notices:
                console.print(f"  {notice.level.title()}: {notice.message}")


@app.command("tickets")
def tickets_command(
    repository_root: Annotated[
        Path | None,
        typer.Option(
            "--repository-root",
            "-r",
            help="Repository root directory.",
        ),
    ] = None,
    include_deferred: Annotated[
        bool,
        typer.Option(
            "--include-deferred",
            help="Include deferred-only work packages in ticket drafts.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite existing generated ticket draft artifacts.",
        ),
    ] = False,
) -> None:
    """Generate repository-local ticket drafts from work packages."""
    from pharabius.core.tickets import (
        generate_ticket_draft_index,
        generate_ticket_markdown_drafts,
        write_ticket_draft_index,
        write_ticket_draft_summary,
    )

    resolved_root = repository_root or Path.cwd()
    workspace = resolved_root / ".ai-debt"

    if not workspace.exists():
        console.print("[bold red]No .ai-debt workspace found. Run `ai-debt init` first.[/bold red]")
        raise typer.Exit(code=1)

    wp_dir = workspace / "work-packages"
    if not wp_dir.exists() or not list(wp_dir.glob("*.md")):
        console.print(
            "[bold red]No work packages found. "
            "Run `ai-debt plan` before generating ticket drafts.[/bold red]"
        )
        raise typer.Exit(code=1)

    output_dir = workspace / "ticket-drafts"

    # Check existing output
    if not force and output_dir.exists() and list(output_dir.glob("TICKET-*.md")):
        console.print(
            "Ticket draft output already exists. "
            "Re-run with --force to overwrite generated draft artifacts."
        )
        raise typer.Exit(code=1)

    drafts, validation_issues = generate_ticket_markdown_drafts(
        workspace,
        output_dir=output_dir,
        include_deferred=include_deferred,
    )
    index = generate_ticket_draft_index(workspace, drafts, validation_issues)
    json_path = write_ticket_draft_index(index, output_dir)
    summary_path = write_ticket_draft_summary(index, workspace / "reports")

    included = sum(1 for d in drafts if d.status == "draft")
    excluded = sum(1 for d in drafts if d.status == "excluded")

    console.print("[bold green]Ticket drafts generated.[/bold green]")
    console.print(f"  Markdown drafts: {included}")
    console.print(f"  JSON index: {json_path}")
    console.print(f"  Summary report: {summary_path}")
    if excluded:
        console.print(f"  Excluded by review: {excluded}")
    console.print("  External tickets created: 0")


if __name__ == "__main__":
    app()
