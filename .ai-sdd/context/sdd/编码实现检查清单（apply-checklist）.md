<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 编码实现检查清单（Apply Checklist）

> 用途：每个编码任务完成后，逐项检查确保代码质量与设计一致性。

---

## 零、On-Demand 上下文路由

| # | 检查项 | 依据 |
|---|--------|------|
| 0.1 | 编码前已按 `context-index.yaml` 的 `stage/scope/load_policy/triggers` 完成 apply 阶段上下文路由 | context-governance |
| 0.2 | 修改数据库、SQL、BO/DAO/Engine/AppFrame2 持久化时，已加载数据库设计规范并按其实现 | database-conventions |
| 0.3 | 修改 CSF/BSV/PSV/网关/serviceCode/接口契约时，已加载接口设计规范与具体 API 资料 | api-style-guide / api-drilldown |
| 0.4 | 修改 PC/H5 前端调用、网关通信、签字页跳转或响应处理时，已加载前端通信协议规范 | frontend-gateway-protocol |
| 0.5 | 修改 ET、Task、流程实例、前置/后置/参数补全或后台组件时，已加载 ET 指南和对应代码模式 | et-dispatch-guide / code-patterns |
| 0.6 | 实现命中 design-playbooks 中某类典型场景的扩展时，已加载对应 playbook，并确认代码没有偏离 playbook 的开发/配置边界 | design-playbooks |

## 一、设计一致性

| # | 检查项 | 依据 |
|---|--------|------|
| 1.1 | 代码实现与 design.md 中的技术方案一致，无偏离 | config.yaml apply rules |
| 1.2 | 实现范围与 tasks.md 中的当前任务一致，无越界实现 | config.yaml apply rules |
| 1.3 | 任何偏离设计的部分已记录并标注原因 | config.yaml apply rules |
| 1.4 | 实现中发现的设计缺陷已记录供评审 | config.yaml apply rules |

## 二、分层职责合规

| # | 检查项 | 依据 |
|---|--------|------|
| 2.1 | CSF/CSV 层仅做参数转换与委托（Map 裸类型入参），无业务逻辑 | core-layered-model / api-style-guide §2.1 |
| 2.2 | SV 层控制事务，DAO 层和 CSF 层不控制事务 | design-conventions |
| 2.3 | DAO 层仅负责单表 CRUD，无业务判断逻辑 | design-conventions |
| 2.4 | 业务规则检查位于 Service/SV 层 | core-layered-model |
| 2.5 | SV 层访问数据仅通过 DAO/BO（或等价 Repository）；无直接 SQL/JDBC、无绕过 DAO 直接调 Engine | design-conventions / database-conventions |
| 2.6 | 无跨微服务中心直接 import 对方业务包（共享基础库除外） | config.yaml apply rules |
| 2.7 | 跨中心协作路径仅为 CSF 调用或 design 明确的数据层互访路径，无其他绕行调用 | config.yaml apply rules |

## 三、接口复用与新增

| # | 检查项 | 依据 |
|---|--------|------|
| 3.1 | 服务调用优先复用已有能力接口，未重复实现同等功能 | config.yaml apply rules |
| 3.2 | 新增 API 已实现完整逻辑（无 TODO 占位），并标注为新 API | config.yaml apply rules |
| 3.3 | 不确定的接口契约已通过 GitNexus 调查确认，未凭推导编造 | config.yaml apply rules |
| 3.4 | 所有跨中心调用的 serviceCode 已通过源码或 GitNexus 验证目标 CSV 类和方法**实际存在**（禁止仅凭命名规则推导） | api-style-guide §8.1A |
| 3.5 | serviceCode 中心编码前缀与**目标 CSV 所在仓库/中心**一致，而非调用方中心 | api-style-guide §8.1A |
| 3.6 | 跨中心 CSF 调用的完整链路（serviceCode → CSVImpl → SV → DAO）已验证可达；链路缺失层已在 tasks 中补充或标记阻塞 | api-style-guide §8.1A |
| 3.7 | **调用外部系统接口（含平台接入组件 / 能力开放网关 / 通信服务总线 / 数据同步桥等任一形式，参见 api-style-guide §8）时，已对照 api-catalog 或接口文档逐字段组装请求参数，所有必填字段均已填入且来源明确**；不允许仅传入内部业务 ID 而缺失接口规范要求的业务字段（如协议要求填入的订单号 / 业务类型 / 业务流水 / 设备标识等，名称以接口文档为准） | api-catalog + config.yaml apply rules |
| 3.8 | **工作流/异步组件/ET 任务中调用接口时**，参数来源（从订单上下文、DAO 查询或入参传递）已明确标注；若当前上下文不包含某必填字段，须在 review-notes 中记录并标记 PENDING | bsv-coding-guide/分层编码规范 + et-dispatch-guide |
| 3.9 | **本仓库作为 CSF 接口接收外部入站调用时（INBOUND），读取入参 KEY 必须与外部规范字段名大小写/拼写完全一致，统一使用本仓库字段常量类（项目约定的 IConstants/UipConstants/业务常量类，具体名以项目编码规范为准）而非裸字符串字面量；必填字段读取后须立即判空，缺失时按项目异常工具抛出业务异常或回 ACK-NAK，禁止 null 静默灌进下游** | design INBOUND 节 / contracts.md INBOUND 字段映射 |
| 3.10 | **实现命中设计手册中某类典型场景（如规则引擎/规则中心、出账、工作流等）时，必须按设计手册指定的"业务方接入模式"（入参结构/调用路径/返回值解析）实现**；禁止直接调用设计手册中仅供框架/引擎内部使用的方法；入参须含设计手册要求的外层结构，返回值须按设计手册的标准响应格式解析；与设计手册接入模式不符的实现须记录到 review-notes | design-playbooks / code-patterns |

