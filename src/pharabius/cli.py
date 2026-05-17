from __future__ import annotations

from pathlib import Path
from typing import Annotated

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
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main() -> None:
    """
    Pharabius technical debt intelligence CLI.
    """


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
    """
    Collect normalized repository evidence.
    """
    repository_root = repository_root.resolve()

    evidence_store = write_evidence_store(repository_root)

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
) -> None:
    """
    Convert normalized evidence into deterministic technical debt findings.
    """
    if not no_ai:
        raise typer.BadParameter("AI analysis is not implemented yet. Use --no-ai.")

    resolved_root = (repository_root or Path.cwd()).resolve()

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


if __name__ == "__main__":
    app()
