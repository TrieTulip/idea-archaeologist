#!/usr/bin/env python3
"""Route a creative request to a task type and thinking mode.

This CLI is a deterministic aid for the Skill. It does not generate ideas or
replace user intent; explicit mode and task overrides always win.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / "references"
TASK_TYPES = {
    "discovery",
    "cross-domain",
    "problem",
    "knowledge-archaeology",
    "review",
    "retrospective",
}
MODES = {"quick", "standard", "deep"}

TASK_PATTERNS = (
    ("retrospective", ("回顾", "复盘", "过去", "历史记录", "历史探索", "偏好变化", "阶段报告")),
    ("review", ("评审", "评估这个", "判断这个", "优化已有", "风险分析", "值不值得")),
    ("cross-domain", ("跨领域", "跨界", "类比迁移", "联系起来", "之间有什么联系")),
    ("knowledge-archaeology", ("第一性原理", "知识考古", "旧笔记", "文章", "这个概念", "原理如何")),
    ("problem", ("瓶颈", "系统方案", "解决方案", "真正的问题", "重要决策", "多个约束")),
)

QUICK_SIGNALS = ("快速", "简洁", "简单创意", "三个", "几个点子", "不用评分", "先给方向")
DEEP_SIGNALS = (
    "深度",
    "完整",
    "系统研究",
    "重要决策",
    "高风险",
    "多个约束",
    "完整评分",
    "全面评估",
)

STAGES = {
    "quick": {
        "discovery": ["Analyze", "Retrieve", "Cross-domain", "Explore", "Observe"],
        "cross-domain": ["Analyze", "Retrieve", "Cross-domain", "Hypothesize", "Explore", "Observe"],
        "problem": ["Analyze", "Retrieve", "Explore", "Observe"],
        "knowledge-archaeology": ["Analyze", "Retrieve", "Explore", "Observe"],
        "review": ["Analyze", "Retrieve", "Observe", "Launch"],
        "retrospective": ["Retrieve", "Observe"],
    },
    "standard": {
        "discovery": ["Analyze", "Retrieve", "Cross-domain", "Explore", "Observe"],
        "cross-domain": [
            "Analyze",
            "Retrieve",
            "Cross-domain",
            "Hypothesize",
            "Associate",
            "Explore",
            "Observe",
        ],
        "problem": [
            "Analyze",
            "Retrieve",
            "Cross-domain",
            "Hypothesize",
            "Associate",
            "Explore",
            "Observe",
            "Launch",
        ],
        "knowledge-archaeology": [
            "Analyze",
            "Retrieve",
            "Hypothesize",
            "Associate",
            "Explore",
            "Observe",
            "Launch",
        ],
        "review": ["Analyze", "Retrieve", "Observe", "Launch"],
        "retrospective": ["Retrieve", "Observe", "Launch"],
    },
    "deep": {
        task: [
            "Analyze",
            "Retrieve",
            "Cross-domain",
            "Hypothesize",
            "Associate",
            "Explore",
            "Observe",
            "Launch",
            "Optimize",
        ]
        for task in TASK_TYPES
    },
}


def detect_task_type(text: str) -> tuple[str, str]:
    for task_type, patterns in TASK_PATTERNS:
        for pattern in patterns:
            if pattern in text:
                return task_type, f"request contains “{pattern}”"
    return "discovery", "request asks for open-ended inspiration"


def detect_mode(text: str) -> tuple[str, str]:
    if any(signal in text for signal in DEEP_SIGNALS):
        return "deep", "request contains an explicit depth or decision-risk signal"
    if any(signal in text for signal in QUICK_SIGNALS) and not any(
        signal in text for signal in ("多个约束", "重要", "完整评估")
    ):
        return "quick", "request asks for a small, direct answer"
    return "standard", "default for ordinary creative exploration"


def reference_files_for(mode: str, task_type: str, text: str) -> list[str]:
    if mode == "quick":
        names: list[str] = []
    elif mode == "deep":
        names = [
            "methodology.md",
            "thinking-models.md",
            "scoring-rules.md",
            "interaction-rules.md",
            "memory-protocol.md",
        ]
    else:
        names = []
        if task_type in {"cross-domain", "problem", "knowledge-archaeology"}:
            names.append("thinking-models.md")
        if task_type in {"review", "problem"} or any(
            signal in text for signal in ("评分", "评估", "价值", "可行性")
        ):
            names.append("scoring-rules.md")
        if any(signal in text for signal in ("怎么输出", "格式", "简洁", "压缩")):
            names.append("interaction-rules.md")
        if task_type == "retrospective":
            names.append("memory-protocol.md")

    return [str(REFERENCES / name) for name in dict.fromkeys(names)]


def route(
    text: str,
    task_type_override: str = "auto",
    mode_override: str = "auto",
) -> dict[str, object]:
    task_type, task_reason = (
        (task_type_override, "explicit task-type override")
        if task_type_override != "auto"
        else detect_task_type(text)
    )
    mode, mode_reason = (
        (mode_override, "explicit mode override")
        if mode_override != "auto"
        else detect_mode(text)
    )
    return {
        "task_type": task_type,
        "mode": mode,
        "stages": STAGES[mode][task_type],
        "reference_files": reference_files_for(mode, task_type, text),
        "reason": {"task_type": task_reason, "mode": mode_reason},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, help="User request text.")
    parser.add_argument("--task-type", choices=("auto", *sorted(TASK_TYPES)), default="auto")
    parser.add_argument("--mode", choices=("auto", *sorted(MODES)), default="auto")
    args = parser.parse_args()
    print(json.dumps(route(args.text, args.task_type, args.mode), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
