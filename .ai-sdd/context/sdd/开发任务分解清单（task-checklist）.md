<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 开发任务分解清单（Task Checklist）

> 用途：tasks.md 生成后，逐项检查确保任务可执行性与完整性。

---

## 零、On-Demand 上下文路由

| # | 检查项 | 依据 |
|---|--------|------|
| 0.1 | 已按 `context-index.yaml` 的 `stage/scope/load_policy/triggers` 完成 tasks 阶段上下文路由 | context-governance |
| 0.2 | 涉及数据库层、DDL、SQL、BO/DAO/Engine 的任务，已加载数据库设计规范和分层任务模板 | database-conventions / layered-task-template |
| 0.3 | 涉及 CSF/BSV/PSV/网关/serviceCode 的任务，已加载接口设计规范并标注复用/新增接口 | api-style-guide / API Registry |
| 0.4 | 涉及 PC/H5 页面、网关调用、签字页跳转或响应处理的任务，已加载前端通信协议规范 | frontend-gateway-protocol |
| 0.5 | 涉及 ET、Task、流程实例、前置/后置/参数补全或后台任务终态的任务，已加载 ET 后台调度组件编码指南和对应代码模式 | et-dispatch-guide / code-patterns |
| 0.6 | 涉及 design-playbooks 典型场景的任务，已加载对应 playbook，并把 AI 开发任务与人类配置任务分开 | design-playbooks |

## 一、任务粒度与可执行性

| # | 检查项 | 依据 |
|---|--------|------|
| 1.1 | 每个任务对应一个明确修改点或交付物，无模糊任务（"研究一下""看看怎么做"） | config.yaml tasks rules |
| 1.2 | 后端任务按分层维度拆分：数据库层、实体层、数据访问层、业务服务层、接口层，每层任务独立 | 分层任务模板 |
| 1.3 | 前端任务按功能模块拆分（路由/页面/组件/API 调用） | config.yaml tasks rules |
| 1.4 | 每个任务有明确的输入（依赖哪些上游产出）和输出（交付什么） | — |
| 1.5 | 任务粒度到类/方法级别，而非模块级别 | — |

## 二、分层完整性（后端）

| # | 检查项 | 依据 |
|---|--------|------|
| 2.1 | 涉及新增/修改数据表时，有独立的 DB 层任务（DDL/DML） | 分层任务模板 Phase 1 |
| 2.2 | 涉及新实体时，有 Entity/DTO 层任务 | Phase 2 |
| 2.3 | 涉及新查询时，有 DAO/Mapper 层任务 | Phase 3 |
| 2.4 | 业务逻辑编排在 Service/SV 层任务中 | Phase 4 |
| 2.5 | 新接口暴露有 REST/CSF 层任务 | Phase 5 |
| 2.6 | 涉及 DDL 时，已定义 .sql 落盘路径并明确复用共享 DB 配置文件 | Phase 1 |
| 2.7 | 涉及跨中心调用时，已确认目标 CSV 类在目标仓库中存在；不存在则已拆分 CSV 创建任务（接口 + 实现 + 服务注册） | api-style-guide §8.1A |
| 2.8 | 跨中心 CSF 调用的 serviceCode 中心编码与目标 CSV 所在仓库/中心一致，而非调用方中心 | api-style-guide §8.1A |

## 三、接口复用

| # | 检查项 | 依据 |
|---|--------|------|
| 3.1 | 已通过 API Registry MCP 查询可复用接口 | API Registry |
| 3.2 | 可复用接口已标注"复用已有接口：XXX.methodName()" | — |
| 3.3 | 新增 API 明确标注为"新增" | — |

## 四、测试覆盖

| # | 检查项 | 依据 |
|---|--------|------|
| 4.1 | 有测试任务覆盖主流程 | config.yaml tasks rules |
| 4.2 | 有测试任务覆盖业务规则校验（准入规则、字段约束等） | config.yaml tasks rules |
| 4.3 | 有测试任务覆盖异常路径（异常场景、边界条件） | config.yaml tasks rules |
| 4.4 | 有测试任务覆盖合规校验（安全/敏感数据处理） | config.yaml tasks rules |
| 4.5 | 涉及前端改动时，已补充 E2E 用例清单规范 | testing-strategy |
| 4.6 | 在用户未明确要求前，未自动新增 E2E 执行任务或自动化脚本任务 | config.yaml tasks rules |
| 4.7 | 涉及 DDL 的任务已包含"执行 SQL 前征询用户同意"与"集成测试前执行 DDL"约束 | config.yaml tasks rules |

## 五、依赖与模块归属

| # | 检查项 | 依据 |
|---|--------|------|
| 5.1 | 每个任务已确定归属模块 | system-structure-capability |
| 5.2 | 任务间依赖关系明确 | — |
| 5.3 | 跨模块调用已确认调用链路 | integration-map |

## 五-B、外部接口参数闭环

