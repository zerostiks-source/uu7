<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 上下文治理规则（context-governance）

> 用途：约束 Agent 如何加载、判断和使用 `.ai-sdd/context/`，避免把庞大资料库当成默认上下文。

## 核心原则

1. **最小加载**：先读 `context-index.yaml`，按 `stage`、`scope`、`load_policy` 筛选。目录型上下文触发后只先读 `README.md` 或索引，具体文件必须按场景、候选项、关键词或证据需求再加载。
2. **当前优先**：本轮用户说明和当前 change 制品优先于历史上下文。`changes/{change-name}/` 只在处理同名 change 时加载，不能跨 change 默认复用。
3. **事实要证据**：接口签名、字段、枚举、配置、组件 ID、路由、代码行为必须由 API Registry、GitNexus 或源码确认。playbook 和 code-pattern 只能证明设计方法和写法模式，不能单独证明具体事实存在。
4. **冲突要阻塞**：上下文、API 文档、源码或用户说明冲突时，必须记录冲突来源。影响实现落点、数据归属、接口契约、配置项的冲突，在确认前不得写成确定结论。
5. **资料库按需发现**：`api-drilldown`、`code-patterns`、数据字典、旧 change 上下文按任务类型、候选探索或证据需求加载。禁止阶段启动时全量展开大型目录。

## On-Demand 路由规则

`on-demand` 不是“想起来才读”，而是按当前问题、产物类型、技术落点和证据需求做强制路由。进入 `design/tasks/apply` 阶段时，先用 `context-index.yaml` 中每个条目的 `triggers` 做一次命中判断；阶段中新增了表、接口、ET、前端调用等内容时，立即重新路由。

路由步骤：

1. 先筛选当前 `stage` 与 `scope` 可用的上下文。
2. 对 `load_policy: always` 和匹配阶段的 `stage-start` 直接加载。
3. 对 `load_policy: on-demand`，只要当前问题、产物内容、候选探索或证据需求命中任一 `triggers`，就必须加载。
4. 目录型上下文命中后，只先读 `README.md` 或索引；再按 README、候选 API、代码模式、playbook 或证据需求读取具体文件。
5. `stage-end` checklist 自检时，必须确认是否有新增内容触发了未加载的 on-demand 上下文。

常见强制命中：

| 产物/问题中出现 | 必须路由到 |
| --- | --- |
| 表、字段、索引、DDL、SQL、DAO、BO、Engine、AppFrame2 持久化 | `engineering/数据库设计规范（database-conventions）.md`，必要时 `data/核心数据模型（data-model）/` |
| CSF、BSV、PSV、网关、serviceCode、接口入参/出参、跨中心调用 | `engineering/接口设计规范（api-style-guide）.md`，必要时 `system/api-drilldown/` 与 `system/系统接口目录（api-catalog）/` |
| PC/H5 页面调用、网关协议、Header、AES、签字页跳转、前端接口响应处理 | `engineering/前端通信协议规范（frontend-gateway-protocol）.md` |
| ET、Task、流程实例、后台调度、前置/后置/参数补全、幂等、任务终态 | `engineering/ET后台调度组件编码指南（et-dispatch-guide）.md` 与相关 `code-patterns` |
| 典型业务/技术场景（直接命中或子流程引用，以 design-playbooks 目录为准） | `system/设计手册（design-playbooks）/README.md`，再按命中模式读具体 playbook；主 playbook 的扩展点引用子 playbook 时，仅在涉及该扩展点时加载子 playbook |
| 需要实现具体 CSF/SV/DAO/BO/ET/前端/测试写法 | `system/代码模式（code-patterns）/README.md`，再按任务类型读具体代码模式 |
| 枚举、状态码、类型编码、场景码、业务编码、配置编码 | `data/枚举值字典（enum-dictionary）.md` 或 `api-drilldown` 枚举/接口资料 |
| 敏感信息、手机号、证件号、客户资料、日志脱敏、权限 | `security/安全与合规规范（security-rules）.md` |

如果命中多个上下文，按最小集合加载；但不得因为已加载 playbook 而跳过横向工程规范。playbook 说明“做什么”，工程规范约束“怎么做才合规”。

**Playbook 两级加载规则**：

1. 主 playbook 加载后，检查其扩展点/证据矩阵中是否引用了子 playbook。
2. 子 playbook 仅在当前场景涉及对应扩展点时才加载，不因被引用就默认全部加载；但子 playbook 也可独立命中。
3. 主、子 playbook 的“必须查证项”合并到同一份 `evidence-matrix.md`，按场景/扩展点分组并标注来源 playbook。

## 证据顺序

当多个来源给出不同结论时，按以下顺序处理：

1. 用户本轮明确说明、当前 change 的已确认 proposal/spec/design/tasks。
2. 源码精确读取、GitNexus `query/context/impact/detect_changes`、API Registry 详情。
3. 命中的 design playbook、code-patterns。
4. 系统架构、模块能力、数据归属、工程规范、安全规范等稳定上下文。
5. 历史资料、原始需求、未验证补充说明。

同一层级证据冲突时，不能自行选择；写入待确认项或交给用户决策。

## 必须查证的事实

- 接口签名、参数、返回值、serviceCode、网关映射。
- 表、字段、索引、枚举值、场景码、配置项、组件 ID。
- 方法路径、调用链、实现类、共享工具类方法签名。
- 中心归属、数据归属、跨中心调用路径。
- ET/后台任务链路、规则函数、前后端页面路径和 mock 映射。

## 与阶段规则的边界

本文只约束上下文如何加载、证据如何排序、冲突如何处理。OpenSpec 各阶段的产物格式、任务拆分、DDL/E2E/测试资产、apply 编码门禁等细则，见：

- `openspec/config.yaml`
- 各阶段 checklist/template 文档
