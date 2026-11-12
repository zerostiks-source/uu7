# paper-ai-rate-reducer — Change 专属上下文

> 变更名：paper-ai-rate-reducer
> 创建日期：2026-10-23
> 需求来源：`.ai-sdd/requirements/paper-ai-rate-reducer/discover-2026-10-23.md`

---

## 一、文件清单

| 文件 | 承载内容 | 加载建议 |
|------|----------|----------|
| [补充设计约束（design-constraints）.md](./补充设计约束（design-constraints）.md) | 本 change 的架构/锁定/强度/长文/隐私设计约束 | design / tasks 阶段命中改写引擎、锁定机制、供应商适配时加载 |
| [补充需求澄清（requirements-clarification）.md](./补充需求澄清（requirements-clarification）.md) | 本 change 的目标用户、检测基准、格式、边界等澄清 | proposal / specs 阶段理解需求边界时加载 |

---

## 二、原型

| # | 原型内容 | 来源 | 说明 |
|---|---------|------|------|
| 1 | 主工作区三段式布局：左输入/上传、中检测评分、右改写结果 | 用户口述 | 顶部工具名与设置入口 |
| 2 | 改写前后对比视图（差异高亮，锁定项异色不可编辑） | 用户口述 | 便于用户核验改动 |

---

## 三、待确认项

| # | 问题 | 影响级别 |
|---|------|---------|
| 1 | 语义保持量化阈值 | 🟠 HIGH |
| 2 | 官方检测接口对接方与授权 | 🟠 HIGH |
| 3 | 长文本单次处理上限与成本预算 | 🟡 MEDIUM |
| 4 | 是否本地/浏览器端保存历史记录 | 🟡 MEDIUM |
