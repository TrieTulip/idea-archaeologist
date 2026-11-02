#!/usr/bin/env python3
"""Validate IDEA ARCHAEOLOGIST Markdown knowledge assets.

The validator is read-only and uses only the Python standard library.
Semantic duplicate detection still requires an explicit model/user review.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable


REQUIRED_FILES = ("ideas.md", "connections.md", "preferences.md", "evolution.md")
V2_INDEX_FIELDS = ("类型", "详情路径", "关键词", "摘要")
RECORD_HEADING = re.compile(r"^##\s+([A-Z]+-[^\s—]+)(?:\s+—.*)?\s*$")
FIELD_LINE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*[:：]\s*(.*?)\s*$")
DATE_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_TEXT = re.compile(r"^(IA|CN|FB|PREF)-\d{8}-\d{2}$")
VERSION_TEXT = re.compile(r"^\d+\.\d+\.\d+$")
REFERENCE_TEXT = re.compile(r"\b(?:IA|CN|FB|PREF)-\d{8}-\d{2}\b")

REQUIRED_FIELDS = {
    "ideas": (
        "日期",
        "主题",
        "创意名称",
        "核心构想",
        "来源",
        "推导逻辑",
        "评分",
        "当前状态",
        "去重键",
    ),
    "connections": (
        "日期",
        "概念A",
        "概念B",
        "共同原理",
        "关联类型",
        "应用场景",
        "适用边界",
        "置信度",
        "去重键",
    ),
    "feedback": (
        "日期",
        "关联创意",
        "原始反馈",
        "偏好级别",
        "授权状态",
        "状态变更",
        "重复检查",
    ),
    "preferences": (
        "日期",
        "偏好类型",
        "内容",
        "反馈依据",
        "确认状态",
        "当前状态",
    ),
    "evolution": (
        "版本号",
        "日期",
        "原有问题",
        "优化建议",
        "具体修改",
        "预期收益",
        "用户确认状态",
        "应用状态",
        "实际修改",
    ),
}


@dataclass
class Record:
    record_id: str
    title: str
    source: str
    fields: dict[str, str] = field(default_factory=dict)


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", "", value)


def normalize_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold(), flags=re.UNICODE)


def version_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def parse_records(path: Path) -> list[Record]:
    records: list[Record] = []
    current: Record | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        heading = RECORD_HEADING.match(raw_line)
        if heading:
            record_id = heading.group(1)
            suffix = raw_line[heading.end(1) :].strip(" —-")
            current = Record(record_id=record_id, title=suffix, source=path.name)
            records.append(current)
            continue

        if raw_line.startswith("## "):
            current = None
            continue

        if current is None:
            continue

        field_match = FIELD_LINE.match(raw_line)
        if not field_match:
            continue

        label = normalize_label(field_match.group(1))
        value = field_match.group(2).strip()
        if label in current.fields:
            current.fields[f"{label}__DUPLICATE"] = value
        else:
            current.fields[label] = value

    return records


def record_kind(record_or_id: Record | str) -> str:
    record_id = (
        record_or_id.record_id if isinstance(record_or_id, Record) else record_or_id
    )
    if record_id.startswith("IA-"):
        return "ideas"
    if record_id.startswith("CN-"):
        return "connections"
    if record_id.startswith("FB-"):
        return "feedback"
    if record_id.startswith("PREF-"):
        return "preferences"
    if record_id.startswith("EV-") and VERSION_TEXT.fullmatch(record_id[3:]):
        return "evolution"
    return "unknown"


def required_for(record: Record) -> Iterable[str]:
    kind = record_kind(record.record_id)
    return REQUIRED_FIELDS.get(kind, ())


def add_record_errors(record: Record, errors: list[str]) -> None:
    kind = record_kind(record.record_id)
    if kind == "unknown":
        errors.append(f"{record.source}: invalid record ID {record.record_id}")
        return

    if kind != "evolution" and not ID_TEXT.fullmatch(record.record_id):
        errors.append(f"{record.source}: malformed ID {record.record_id}")

    for field_name in required_for(record):
        value = record.fields.get(field_name, "")
        if not value:
            errors.append(
                f"{record.source}: {record.record_id} missing required field {field_name}"
            )

    date_value = record.fields.get("日期", "").strip("` ")
    if date_value and not DATE_TEXT.fullmatch(date_value):
        errors.append(f"{record.source}: {record.record_id} invalid date {date_value}")
    elif DATE_TEXT.fullmatch(date_value):
        try:
            date.fromisoformat(date_value)
        except ValueError:
            errors.append(f"{record.source}: {record.record_id} invalid calendar date {date_value}")

    duplicate_field = [name for name in record.fields if name.endswith("__DUPLICATE")]
    for field_name in duplicate_field:
        errors.append(
            f"{record.source}: {record.record_id} duplicates field {field_name.removesuffix('__DUPLICATE')}"
        )


def add_v2_detail_errors(record: Record, errors: list[str]) -> None:
    add_record_errors(record, errors)
    for field_name in ("当前版本", "版本历史"):
        if not record.fields.get(field_name, "").strip():
            errors.append(
                f"{record.source}: {record.record_id} missing required field {field_name}"
            )
    current_version = record.fields.get("当前版本", "").strip()
    history = record.fields.get("版本历史", "").strip()
    if current_version and not current_version.isdigit():
        errors.append(f"{record.source}: {record.record_id} invalid current version")
    elif current_version and history and not re.search(
        rf"(?<!\d){re.escape(current_version)}\s*\|", history
    ):
        errors.append(
            f"{record.source}: {record.record_id} version history lacks current version {current_version}"
        )


def add_duplicate_errors(
    records: list[Record], errors: list[str], warnings: list[str]
) -> None:
    seen_ids: dict[str, str] = {}
    seen_keys: dict[tuple[str, str], str] = {}
    seen_titles: dict[tuple[str, str], str] = {}

    for record in records:
        kind = record_kind(record.record_id)
        if record.record_id in seen_ids:
            errors.append(
                f"{record.source}: duplicate ID {record.record_id} "
                f"(also in {seen_ids[record.record_id]})"
            )
        else:
            seen_ids[record.record_id] = record.source

        title = record.fields.get("创意名称", record.title).strip()
        normalized_title = normalize_text(title)
        if kind in {"ideas", "connections"} and normalized_title:
            title_key = (kind, normalized_title)
            if title_key in seen_titles:
                errors.append(
                    f"{record.source}: duplicate normalized title for {record.record_id}: {title}"
                )
            else:
                seen_titles[title_key] = record.record_id

        dedupe_key = record.fields.get("去重键", "").strip().casefold()
        if kind in {"ideas", "connections"} and dedupe_key:
            key = (kind, dedupe_key)
            if key in seen_keys:
                errors.append(
                    f"{record.source}: duplicate dedupe key '{dedupe_key}' "
                    f"in {seen_keys[key]} and {record.record_id}"
                )
            else:
                seen_keys[key] = record.record_id

    titles = [
        (record.record_id, normalize_text(record.fields.get("创意名称", record.title)))
        for record in records
        if record_kind(record) == "ideas"
    ]
    for index, (left_id, left_title) in enumerate(titles):
        for right_id, right_title in titles[index + 1 :]:
            if not left_title or not right_title or left_title == right_title:
                continue
            ratio = difflib.SequenceMatcher(None, left_title, right_title).ratio()
            if ratio >= 0.82:
                warnings.append(
                    f"{record.source}: possible near-duplicate ideas {left_id} / "
                    f"{right_id} (title similarity {ratio:.2f}); review mechanism and scenario"
                )


def add_reference_errors(
    ideas: list[Record],
    connections: list[Record],
    preferences_records: list[Record],
    errors: list[str],
) -> None:
    idea_ids = {record.record_id for record in ideas}
    connection_ids = {record.record_id for record in connections}
    feedback = [record for record in preferences_records if record.record_id.startswith("FB-")]
    feedback_ids = {record.record_id for record in feedback}
    feedback_by_id = {record.record_id: record for record in feedback}
    preferences = [record for record in preferences_records if record.record_id.startswith("PREF-")]

    for record in feedback:
        linked_ideas = record.fields.get("关联创意", "")
        if linked_ideas.strip() not in {"", "不适用"}:
            references = REFERENCE_TEXT.findall(linked_ideas)
            if not references:
                errors.append(
                    f"preferences.md: {record.record_id} has no parseable idea reference"
                )
            for reference in references:
                if reference.startswith("IA-") and reference not in idea_ids:
                    errors.append(
                        f"preferences.md: {record.record_id} references missing idea {reference}"
                    )
                if reference.startswith("CN-") and reference not in connection_ids:
                    errors.append(
                        f"preferences.md: {record.record_id} references missing connection {reference}"
                    )

        level = record.fields.get("偏好级别", "")
        if level not in {"明确偏好", "待确认模式", "单次信号"}:
            errors.append(f"preferences.md: {record.record_id} invalid preference level {level}")

        authorization = record.fields.get("授权状态", "")
        if authorization not in {"已授权", "未授权"}:
            errors.append(
                f"preferences.md: {record.record_id} invalid authorization {authorization}"
            )

    for record in preferences:
        if record.fields.get("偏好类型") != "明确偏好":
            errors.append(
                f"preferences.md: {record.record_id} stable preference must be 明确偏好"
            )
        if record.fields.get("确认状态") != "已确认":
            errors.append(
                f"preferences.md: {record.record_id} stable preference is not confirmed"
            )
        if record.fields.get("当前状态") not in {"有效", "已撤销"}:
            errors.append(
                f"preferences.md: {record.record_id} invalid current state"
            )

        evidence = REFERENCE_TEXT.findall(record.fields.get("反馈依据", ""))
        if not evidence:
            errors.append(
                f"preferences.md: {record.record_id} has no feedback evidence"
            )
        has_explicit_feedback = False
        for reference in evidence:
            if reference.startswith("FB-") and reference not in feedback_ids:
                errors.append(
                    f"preferences.md: {record.record_id} references missing feedback {reference}"
                )
                continue
            source_feedback = feedback_by_id.get(reference)
            if source_feedback is None:
                continue
            if source_feedback.fields.get("授权状态") != "已授权":
                errors.append(
                    f"preferences.md: {record.record_id} depends on unauthorized feedback {reference}"
                )
            if source_feedback.fields.get("偏好级别") == "明确偏好":
                has_explicit_feedback = True
        if evidence and not has_explicit_feedback:
            errors.append(
                f"preferences.md: {record.record_id} lacks explicit-preference feedback"
            )


def add_version_errors(records: list[Record], errors: list[str]) -> None:
    versions: dict[str, Record] = {}
    applied: list[tuple[tuple[int, int, int], Record]] = []

    for record in records:
        version = record.fields.get("版本号", "").strip("` ")
        if not VERSION_TEXT.fullmatch(version):
            errors.append(f"evolution.md: {record.record_id} invalid version {version}")
            continue
        if record.record_id != f"EV-{version}":
            errors.append(
                f"evolution.md: {record.record_id} does not match version {version}"
            )
        if version in versions:
            errors.append(f"evolution.md: duplicate version {version}")
        else:
            versions[version] = record

        status = record.fields.get("应用状态", "")
        if status not in {"待确认", "已应用", "已回滚"}:
            errors.append(
                f"evolution.md: {record.record_id} invalid application status {status}"
            )
        if status == "已应用":
            confirmation = record.fields.get("用户确认状态", "")
            if "已确认" not in confirmation:
                errors.append(
                    f"evolution.md: {record.record_id} is applied without user confirmation"
                )
            if not record.fields.get("实际修改"):
                errors.append(
                    f"evolution.md: {record.record_id} is applied without actual changes"
                )
            applied.append((version_tuple(version), record))

    previous: tuple[int, int, int] | None = None
    for version, record in applied:
        if previous is not None and version < previous:
            errors.append(
                f"evolution.md: applied versions are out of order at {record.record_id}"
            )
        previous = version


def validate_legacy(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        return [f"Knowledge directory not found: {root}"], warnings, {}

    for filename in REQUIRED_FILES:
        if not (root / filename).is_file():
            errors.append(f"Missing required file: {filename}")

    if errors:
        return errors, warnings, {}

    ideas = parse_records(root / "ideas.md")
    connections = parse_records(root / "connections.md")
    preferences = parse_records(root / "preferences.md")
    evolution = parse_records(root / "evolution.md")
    all_records = ideas + connections + preferences + evolution

    for record in all_records:
        add_record_errors(record, errors)

    add_duplicate_errors(ideas + connections, errors, warnings)
    add_reference_errors(ideas, connections, preferences, errors)
    add_version_errors(evolution, errors)

    counts = {
        "ideas": len(ideas),
        "connections": len(connections),
        "feedback": sum(record.record_id.startswith("FB-") for record in preferences),
        "preferences": sum(record.record_id.startswith("PREF-") for record in preferences),
        "evolution": len(evolution),
    }
    return errors, warnings, counts


def validate_v2(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    """Validate the V2 index-first knowledge layout."""
    errors: list[str] = []
    warnings: list[str] = []

    for directory in ("ideas", "connections"):
        if not (root / directory).is_dir():
            errors.append(f"Missing required directory: {directory}/")
    for filename in ("index.md", "preferences.md", "evolution.md"):
        if not (root / filename).is_file():
            errors.append(f"Missing required file: {filename}")
    if errors:
        return errors, warnings, {}

    index_records = parse_records(root / "index.md")
    seen_index_ids: dict[str, str] = {}
    indexed: dict[str, str] = {}
    linked_details: set[Path] = set()

    for entry in index_records:
        if entry.record_id in seen_index_ids:
            errors.append(
                f"index.md: duplicate index ID {entry.record_id} "
                f"(also in {seen_index_ids[entry.record_id]})"
            )
        else:
            seen_index_ids[entry.record_id] = "index.md"

        for field_name in V2_INDEX_FIELDS:
            if not entry.fields.get(field_name, "").strip():
                errors.append(
                    f"index.md: {entry.record_id} missing required index field {field_name}"
                )

        expected_kind = record_kind(entry.record_id)
        declared_kind = (
            "ideas"
            if entry.fields.get("类型") == "创意"
            else "connections"
            if entry.fields.get("类型") == "关联"
            else "unknown"
        )
        if declared_kind == "unknown":
            errors.append(f"index.md: {entry.record_id} invalid index type")
        elif expected_kind != declared_kind:
            errors.append(
                f"index.md: {entry.record_id} ID prefix does not match type {declared_kind}"
            )

        relative = entry.fields.get("详情路径", "").strip("` ")
        if not relative:
            continue
        detail_path = (root / relative).resolve()
        try:
            detail_path.relative_to(root.resolve())
        except ValueError:
            errors.append(f"index.md: {entry.record_id} detail path escapes knowledge root")
            continue
        if detail_path.suffix != ".md":
            errors.append(f"index.md: {entry.record_id} detail path must be Markdown")
        if not detail_path.is_file():
            errors.append(
                f"index.md: {entry.record_id} missing detail file {relative}"
            )
            continue
        if detail_path in linked_details:
            errors.append(
                f"index.md: {entry.record_id} reuses detail file {relative}"
            )
        linked_details.add(detail_path)
        indexed[entry.record_id] = relative

    detail_records: list[Record] = []
    for category in ("ideas", "connections"):
        for path in sorted((root / category).glob("*.md")):
            if path.resolve() not in linked_details:
                errors.append(f"{category}: unindexed detail file {path.name}")
            records = parse_records(path)
            if len(records) != 1:
                errors.append(
                    f"{category}/{path.name}: expected one V2 detail record, found {len(records)}"
                )
            for record in records:
                detail_records.append(record)
                indexed_path = indexed.get(record.record_id)
                if indexed_path is None:
                    errors.append(
                        f"{category}/{path.name}: detail record {record.record_id} has no index entry"
                    )
                elif (root / indexed_path).resolve() != path.resolve():
                    errors.append(
                        f"{category}/{path.name}: detail record {record.record_id} "
                        "does not match its indexed path"
                    )

    for record in detail_records:
        add_v2_detail_errors(record, errors)
    add_duplicate_errors(detail_records, errors, warnings)

    preferences = parse_records(root / "preferences.md")
    evolution = parse_records(root / "evolution.md")
    for record in preferences + evolution:
        add_record_errors(record, errors)
    add_reference_errors(
        [r for r in detail_records if record_kind(r) == "ideas"],
        [r for r in detail_records if record_kind(r) == "connections"],
        preferences,
        errors,
    )
    add_version_errors(evolution, errors)

    counts = {
        "ideas": sum(record_kind(r) == "ideas" for r in detail_records),
        "connections": sum(record_kind(r) == "connections" for r in detail_records),
        "feedback": sum(record.record_id.startswith("FB-") for record in preferences),
        "preferences": sum(record.record_id.startswith("PREF-") for record in preferences),
        "evolution": len(evolution),
        "indexed": len(index_records),
    }
    return errors, warnings, counts


def validate(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    if (root / "index.md").is_file() and (root / "ideas").is_dir():
        return validate_v2(root)
    return validate_legacy(root)


def validate_skill(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    """Validate the V2 Skill package and its index-first knowledge store."""
    errors: list[str] = []
    warnings: list[str] = []
    required_files = (
        "SKILL.md",
        "README.md",
        "CHANGELOG.md",
        "references/methodology.md",
        "references/thinking-models.md",
        "references/scoring-rules.md",
        "references/interaction-rules.md",
        "references/memory-protocol.md",
        "knowledge/index.md",
        "knowledge/preferences.md",
        "knowledge/evolution.md",
        "tests/test-cases.md",
        "tests/quality-checklist.md",
        "tests/expected-behaviors.md",
        "tests/evaluation-results.md",
        "scripts/validate.py",
        "scripts/route_mode.py",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            errors.append(f"Missing required Skill file: {relative}")

    for relative in ("knowledge/ideas", "knowledge/connections"):
        if not (root / relative).is_dir():
            errors.append(f"Missing required Skill directory: {relative}/")

    for legacy in ("knowledge/ideas.md", "knowledge/connections.md"):
        if (root / legacy).exists():
            errors.append(f"Legacy knowledge file still present: {legacy}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > 180:
            errors.append(f"SKILL.md is too long for a progressive entry: {len(lines)} lines")
        if not re.search(r"^---\s*$", text, re.MULTILINE):
            errors.append("SKILL.md missing YAML frontmatter")
        if not re.search(r"^name:\s*idea-archaeologist\s*$", text, re.MULTILINE):
            errors.append("SKILL.md has invalid name")
        if not re.search(r'^description:\s*Use when\b', text, re.MULTILINE | re.IGNORECASE):
            errors.append("SKILL.md description must start with 'Use when'")
        if not re.search(r'^  version:\s*"2\.0\.0"\s*$', text, re.MULTILINE):
            errors.append("SKILL.md version must be 2.0.0")
        for mode in ("MODE_QUICK", "MODE_STANDARD", "MODE_DEEP"):
            if mode not in text:
                errors.append(f"SKILL.md missing {mode}")
        if "0.25N + 0.20R + 0.25V + 0.20F + 0.10E" not in text:
            errors.append("SKILL.md missing the required score formula")

        for relative in sorted(set(re.findall(r"\]\((references/[^)#]+)", text))):
            if not (root / relative).is_file():
                errors.append(f"SKILL.md broken reference path: {relative}")
        if len(set(re.findall(r"\]\((references/[^)#]+)", text))) < 5:
            errors.append("SKILL.md must route to all five V2 reference modules")

    knowledge_errors, knowledge_warnings, counts = validate_v2(root / "knowledge")
    errors.extend(knowledge_errors)
    warnings.extend(knowledge_warnings)
    return errors, warnings, counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate IDEA ARCHAEOLOGIST V2 package or knowledge assets."
    )
    parser.add_argument("knowledge_dir", nargs="?", type=Path)
    parser.add_argument("--skill", type=Path, help="Validate a complete Skill package.")
    args = parser.parse_args()

    if (args.knowledge_dir is None) == (args.skill is None):
        parser.error("provide either a knowledge directory or --skill <directory>")

    if args.skill is not None:
        errors, warnings, counts = validate_skill(args.skill.resolve())
    else:
        errors, warnings, counts = validate(args.knowledge_dir.resolve())
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"FAIL: {len(errors)} validation error(s)")
        return 1

    summary = ", ".join(f"{name}={count}" for name, count in counts.items())
    label = "skill package" if args.skill is not None else "knowledge assets"
    print(f"PASS: {label} valid ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
