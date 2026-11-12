<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 系统设计检查清单（Design Checklist）

> 用途：design.md 生成后，逐项检查确保方案完整性与合规性。

---

## 零、On-Demand 上下文路由

| # | 检查项 | 依据 |
|---|--------|------|
| 0.1 | 已按 `context-index.yaml` 的 `stage/scope/load_policy/triggers` 完成 design 阶段上下文路由 | context-governance |
| 0.2 | 若 design 涉及表、字段、索引、DDL、SQL、BO/DAO/Engine，已加载并按数据库设计规范校准 | database-conventions |
| 0.3 | 若 design 涉及 CSF/BSV/PSV/网关/serviceCode/接口出入参，已加载接口设计规范并查证可复用接口 | api-style-guide / API Registry |
| 0.4 | 若 design 涉及 PC/H5 调用、网关协议、签字页跳转或前端响应处理，已加载前端通信协议规范 | frontend-gateway-protocol |
| 0.5 | 若 design 涉及 ET、Task、流程实例、后台调度、前置/后置/参数补全，已加载 ET 后台调度组件编码指南 | et-dispatch-guide |
| 0.6 | 若 design 命中 design-playbooks 中的典型场景，已加载对应 playbook；若涉及具体写法，已加载 code-patterns | design-playbooks / code-patterns |

## 一、架构与分层合规

| # | 检查项 | 依据 |
|---|--------|------|
| 1.1 | 后端设计遵循五层分层架构（数据库层 → 实体层 → 数据访问层 → 业务服务层 → 接口层），各层职责无越界 | core-layered-model |
| 1.2 | CSF 接口层仅做参数转换与委托，不包含业务逻辑 | design-conventions |
| 1.3 | SV 层承担事务控制与业务逻辑编排，DAO 层仅负责单表 CRUD | design-conventions |
| 1.4 | 新增功能已根据功能类型确定实现位置 | core-layered-model |

## 二、接口设计

| # | 检查项 | 依据 |
|---|--------|------|
| 2.1 | 前端对应的后端接口已优先考虑复用/修改现有接口，避免轻易引入新接口 | config.yaml design rules |
| 2.2 | 已通过 API Registry MCP 工具查询 API 清单，确认可复用接口 | API Registry |
| 2.3 | CSF 接口命名与包结构遵循项目规范 | design-conventions |
| 2.4 | design.md 末尾列出本次 change 可重用的全部接口方法 | config.yaml design rules |

## 三、数据设计

| # | 检查项 | 依据 |
|---|--------|------|
| 3.1 | 涉及数据写入时已明确主数据归属和同步边界 | data-ownership |
| 3.2 | 表名/字段名/主键遵循数据库设计规范 | database-conventions |
| 3.3 | 使用已有枚举值字典中的枚举，未自行编造 | enum-dictionary |
| 3.4 | 涉及分表的表已遵循项目分片规则 | data-model 通用约定 |

## 四、前后端交互

| # | 检查项 | 依据 |
|---|--------|------|
| 4.1 | 前端通过 HTTP → API 网关 → CSF 的调用路径设计完整 | architecture-overview |
| 4.2 | 前端设计已标明涉及的页面/组件/路由 | — |
| 4.3 | 前后端接口出入参匹配，无遗漏字段 | — |
| 4.5 | 若 design 涉及外部系统异步回调（INBOUND）且前端需展示或轮询回调结果，已设计"入站→BSV 写 DB→PSV 查 DB→前端展示/轮询"的完整数据流，包括落表字段、写入规则和 BSV 查询接口；不可遗漏中间持久化层 | — |
| 4.6 | design 中的前端操作方式（手工按钮触发 / 自动轮询 / 页面加载触发）已与 specs 的 Requirement/Scenario 描述逐条对齐，未将用户主动操作泛化为系统被动行为（典型错误："系统查询到…则展示"替代"营业员点击查询后…展示"） | — |
| 4.7 | design.md mermaid 流程图中每个调用/系统动作节点，必须在对应层次（BSV/PSV/前端）的文字描述表或编排步骤中有对等条目；禁止流程图节点在文字描述中静默省略（典型错误：mermaid 有"enrollESim"节点，PSV 文字描述只写"设备校验→套餐过滤→轮询"跳过该步骤） | — |

