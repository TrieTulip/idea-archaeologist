# IDEA ARCHAEOLOGIST V2.0 交付报告

日期：2026-11-02

## 1. V1.0 与 V2.0 架构对比

| 层 | V1.0 / 0.4.0 | V2.0 |
|---|---|---|
| 入口 | 入口、九阶段、关联审查、评分和记忆规则集中 | 128 行渐进入口，只保留路由、模式、底线和输出契约 |
| 模式 | 快速/标准/完整混在方法论说明中 | QUICK / STANDARD / DEEP，含确定性路由脚本 |
| 方法论 | 单个大文件叠加评分、生成和记忆 | `methodology.md` 聚焦九阶段与转换条件 |
| 生成与评分 | 多处重复 | `thinking-models.md` 与 `scoring-rules.md` 分离 |
| 交互 | 主要写在入口 | `interaction-rules.md` 按需加载 |
| 知识 | `ideas.md`、`connections.md` 聚合文件 | `index.md` + `ideas/` + `connections/` 详情分离 |
| 验证 | 单一路径验证旧知识 | 包校验 + V2 索引校验 + 旧知识兼容 + 模式契约测试 |

## 2. 文件变更

### 主要新增

- `scripts/route_mode.py`
- `references/thinking-models.md`
- `references/scoring-rules.md`
- `references/interaction-rules.md`
- `knowledge/index.md`
- `knowledge/ideas/`
- `knowledge/connections/`
- `tests/test_v2.py`
- `V2-REPORT.md`

### 主要修改

- `SKILL.md`
- `references/methodology.md`
- `references/memory-protocol.md`
- `scripts/validate.py`
- `knowledge/preferences.md`
- `knowledge/evolution.md`
- `README.md`
- `CHANGELOG.md`
- `agents/openai.yaml`
- `assets/templates/`
- `tests/test-cases.md`
- `tests/expected-behaviors.md`
- `tests/quality-checklist.md`
- `tests/evaluation-results.md`

### 迁移与删除

- V0.4.0 入口、方法论、记忆协议和 Phase 2 测试保留在 `tests/archive/`。
- 旧空文件 `knowledge/ideas.md`、`knowledge/connections.md` 已由索引和目录结构替代。
- 旧 Phase 3 测试夹具保留，用于向后兼容回归。

## 3. Token 优化措施

- 入口从 7,779 字节/136 行降为 6,435 字节/128 行。
- QUICK 默认不加载 references。
- STANDARD 根据任务类型加载思维、评分、交互或记忆模块。
- DEEP 才加载完整参考组合。
- 知识检索先读索引摘要，再读命中的详情文件。
- 删除入口与参考文件之间的重复内容。
- 当前环境没有与目标模型一致的可靠 Token 计数器；只用字节、行数和加载路径说明体积变化。

## 4. 三种思考模式

- **QUICK**：低风险或明确要求简洁；1 个关键洞察、1–3 个方向，不强制评分。
- **STANDARD**：默认模式；完成必要的分析、跨域、假设、候选和审查，按需评分与实验。
- **DEEP**：明确深度或高复杂度决策；完整 ARCHAEOLOGY、候选比较、评分、反例、实验和历史检索。

用户明确指定的模式优先。模式不明确影响结果时直接按复杂度判断，不要求用户选择。

## 5. 知识检索架构

- `index.md` 保存 ID、类型、详情路径、关键词和摘要。
- 详细创意位于 `ideas/IA-YYYYMMDD-XX.md`。
- 详细关联位于 `connections/CN-YYYYMMDD-XX.md`。
- 反馈和偏好保存在 `preferences.md`，方法版本保存在 `evolution.md`。
- 验证器检查索引重复 ID、缺失详情、未索引详情、字段完整性、去重键、反馈引用、授权和版本历史。
- 写入前自动测试结构，但目标问题和核心机制的最终语义合并仍需 Agent/用户审查。

## 6. 测试结果

```text
python -m unittest tests.test_v2 -v
Ran 15 tests
OK
```

另外通过：

- `validate.py --skill .`
- `validate.py knowledge`
- 旧 base 与 after 夹具
- duplicate 夹具按预期以退出码 1 拒绝
- unauthorized 夹具按预期以退出码 1 拒绝
- 全部相对 Markdown 链接

RED 基线为初始 13 个测试中 12 个失败、1 个兼容性通过。最终 V2 测试扩展到 15 个并全部通过。

## 7. Token 消耗变化

无法获得与目标模型一致的准确 prompt/output Token 统计，因此不声明精确节省比例。

可复核替代指标：

- 入口减少 1,344 字节，约 -17.28%。
- V1 入口 + 方法论 + 记忆协议为 36,484 字节。
- V2 入口 + 五个参考模块为 22,880 字节。
- 如果 DEEP 任务确实加载全部模块，静态文件体积相对减少约 37.29%。
- QUICK 的 advantage 来自不加载 references，而不是删除必要质量门禁。

## 8. 质量提升与退化

### 提升

- 六组指定输入均有确定性模式断言。
- 知识库从平铺文件升级为索引优先结构。
- 索引重复 ID、缺失详情和缺失版本历史可自动拒绝。
- 模式选择不再每次依赖自然语言解释。

### 退化风险

- 路由脚本使用可解释关键词规则，复杂表达可能误判；用户显式选择始终优先。
- 拆分为更多文件增加维护成本，但降低默认上下文。
- 本次没有独立模型评估，因此不能证明所有复杂开放任务的实际推理质量无退化。

## 9. 当前技术限制

- 无准确 Token 计数和模型一致的时间统计。
- 测试主要是结构、路由和旧夹具回归；六组内容质量没有通过独立评审。
- 去重键与近标题检测不能替代机制级语义判断。
- 正式知识库没有真实用户创意、反馈或十次探索，因此没有生成趋势报告。

## 10. 下一阶段建议

1. 用同一模型分别加载 V1/V2，对六组输入做盲评并记录真实输入/输出 Token。
2. 收集至少 10 次真实探索和可追溯反馈，再校准默认模式阈值。
3. 为 V2 增加语义重复辅助检查，但保留人工确认。
4. 监测高频误路由表达，调整 `route_mode.py` 的可解释规则或增加显式旗标。
5. 对知识索引规模增长后的检索准确度和上下文成本做基准测试。
