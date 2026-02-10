from __future__ import annotations

from typing import Any, Dict, Iterable, List
import json

import tiktoken
from unidiff import PatchSet

from agent_mr_reviewer.llm_client import OpenAICompatibleClient
from agent_mr_reviewer.review_rules import Finding


def map_reduce_review(
    client: OpenAICompatibleClient,
    mr: Dict[str, Any],
    changes: Iterable[Dict[str, Any]],
    max_context_tokens: int = 50000,
    chunk_tokens: int = 12000,
) -> List[Finding]:
    encoding = tiktoken.get_encoding("cl100k_base")
    annotated = build_annotated_diff(changes)
    chunks = chunk_texts(annotated, chunk_tokens, encoding)

    findings: List[Finding] = []
    for chunk in chunks:
        messages = _build_map_messages(mr, chunk)
        content = client.chat(messages, temperature=0.1, max_tokens=1500)
        findings.extend(parse_findings(content))

    return dedupe_findings(findings)


def build_annotated_diff(changes: Iterable[Dict[str, Any]]) -> List[str]:
    texts: List[str] = []
    for change in changes:
        diff = change.get("diff")
        if not diff:
            continue
        patch = PatchSet(diff)
        for patched_file in patch:
            if patched_file.is_binary_file:
                continue
            file_path = patched_file.path or change.get("new_path") or change.get("old_path")
            lines: List[str] = [f"File: {file_path}"]
            for hunk in patched_file:
                lines.append(f"Hunk: {hunk.target_start},{hunk.target_length}")
                for line in hunk:
                    if line.is_added:
                        if line.target_line_no is None:
                            continue
                        lines.append(f"+{line.target_line_no}: {line.value.rstrip()}")
                    elif line.is_removed:
                        if line.source_line_no is None:
                            continue
                        lines.append(f"-{line.source_line_no}: {line.value.rstrip()}")
                    else:
                        if line.target_line_no is None:
                            continue
                        lines.append(f" {line.target_line_no}: {line.value.rstrip()}")
            texts.append("\n".join(lines))
    return texts


def chunk_texts(texts: Iterable[str], max_tokens: int, encoding) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for text in texts:
        text_tokens = _count_tokens(text, encoding)
        if text_tokens > max_tokens:
            chunks.extend(_split_large_text(text, max_tokens, encoding))
            continue

        if current_tokens + text_tokens > max_tokens and current:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0

        current.append(text)
        current_tokens += text_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _split_large_text(text: str, max_tokens: int, encoding) -> List[str]:
    chunks: List[str] = []
    buffer: List[str] = []
    buffer_tokens = 0
    for line in text.splitlines():
        line_text = f"{line}\n"
        line_tokens = _count_tokens(line_text, encoding)
        if buffer_tokens + line_tokens > max_tokens and buffer:
            chunks.append("\n".join(buffer))
            buffer = []
            buffer_tokens = 0
        buffer.append(line)
        buffer_tokens += line_tokens
    if buffer:
        chunks.append("\n".join(buffer))
    return chunks


def _count_tokens(text: str, encoding) -> int:
    return len(encoding.encode(text))


def _build_map_messages(mr: Dict[str, Any], chunk: str) -> List[Dict[str, str]]:
    title = mr.get("title", "(no title)")
    description = (mr.get("description") or "").strip()
    return [
        {
            "role": "system",
            "content": (
                "You are a senior code reviewer for GitLab merge requests. "
                "Return ONLY valid JSON. No markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                "Review the following annotated diff chunk. Focus on code quality, "
                "naming, documentation, architecture, clean code, and design patterns. "
                "Use the line numbers provided.\n\n"
                f"MR Title: {title}\n"
                f"MR Description: {description}\n\n"
                "Return a JSON array of objects with keys: "
                "path (string), line (int), severity (low|medium|high), message (markdown string), rule_id (string).\n"
                "If there are no issues, return an empty array: [].\n\n"
                f"Annotated diff:\n{chunk}"
            ),
        },
    ]


def parse_findings(content: str) -> List[Finding]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict) and "findings" in data:
        data = data["findings"]

    if not isinstance(data, list):
        return []

    findings: List[Finding] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        line = item.get("line")
        message = item.get("message")
        if not path or message is None:
            continue
        try:
            line_no = int(line)
        except (TypeError, ValueError):
            continue
        severity = str(item.get("severity", "medium")).lower()
        if severity not in {"low", "medium", "high"}:
            severity = "medium"
        rule_id = str(item.get("rule_id", "LLM"))
        findings.append(
            Finding(
                path=path,
                line=line_no,
                message=str(message),
                severity=severity,
                rule_id=rule_id,
            )
        )

    return findings


def dedupe_findings(findings: Iterable[Finding]) -> List[Finding]:
    seen = set()
    unique: List[Finding] = []
    for finding in findings:
        key = (finding.path, finding.line, finding.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