| # | 检查项 | 依据 |
|---|--------|------|
| 5B.1 | 涉及出站外部协议的编码任务，应逐字段说明入参取值来源（入参直传 / 后端生成 / 业务常量 / 上下文补全），并标注字段名（含原大小写）；避免只写"调 XxxService"而不列参数 | design-checklist §七-B |
| 5B.2 | 工作流/异步组件任务中的接口调用，建议列出"上下文补全子步骤"——需先查哪些数据（从 XxxServiceFactory / DAO / CenterClient 取业务字段），再拼装出站入参 | design-checklist §七-B |
| 5B.3 | 跨中心任务中，目标 serviceCode 对应的 CSF 接口+实现建议拆为独立子任务（或确认已存在），避免"apply 时再建" | api-style-guide §8.1A |
| 5B.4 | 涉及前端 UI 特殊组件（QR 码 / 图表 / 地图 / 富文本等）的任务，应标注：组件技术选型（使用哪个库） / HTML 挂载元素类型 / 引入方式（script 标签 / 模块引入）；避免只写"展示 XX"而无技术实现说明 | frontend-conventions |

## 六、代码现实校准

| # | 检查项 | 依据 |
|---|--------|------|
| 6.1 | 已使用技能 ai-pre-code-review 对任务做代码现实校准 | config.yaml tasks rules |
| 6.2 | 设计假设与实际代码结构一致，偏差已修正 | config.yaml tasks rules |

## 七、后台进程组件任务完整性检查（异步场景触发）

| # | 检查项 | 依据 |
|---|--------|------|
| 7.1 | design 已明确执行模式为"异步"，Phase 4-Task 有触发依据 | design 阶段 |
| 7.2 | 组件接口对应 ET 后台调度已有 SPI 约定（勿新造接口风格） | et-dispatch-guide |
| 7.3 | 幂等检查明确落在方法体首行，并指出依赖的状态字段 | 分层任务模板 Phase 4-Task |
| 7.4 | 事务边界独立于 BSV-ServiceImpl（说明是否开独立事务或无事务） | 分层任务模板 Phase 4-Task |
| 7.5 | 单元测试覆盖"首次执行"、"幂等重入"、"异常失败"三条路径 | 分层任务模板 Phase 4-Task |
| 7.6 | Phase 4-Task 后已追加 ET 后台调度组件配置任务（人类配置） | config.yaml tasks rules |
| 7.7 | task 组件未调用 PSV 或前端相关接口 | 分层任务模板 Phase 4-Task |

## 八、测试与验证资产统一目录

| # | 检查项 | 依据 |
|---|--------|------|
| 8.1 | DDL/E2E/DB 配置产物落到 change 级目录（不带 `{repo}`） | project-profile paths |
| 8.2 | 测试源码、仓库级测试用例、测试数据、runner、报告落到 repo 级目录（带 `{repo}`） | project-profile paths |
| 8.3 | 未默认写入业务仓库内的 `test/sql/`、`test/report/` 或前端仓库 `docs/testing/e2e/`，统一使用 project-profile 声明的制品路径 | project-profile paths |
| 8.4 | tasks 中明确每类产物是 change 级还是 repo 级 | config.yaml tasks rules |

## 九、Design 双向追踪与偏差检查

| # | 检查项 | 依据 |
|---|--------|------|
| 9.1 | 已从 `design.md` 生成 Design Trace Matrix，将接口、方法、DAO、实体、表字段、路由、页面、外部接口、人类配置、测试要求和待确认项拆成原子 trace | ai-tasks-change |
| 9.2 | 每个需要实现、验证、配置或测试的 trace 都至少被一个 task 的 `Trace:` 字段覆盖 | design/tasks traceability |
| 9.3 | 每个 task 都能反向追溯到一个或多个 trace；无 design 来源的业务任务已删除或改为待确认 | design/tasks traceability |
| 9.4 | task 的操作类型与 trace 一致：新增/修改、复用验证、人类配置、测试、非编码、待确认没有混用 | design consistency |
| 9.5 | task 所在 Phase、实施仓库/center、调用链与 trace 的 layer/phase、repo/center 一致 | design consistency |
| 9.6 | task 中的方法签名、类名、表名、字段名、路由、页面组件名与 trace target 一致；不确定项已标 `TODO: 待确认` | design consistency |
| 9.7 | design 中 `deferred` / 待确认项没有被 tasks 写成确定性实现任务 | design-governance |
| 9.8 | design 中 `action=none` 的非编码说明没有被 tasks 转成实现任务 | design-governance |
| 9.9 | 人类配置 trace 只生成配置提醒与联调验证任务，未生成配置 SQL、配置模板或配置表字段说明 | config.yaml tasks rules |
| 9.10 | Design Drift Report 中 HIGH/MEDIUM 偏差为 0；LOW 偏差已补齐引用或记录原因 | ai-tasks-change |
| 9.11 | 对 design.md 中每个 mermaid 流程图，逐节点核对是否有对应 task 覆盖；PSV/前端编排类 task 的编排步骤列表须与流程图节点序列逐一对应，不允许流程图中有节点而 task 中跳过 | design/tasks completeness |
| 9.12 | 本 change 中新增的 CSF serviceCode，必须同时出现在"被调用方 task"（CSF 接口+实现创建）和"调用方 task"（PSV/BSV 编排引用），不允许任一侧缺失 | api-style-guide §8.1A |
