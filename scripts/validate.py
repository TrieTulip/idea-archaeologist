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


def validate(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate IDEA ARCHAEOLOGIST Markdown knowledge assets."
    )
    parser.add_argument("knowledge_dir", type=Path)
    args = parser.parse_args()

    errors, warnings, counts = validate(args.knowledge_dir.resolve())
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"FAIL: {len(errors)} validation error(s)")
        return 1

    summary = ", ".join(f"{name}={count}" for name, count in counts.items())
    print(f"PASS: knowledge assets valid ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
