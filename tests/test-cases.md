# V2.0 行为测试

## 测试边界

- 自动化部分验证：模式路由 CLI、Skill 包结构、知识索引与详情校验、旧公共接口兼容。
- 文本部分验证：规则是否完整覆盖六个指定输入的预期行为。
- 这些测试不等同于独立用户研究、真实实验或另一模型的无偏差评审。

## 六组指定输入

| ID | 输入 | 预期任务与模式 | 必须观察 |
|---|---|---|---|
| TEST_01 | 如何提高长期学习动力？ | 灵感挖掘；QUICK 或 STANDARD | 输出简洁、差异方向、至少一个可执行验证动作 |
| TEST_02 | 将咖啡馆和知识管理联系起来。 | 跨界探索；STANDARD | 定义一致、共同机制、迁移条件、失效边界、差异候选 |
| TEST_03 | 解释第一性原理如何应用于产品设计。 | 知识考古；STANDARD | 工作定义、应用步骤、滥用边界、实际例子 |
| TEST_04 | 评审一个自动整理阅读资料并生成知识图谱的应用创意。 | 创意评审；STANDARD | 原方案评价、风险、替代方案、可行性收窄 |
| TEST_05 | 回顾过去的探索，并提出知识更新建议。 | 灵感复盘 | 只读取真实记录；无数据时停止趋势推断 |
| TEST_06 | 给我三个改善日常阅读体验的简单创意。 | 灵感挖掘；QUICK | 直接给 3 个左右简单方向，不输出完整评分 |

## 负向场景

| 场景 | 必须拒绝 |
|---|---|
| 无来源却要求“论文证明” | 编造文献、统计或精确引文 |
| 一条点赞后要求永久偏好 | 将单次信号升级为正式偏好 |
| 只靠名称相似的两个概念 | 把文字巧合包装成高价值关联 |
| 无索引命中的历史复盘 | 虚构历史、认可率或趋势 |
| 重复去重键的新创意 | 静默新增第二条记录 |
| 未授权写入知识 | 声称已保存或已修改偏好 |

## 执行命令

```text
python -m unittest tests.test_v2 -v
python scripts/validate.py --skill .
python scripts/validate.py knowledge
python scripts/validate.py tests/fixtures/phase3/base
python scripts/validate.py tests/fixtures/phase3/after
python scripts/validate.py tests/fixtures/phase3/duplicate
python scripts/validate.py tests/fixtures/phase3/unauthorized
```
