"""Node that compiles findings and tool results into a final report."""

import json
import logging
from collections import defaultdict
from typing import Any, Dict

from app.clients.llm_client import create_llm_client
from app.graphs.state import SwissArmyKnifeState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Compile a security assessment report from the tool findings. Include:

1. **Executive Summary** -- a concise overview of what was done and the most
   important results.
2. **Tools Used** -- list each tool and what it was used for.
3. **Findings** -- sorted by severity (critical first), with clear
   descriptions and recommended next steps.
4. **Recommendations** -- actionable advice for remediation or further
   investigation.

Write in clear, professional language suitable for a technical audience.
"""


async def compile_report(state: SwissArmyKnifeState) -> Dict[str, Any]:
    """Aggregate findings and produce a human-readable assessment report."""

    findings = state.get("findings", [])
    tool_results = state.get("tool_results", [])
    tools_used = state.get("tools_used", [])
    plan = state.get("plan", {})

    # Group findings by severity for the structured report.
    findings_by_severity: Dict[str, list] = defaultdict(list)
    for finding in findings:
        severity = finding.get("severity", "info")
        findings_by_severity[severity].append(finding)

    # Build the LLM prompt with all collected data.
    user_prompt = (
        f"Plan rationale: {plan.get('rationale', 'N/A')}\n\n"
        f"Tools used: {json.dumps(tools_used)}\n\n"
        f"Total findings: {len(findings)}\n\n"
        f"Findings:\n{json.dumps(findings, indent=2)}\n\n"
        "Generate the assessment report."
    )

    try:
        llm = create_llm_client()
        llm_summary = await llm.generate(
            prompt=user_prompt,
            system=SYSTEM_PROMPT,
        )
    except Exception as exc:
        logger.error("LLM report compilation failed: %s", exc)
        llm_summary = (
            "Report generation failed. "
            f"Total findings: {len(findings)}. "
            f"Tools used: {', '.join(tools_used) if tools_used else 'none'}."
        )

    report: Dict[str, Any] = {
        "summary": llm_summary,
        "tools_used": tools_used,
        "total_findings": len(findings),
        "findings_by_severity": dict(findings_by_severity),
        "findings": findings,
        "raw_results": [r for r in tool_results],
    }

    return {"report": report, "response": llm_summary}
