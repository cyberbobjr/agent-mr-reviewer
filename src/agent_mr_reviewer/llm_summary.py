from __future__ import annotations

from typing import Dict, Iterable

from agent_mr_reviewer.review_rules import Finding


def build_llm_summary(
    mr: Dict[str, str],
    findings: Iterable[Finding],
    max_comments: int,
    source_label: str = "LLM",
) -> str:
    findings_list = list(findings)
    total = len(findings_list)
    by_sev = {"high": 0, "medium": 0, "low": 0}
    for finding in findings_list:
        by_sev[finding.severity] = by_sev.get(finding.severity, 0) + 1

    title = mr.get("title", "(no title)")
    lines = [
        f"MR Review Summary ({source_label})",
        f"- Title: {title}",
        f"- Findings: {total} (high: {by_sev.get('high', 0)}, medium: {by_sev.get('medium', 0)}, low: {by_sev.get('low', 0)})",
        f"- Inline comments posted: {min(total, max_comments)}",
        "",
        "Top findings:",
    ]

    for finding in findings_list[:10]:
        lines.append(
            f"- {finding.path}:{finding.line} [{finding.severity}] {finding.message}"
        )

    return "\n".join(lines)
