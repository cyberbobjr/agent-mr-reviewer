from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List

from unidiff import PatchSet


@dataclass
class Finding:
    path: str
    line: int
    message: str
    severity: str
    rule_id: str


SNAKE_CASE = re.compile(r"^[a-z_][a-z0-9_]*$")
PASCAL_CASE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
TICKET_PATTERN = re.compile(r"TODO[:\s]*[A-Z]{2,}-\d+")


def analyze_diff(patch: PatchSet) -> List[Finding]:
    findings: List[Finding] = []
    for patched_file in patch:
        if patched_file.is_binary_file:
            continue
        for hunk in patched_file:
            hunk_lines = list(hunk)
            for index, line in enumerate(hunk_lines):
                if not line.is_added or line.is_removed:
                    continue
                content = line.value.rstrip("\n")
                path = patched_file.path
                line_no = line.target_line_no
                if line_no is None:
                    continue

                if content.rstrip() != content:
                    findings.append(
                        Finding(
                            path=path,
                            line=line_no,
                            message="Trailing whitespace detected.",
                            severity="low",
                            rule_id="TRAILING_WS",
                        )
                    )

                if len(content) > 120:
                    findings.append(
                        Finding(
                            path=path,
                            line=line_no,
                            message="Line exceeds 120 characters; consider wrapping.",
                            severity="low",
                            rule_id="LINE_LENGTH",
                        )
                    )

                if "TODO" in content and not TICKET_PATTERN.search(content):
                    findings.append(
                        Finding(
                            path=path,
                            line=line_no,
                            message="TODO without ticket reference; add an issue key.",
                            severity="medium",
                            rule_id="TODO_TICKET",
                        )
                    )

                if re.match(r"\s*print\(", content):
                    findings.append(
                        Finding(
                            path=path,
                            line=line_no,
                            message="Avoid print in production code; use logging.",
                            severity="medium",
                            rule_id="PRINT_LOGGING",
                        )
                    )

                def_match = re.match(r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", content)
                if def_match:
                    func_name = def_match.group(1)
                    if not SNAKE_CASE.match(func_name):
                        findings.append(
                            Finding(
                                path=path,
                                line=line_no,
                                message="Function name should be snake_case.",
                                severity="medium",
                                rule_id="FUNC_NAMING",
                            )
                        )

                    if not _has_docstring(hunk_lines, index):
                        findings.append(
                            Finding(
                                path=path,
                                line=line_no,
                                message="Function missing docstring in this change.",
                                severity="low",
                                rule_id="FUNC_DOC",
                            )
                        )

                class_match = re.match(r"\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", content)
                if class_match:
                    class_name = class_match.group(1)
                    if not PASCAL_CASE.match(class_name):
                        findings.append(
                            Finding(
                                path=path,
                                line=line_no,
                                message="Class name should be PascalCase.",
                                severity="medium",
                                rule_id="CLASS_NAMING",
                            )
                        )

    return findings


def _has_docstring(hunk_lines, def_index: int) -> bool:
    for line in hunk_lines[def_index + 1 : def_index + 4]:
        if line.is_added and ("\"\"\"" in line.value or "'''" in line.value):
            return True
    return False