## 五、安全与合规

| # | 检查项 | 依据 |
|---|--------|------|
| 5.1 | 敏感信息（证件号、手机号等）在界面展示时已模糊化处理 | security-rules |
| 5.2 | 遵循安全与合规规范中的数据安全要求 | security-rules |

## 六、异常处理与事务

| # | 检查项 | 依据 |
|---|--------|------|
| 6.1 | 事务边界在 SV 层定义，CSF 层和 DAO 层不控制事务 | design-conventions |
| 6.2 | 异常分类遵循业务异常 / 系统异常 / 参数异常三类体系 | — |
| 6.3 | 关键操作有回滚或补偿设计 | — |

## 七、后台任务层合规（异步场景触发）

| # | 检查项 | 依据 |
|---|--------|------|
| task-1 | 已明确执行模式（同步/异步），异步流程已设计 BSV-Task/ET 组件 | design 阶段 |
| task-2 | 同步业务未引入不必要的 task 组件（避免过度异步化） | design 阶段 |
| task-3 | task 组件幂等策略已明确（业务单据/任务状态判断字段与触发值） | design 阶段 |
| task-4 | task 组件调用链清晰：ET 调度框架 → 组件 → BSV-CSF，禁止跨层调用 PSV | design 阶段 |
| task-5 | task 组件失败处理策略已明确（重试/告警/跳过），并与 ET 后台调度配置动作分开 | design 阶段 |

## 八、待确认项

| # | 检查项 | 依据 |
|---|--------|------|
| 8.1 | 所有模糊需求已标注 "TODO: 待确认" | config.yaml design rules |
| 8.2 | 未确认的数据归属、规则优先级、异常处理、接口能力已显式列出 | config.yaml context |
| 8.3 | TODO 项建议附"查证操作指引"（GitNexus `context(name="X", repo="Y")` / api-catalog §Z / 参考 AAA.java:NNN / 找产品经理确认），避免只写"待确认"而无操作路径 | — |

## 七-B、外部接口数据流闭环（涉及出站外部协议时建议检）

> **适用范围**：出站调用非本仓库可控的下游协议（HTTP/PIP/SDK/MQ bridge/ESB/网关代发等任一形式）。
> 对每个出站接口，design.md 建议覆盖以下"五要素"中的相关项；无相关性的可标"N/A + 理由"。

| 要素 | 建议内容 | 参考反例（不期望的写法）|
|------|----------|------------------------|
| 字段来源属性 | 字段名 / 必填 / 来源（入参直传 \| 后端生成 \| 业务常量 \| 上下文补全） / 责任层 | "调用 XxxService" |
| 上下文补全路径 | 触发上下文持有的最小标识 / 需补查的字段 / 补查途径（查表 / 调 SV / CenterClient） | "工作流调下游接口" |
| 跨系统字段映射 | 源系统字段名 → 目标协议字段名（含大小写/类型差异/衍生字段） | "字段透传" |
| 跨模块部署约束 | 调用方式（CenterClient / ServiceFactory / OPF 路由） / 部署关系（同 WAR / 独立部署 / pom 依赖） | "调用目标中心" |
| TODO 查证操作指引 | 查 GitNexus `context(name="X", repo="Y")` / 查 api-catalog §Z / 参考 AAA.java:NNN / 找产品经理确认 | "TODO：待确认" |

## 九、设计偏离治理

| # | 检查项 | 依据 |
|---|--------|------|
| 9.1 | design 与 specs 的前端交互方式（过滤隐藏 vs 全部展示/拦截、手动触发 vs 自动触发等）若存在不一致，必须在 design.md Decisions 表中显式记录偏离决策（D-* ID / specs 原始定义 / design 修正值 / 修正依据）；不允许静默覆盖 specs 定义 | specs-to-design traceability |
| 9.2 | design 标记"命中 playbook XXX"时，具体实现方式（调用方式/入参结构/返回结构/新增类）必须与 playbook 的**业务方接入模式**骨架一致；禁止把 playbook 中"引擎内部机制"（仅限框架内部调用的方法/类）作为业务方实现方案（典型错误：将规则引擎内部入口函数作为业务方直接调用的 API） | design-playbooks |