## 四、编码规范

| # | 检查项 | 依据 |
|---|--------|------|
| 4.1 | 命名遵循项目编码规范 | coding-conventions |
| 4.2 | 枚举值使用已有字典中的枚举，未自行编造 | config.yaml apply rules |
| 4.3 | 异常处理遵循业务异常/系统异常/参数异常分类体系 | design-conventions |
| 4.4 | 无基本语法与类型错误 | config.yaml apply rules |
| 4.5 | 所有 import 位于文件头；无函数/方法体内临时 import（框架强制场景除外，需记录） | config.yaml apply rules |
| 4.6 | 无通配符 import（`*`）且无未使用 import | config.yaml apply rules |
| 4.7 | 业务编码/枚举/serviceCode/MQ/topic/tag/模板 ID 等无散落硬编码；必要硬编码已集中并记录替换计划 | config.yaml apply rules |
| 4.8 | **所有 SV/DAO 实例通过 `ServiceFactory.getService(Interface.class)` 获取（具体工厂 API 以目标框架分层编码规范为准）；代码中无 `new XxxSVImpl()` 或 `new XxxDAOImpl()` 用法**（包括同模块内 SV 互调、CSV 调 SV、SV 调 DAO 等全部场景） | bsv-coding-guide/分层编码规范 §四 |

## 五、GitNexus 强制步骤

| # | 检查项 | 依据 |
|---|--------|------|
| 5.1 | 编辑现有符号前已执行 `gitnexus_impact`（指定正确 repo） | config.yaml apply rules |
| 5.2 | HIGH/CRITICAL 风险已向用户警告 | AGENTS.md GitNexus rules |
| 5.3 | 实现完成后已执行 `gitnexus_detect_changes` 验证变更范围 | config.yaml apply rules |
| 5.4 | 所有 d=1（WILL BREAK）依赖者已更新 | AGENTS.md impact risk levels |

## 六、记录与评审

| # | 检查项 | 依据 |
|---|--------|------|
| 6.1 | 所有偏离设计的记录与评审项已写入独立文件 | config.yaml apply rules |
| 6.2 | 编码结束后已提示用户查看记录 | config.yaml apply rules |

## 七、DDL 执行门禁（仅涉及 DDL 场景）

| # | 检查项 | 依据 |
|---|--------|------|
| 7.1 | DDL `.sql` 已落盘到 `paths.ddl_directory`（`.ai-sdd/artifacts/changes/{change-name}/sql/`） | config.yaml apply rules |
| 7.2 | 已读取 `paths.db_config_location` 下共享 DB 配置 | config.yaml apply rules |
| 7.3 | 执行 SQL 前已征得用户明确同意 | config.yaml apply rules |
| 7.4 | DDL 已在集成测试启动前执行 | config.yaml apply rules |

## 七-B、测试资产路径检查

| # | 检查项 | 依据 |
|---|--------|------|
| 7B.1 | 测试源码落盘到 `paths.test_source_directory`（repo 级），未写入仓库原生测试目录（除非明确要求沉淀） | project-profile paths |
| 7B.2 | 测试报告落盘到 `paths.test_report_directory`（repo 级） | project-profile paths |
| 7B.3 | E2E 用例落盘到 `paths.e2e_directory`（change 级），未写入前端仓库 `docs/testing/e2e/` | project-profile paths |
| 7B.4 | 测试 runner 脚本声明了目标仓库、模块、依赖和输出报告位置 | config.yaml tasks rules |

## 八、多 Agent 并行检查（仅并行编码场景适用）

| # | 检查项 | 依据 |
|---|--------|------|
| 8.1 | 本 agent 未越界实现其他 Phase 的任务 | agent mode 职责定义 |
| 8.2 | 未修改 contracts.md 和 design.md（共享只读） | config.yaml apply 并行规则 |
| 8.3 | 偏离设计项和契约调整需求已记录到本 agent 的 review-notes 文件 | config.yaml apply 并行规则 |
| 8.4 | API 路径/参数名/响应字段与 contracts.md 完全一致 | 契约一致性 |
| 8.5 | 未直接修改其他 agent 负责层的代码文件 | agent mode 工作目录限制 |
