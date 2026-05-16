from __future__ import annotations

from pydantic import BaseModel, Field


class WorkPackage(BaseModel):
    id: str
    title: str
    linked_debt_items: list[str] = Field(default_factory=list)
    objective: str
    current_risk: str
    recommended_engineering_approach: list[str] = Field(default_factory=list)
    expected_affected_areas: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    verification_recommendations: list[str] = Field(default_factory=list)
    risks_and_cautions: list[str] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)
    estimated_effort: str = "Medium"
    expected_risk_reduction: str = "Medium"
    suggested_owner_area: str = ""
    status: str = "Ready for Product Engineering review"


class PlanResult(BaseModel):
    remediation_roadmap_path: str
    handoff_summary_path: str
    work_package_paths: list[str] = Field(default_factory=list)
    work_packages: list[WorkPackage] = Field(default_factory=list)
