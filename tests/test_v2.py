"""Public-interface tests for IDEA ARCHAEOLOGIST V2.0."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "validate.py"
ROUTER = ROOT / "scripts" / "route_mode.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def route(text: str) -> dict[str, object]:
    result = run_cli(str(ROUTER), "--text", text)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout)


class ModeRoutingTests(unittest.TestCase):
    def test_test_01_learning_motivation_uses_standard(self) -> None:
        result = route("如何提高长期学习动力？")
        self.assertEqual(result["task_type"], "discovery")
        self.assertEqual(result["mode"], "standard")
        self.assertNotIn("methodology.md", ",".join(result["reference_files"]))

    def test_test_02_cafe_and_knowledge_management_use_cross_domain(self) -> None:
        result = route("将咖啡馆和知识管理联系起来。")
        self.assertEqual(result["task_type"], "cross-domain")
        self.assertEqual(result["mode"], "standard")
        self.assertIn("Cross-domain", result["stages"])

    def test_test_03_first_principles_use_knowledge_archaeology(self) -> None:
        result = route("解释第一性原理如何应用于产品设计。")
        self.assertEqual(result["task_type"], "knowledge-archaeology")
        self.assertEqual(result["mode"], "standard")

    def test_test_04_existing_idea_uses_review(self) -> None:
        result = route("评审一个自动整理阅读资料并生成知识图谱的应用创意。")
        self.assertEqual(result["task_type"], "review")
        self.assertEqual(result["mode"], "standard")
        self.assertIn("Observe", result["stages"])

    def test_test_05_history_uses_retrospective_and_memory_protocol(self) -> None:
        result = route("回顾过去的探索，并提出知识更新建议。")
        self.assertEqual(result["task_type"], "retrospective")
        self.assertTrue(
            any(str(path).endswith("memory-protocol.md") for path in result["reference_files"])
        )

    def test_test_06_simple_three_ideas_use_quick(self) -> None:
        result = route("给我三个改善日常阅读体验的简单创意。")
        self.assertEqual(result["task_type"], "discovery")
        self.assertEqual(result["mode"], "quick")
        self.assertEqual(result["reference_files"], [])

    def test_explicit_deep_mode_loads_full_references(self) -> None:
        result = route("请深度、完整、系统研究这个重要决策，并给出完整评分和最小验证。")
        self.assertEqual(result["mode"], "deep")
        expected = {
            "methodology.md",
            "thinking-models.md",
            "scoring-rules.md",
            "interaction-rules.md",
            "memory-protocol.md",
        }
        names = {Path(str(path)).name for path in result["reference_files"]}
        self.assertEqual(names, expected)


class SkillPackageTests(unittest.TestCase):
    def test_skill_package_passes_validation(self) -> None:
        result = run_cli(str(VALIDATOR), "--skill", str(ROOT))
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PASS: skill package valid", result.stdout)

    def test_skill_entry_is_progressive_and_bounded(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 180)
        self.assertTrue(text.startswith("---"))
        self.assertIn("name: idea-archaeologist", lines)
        self.assertIn("version: \"2.0.0\"", text)
        self.assertIn("MODE_QUICK", text)
        self.assertIn("MODE_STANDARD", text)
        self.assertIn("MODE_DEEP", text)
        self.assertIn("0.25N + 0.20R + 0.25V + 0.20F + 0.10E", text)
        self.assertNotIn("## ARCHAELOGY 九阶段", text)

    def test_skill_local_reference_paths_exist(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((references/[^)#]+)", text)
        self.assertGreaterEqual(len(links), 5)
        for link in links:
            self.assertTrue((ROOT / link).is_file(), link)


class KnowledgeValidationTests(unittest.TestCase):
    def make_knowledge(self, target: Path) -> None:
        (target / "ideas").mkdir(parents=True)
        (target / "connections").mkdir()
        (target / "index.md").write_text("# 知识索引\n", encoding="utf-8")
        (target / "preferences.md").write_text(
            "# 反馈与偏好\n\n## 反馈事件\n\n当前无记录。\n\n## 已确认偏好\n\n当前无记录。\n",
            encoding="utf-8",
        )
        (target / "evolution.md").write_text("# 系统迭代日志\n", encoding="utf-8")

    def test_empty_v2_knowledge_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self.make_knowledge(target)
            result = run_cli(str(VALIDATOR), str(target))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("PASS: knowledge assets valid", result.stdout)

    def test_index_duplicate_id_and_missing_detail_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self.make_knowledge(target)
            duplicate = """\
## IA-20261102-01 — 重复创意
- **类型**：创意
- **详情路径**：ideas/missing.md
- **关键词**：测试
- **摘要**：同一 ID 出现两次。

## IA-20261102-01 — 另一个重复创意
- **类型**：创意
- **详情路径**：ideas/missing-two.md
- **关键词**：测试
- **摘要**：同一 ID 再次出现。
"""
            (target / "index.md").write_text("# 知识索引\n\n" + duplicate, encoding="utf-8")
            result = run_cli(str(VALIDATOR), str(target))
            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("duplicate index ID", output)
            self.assertIn("missing detail file", output)

    def test_v2_detail_record_with_index_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self.make_knowledge(target)
            detail = target / "ideas" / "IA-20261102-01.md"
            detail.write_text(
                """\
## IA-20261102-01 — 阅读回看

- **日期**：2026-11-02
- **主题**：阅读体验
- **创意名称**：阅读回看
- **核心构想**：每次阅读后只留下一个可再次使用的问题。
- **来源**：用户测试输入；创意假设。
- **推导逻辑**：把阅读记录从收藏改为下一次行动的入口。
- **评分**：N6 R7 V7 F8 E6；7.0；置信度中；无关联警告。
- **当前状态**：待验证
- **去重键**：reading-next-question
- **当前版本**：1
- **版本历史**：`1 | 2026-11-02 | 创建 | 初始版本`
""",
                encoding="utf-8",
            )
            (target / "index.md").write_text(
                """\
# 知识索引

## IA-20261102-01 — 阅读回看

- **类型**：创意
- **详情路径**：ideas/IA-20261102-01.md
- **关键词**：阅读、回看、问题
- **摘要**：每次阅读后留下一个可再次使用的问题。
""",
                encoding="utf-8",
            )
            result = run_cli(str(VALIDATOR), str(target))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_v2_detail_missing_version_history_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self.make_knowledge(target)
            detail = target / "ideas" / "IA-20261102-01.md"
            detail.write_text(
                """\
## IA-20261102-01 — 缺少历史

- **日期**：2026-11-02
- **主题**：阅读体验
- **创意名称**：缺少历史
- **核心构想**：测试版本字段门禁。
- **来源**：测试。
- **推导逻辑**：测试。
- **评分**：N1 R1 V1 F1 E1。
- **当前状态**：待验证
- **去重键**：missing-history
- **当前版本**：1
""",
                encoding="utf-8",
            )
            (target / "index.md").write_text(
                """\
# 知识索引

## IA-20261102-01 — 缺少历史

- **类型**：创意
- **详情路径**：ideas/IA-20261102-01.md
- **关键词**：测试
- **摘要**：缺少版本历史。
""",
                encoding="utf-8",
            )
            result = run_cli(str(VALIDATOR), str(target))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required field 版本历史", result.stdout + result.stderr)

    def test_legacy_fixture_remains_readable(self) -> None:
        legacy = ROOT / "tests" / "fixtures" / "phase3" / "base"
        result = run_cli(str(VALIDATOR), str(legacy))
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
