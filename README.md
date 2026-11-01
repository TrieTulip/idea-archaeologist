# IDEA ARCHAEOLOGIST

IDEA ARCHAEOLOGIST（灵感考古学家）是一个可安装的 Codex Agent Skill，用于从已有知识和跨领域线索中生成、审查并沉淀有推导依据的创意。

核心入口是带 YAML frontmatter 的 [SKILL.md](SKILL.md)。Codex 在发现阶段读取 `name` 和 `description`，选择该 Skill 后再加载完整说明；方法论、模板和验证脚本按需读取。

## 当前结构

```text
idea-archaeologist/
├── SKILL.md                 Required: metadata + core instructions
├── README.md                Development and installation guide
├── agents/
│   └── openai.yaml          Optional: display metadata and prompt
├── references/              Detailed methodology and memory protocol
├── assets/
│   └── templates/           Output templates used on demand
├── scripts/
│   └── validate.py          Read-only knowledge validator
├── knowledge/               Starter knowledge assets
├── tests/                   Behavioral tests and isolated fixtures
└── CHANGELOG.md             Version history
```

`knowledge/`、`tests/` 和 `CHANGELOG.md` 支持维护本项目，但不是 Codex 加载 Skill 所必需的入口文件。

## 安装

按照当前官方文档，Codex 从用户级或项目级 `.agents/skills` 目录发现本地 Skill。

### 项目级

将本目录放在项目或代码工作区的以下位置：

```text
<project>/.agents/skills/idea-archaeologist/
```

Codex 会从当前目录向上扫描项目内的 `.agents/skills`。当前 `idea-archaeologist/` 目录就是可安装的源目录；需要启用时，将其复制到目标项目的 `.agents/skills/idea-archaeologist/`。

### 用户级

若希望所有项目都能使用，将整个 `idea-archaeologist/` 目录复制到：

```text
~/.agents/skills/idea-archaeologist/
```

Windows 下通常对应：

```text
C:\Users\<用户名>\.agents\skills\idea-archaeologist\
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

- 完整流程和质量门槛：[references/methodology.md](references/methodology.md)
- 记忆、去重和版本协议：[references/memory-protocol.md](references/memory-protocol.md)
- 输出模板：[assets/templates](assets/templates)
- 知识资产验证器：[scripts/validate.py](scripts/validate.py)

运行验证器，只读检查知识资产：

```text
python scripts/validate.py knowledge
```

需要 Python 3.10 或更高版本，无第三方依赖。

## 知识数据

`knowledge/` 包含四类初始资产。未经用户要求，Skill 不会自动写入；Phase 2 测试候选和 Phase 3 夹具不会被当作真实用户历史。

需要分享给他人或在多个环境中分发时，当前官方文档建议将 Skill 打包为插件。直接复制 Skill 文件夹适合本地或项目内安装。

## 官方依据

- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Codex documentation](https://developers.openai.com/codex/)
- [Build plugins](https://developers.openai.com/plugins/build/plugins)
