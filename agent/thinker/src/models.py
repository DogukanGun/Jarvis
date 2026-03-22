from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class Problem(BaseModel):
    id: str
    title: str
    description: str
    source_url: str | None = None


class SubProblem(BaseModel):
    id: str
    parent_id: str
    title: str
    description: str
    research_angle: Literal[
        "literature",
        "feasibility",
        "baselines",
        "implementation_approach",
        "evaluation_strategy",
    ]


class SubProblemReport(BaseModel):
    sub_problem_id: str
    findings: str
    implementation_plan: str


class ExecutionPlan(BaseModel):
    problem_id: str
    chosen_direction: str
    steps: list[str]
    tech_stack: list[str]
    validation_criteria: list[str]


class TestResults(BaseModel):
    problem_id: str
    passed: bool
    output: str
    metrics: dict[str, float]


class ComparisonReport(BaseModel):
    problem_id: str
    our_approach_summary: str
    compared_systems: list[str]
    strengths: list[str]
    weaknesses: list[str]
