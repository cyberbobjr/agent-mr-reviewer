from __future__ import annotations

from typing import List

from agent_mr_reviewer.diff_parser import parse_diff
from agent_mr_reviewer.gitlab_client import GitLabClient
from agent_mr_reviewer.llm_review import map_reduce_review
from agent_mr_reviewer.llm_summary import build_llm_summary
from agent_mr_reviewer.llm_client import OpenAICompatibleClient
from agent_mr_reviewer.review_rules import Finding, analyze_diff


def run_review(
    client: GitLabClient,
    project_id: str,
    mr_iid: str,
    max_comments: int,
    summary_only: bool,
    dry_run: bool,
    llm_client: OpenAICompatibleClient | None,
    llm_max_context: int,
    llm_chunk_tokens: int,
) -> None:
    mr = client.get_merge_request(project_id, mr_iid)
    changes = client.get_changes(project_id, mr_iid)
    commits = client.get_commits(project_id, mr_iid)

    diff_refs = mr.get("diff_refs") or {}
    base_sha = diff_refs.get("base_sha")
    start_sha = diff_refs.get("start_sha")
    head_sha = diff_refs.get("head_sha")

    all_findings: List[Finding]
    if llm_client:
        all_findings = map_reduce_review(
            client=llm_client,
            mr=mr,
            changes=changes.get("changes", []),
            max_context_tokens=llm_max_context,
            chunk_tokens=llm_chunk_tokens,
        )
    else:
        all_findings = []
        for change in changes.get("changes", []):
            patch_text = change.get("diff")
            if not patch_text:
                continue
            patch = parse_diff(patch_text)
            all_findings.extend(analyze_diff(patch))

    limited_findings = all_findings[:max_comments]

    if not summary_only:
        for finding in limited_findings:
            body = f"[{finding.severity}] {finding.message} (rule: {finding.rule_id})"
            position = {
                "position_type": "text",
                "base_sha": base_sha,
                "start_sha": start_sha,
                "head_sha": head_sha,
                "new_path": finding.path,
                "new_line": finding.line,
            }
            if dry_run:
                print(f"INLINE {finding.path}:{finding.line} {body}")
            else:
                client.post_discussion(project_id, mr_iid, body, position)

    if llm_client:
        summary = build_llm_summary(mr, all_findings, max_comments, source_label="LLM")
    else:
        summary = _build_summary(mr, commits, all_findings, max_comments)
    if dry_run:
        print("SUMMARY")
        print(summary)
    else:
        client.post_note(project_id, mr_iid, summary)


def _build_summary(mr, commits, findings: List[Finding], max_comments: int) -> str:
    total = len(findings)
    by_sev = {"high": 0, "medium": 0, "low": 0}
    for finding in findings:
        by_sev[finding.severity] = by_sev.get(finding.severity, 0) + 1

    title = mr.get("title", "(no title)")
    commit_count = len(commits) if isinstance(commits, list) else 0

    lines = [
        "MR Review Summary",
        f"- Title: {title}",
        f"- Commits: {commit_count}",
        f"- Findings: {total} (high: {by_sev.get('high', 0)}, medium: {by_sev.get('medium', 0)}, low: {by_sev.get('low', 0)})",
        f"- Inline comments posted: {min(total, max_comments)}",
        "",
        "Top findings:",
    ]

    for finding in findings[:10]:
        lines.append(
            f"- {finding.path}:{finding.line} [{finding.severity}] {finding.message}"
        )

    return "\n".join(lines)
