# IDEA ARCHAEOLOGIST V2.0

IDEA ARCHAEOLOGIST（灵感考古学家）是一个可安装的 Codex Agent Skill，用于从已有知识和跨领域线索中生成、审查并沉淀有推导依据的创意。

V2.0 采用渐进式加载：入口保留路由、模式、质量底线和输出契约；方法论、生成模型、评分、交互和知识协议只在实际需要时读取。

## 当前结构

```text
idea-archaeologist/
├── SKILL.md                 V2 progressive entry
├── README.md                Development and installation guide
├── agents/openai.yaml
├── references/
│   ├── methodology.md
│   ├── thinking-models.md
│   ├── scoring-rules.md
│   ├── interaction-rules.md
│   └── memory-protocol.md
├── knowledge/
│   ├── index.md
│   ├── ideas/
│   ├── connections/
│   ├── preferences.md
│   └── evolution.md
├── assets/templates/
├── scripts/
│   ├── route_mode.py
│   └── validate.py
├── tests/
└── CHANGELOG.md
```

`knowledge/`、`tests/` 和 `CHANGELOG.md` 支持维护本项目，但不是 Codex 加载 Skill 所必需的入口文件。

## 安装

Codex 可从用户级 `.codex/skills`、项目级 `.codex/skills`，或跨运行时兼容的 `.agents/skills` 发现本地 Skill。

### 项目级

将本目录放在项目或代码工作区的以下位置：

```text
<project>/.codex/skills/idea-archaeologist/
```

当前 `idea-archaeologist/` 目录就是可安装的源目录；需要启用时，将其复制到目标项目的 `.codex/skills/idea-archaeologist/`。若目标运行时使用跨运行时别名，也可放入 `.agents/skills/`。

### 用户级

若希望所有项目都能使用，将整个 `idea-archaeologist/` 目录复制到：

```text
~/.codex/skills/idea-archaeologist/
```

Windows 下通常对应：

```text
C:\Users\<用户名>\.codex\skills\idea-archaeologist\
```

Codex 会自动检测新增或修改的 Skill；如果没有出现，重启 Codex。

## 使用

- 在 Codex CLI 或 IDE extension 中运行 `/skills` 查看可用 Skills，或输入 `$idea-archaeologist` 明确调用。
- 在 ChatGPT/Codex 桌面应用中，从 Skills 界面查看并使用已发现的 Skill。
- Skill 的 `description` 已描述灵感挖掘、跨界探索、问题突破、知识考古、创意评审和灵感复盘，因此也支持明确的隐式匹配。

第一次可以尝试：

```text
用 $idea-archaeologist 深度探索这个问题，并给出可逆的最小验证：如何让远程团队把零散讨论沉淀为可用于决策的知识？
```

## 按需资源

- 方法、生成、评分、交互与记忆模块：[references](references)
- 输出模板：[assets/templates](assets/templates)
- 模式路由：[scripts/route_mode.py](scripts/route_mode.py)
- 包与知识验证器：[scripts/validate.py](scripts/validate.py)
- V2.0 完整交付报告：[V2-REPORT.md](V2-REPORT.md)

运行验证：

```text
python scripts/route_mode.py --text "给我三个改善阅读体验的简单创意"
python scripts/validate.py --skill .
python scripts/validate.py knowledge
python -m unittest tests.test_v2 -v
```

需要 Python 3.10 或更高版本，无第三方依赖。

## 知识数据

`knowledge/index.md` 只保存关键词、主题、摘要与详情路径。创意和关联详情独立存放在 `ideas/`、`connections/`；反馈、偏好和版本继续保存在 `preferences.md`、`evolution.md`。未经用户要求，Skill 不会自动写入。

需要分享给他人或在多个环境中分发时，当前官方文档建议将 Skill 打包为插件。直接复制 Skill 文件夹适合本地或项目内安装。

## 官方依据

- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Codex documentation](https://developers.openai.com/codex/)
- [Build plugins](https://developers.openai.com/plugins/build/plugins)
