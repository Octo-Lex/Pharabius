from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class RepositoryProfile(BaseModel):
    schema_version: str = "1.0"
    project_name: str = ""
    repository_root: str = ""

    detected_languages: list[str] = Field(default_factory=list)
    detected_frameworks: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)

    entry_points: list[str] = Field(default_factory=list)
    deployment_files: list[str] = Field(default_factory=list)
    infrastructure_files: list[str] = Field(default_factory=list)
    documentation_files: list[str] = Field(default_factory=list)
    test_directories: list[str] = Field(default_factory=list)
    configuration_files: list[str] = Field(default_factory=list)

    risk_sensitive_areas: list[str] = Field(default_factory=list)

    monorepo: bool = False
    services_or_packages: list[str] = Field(default_factory=list)

    analysis_confidence: str = "Unknown"
    limitations: list[str] = Field(default_factory=list)

    @classmethod
    def empty(cls, repository_root: Path) -> RepositoryProfile:
        return cls(
            project_name=repository_root.name,
            repository_root=str(repository_root),
            limitations=["Repository has not been profiled yet."],
        )
