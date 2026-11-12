<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 分层任务模板（Layered Task Template）

> 用途：OpenSpec tasks 阶段，后端任务按此模板分层拆分。
> 后端分为两条栈：**BSV（业务服务层）** 和 **PSV（页面服务层）**，各自独立分层。
> 前端任务按功能模块拆分（路由/页面/组件/API 调用），不套用此模板。

---

## 架构总览

```
PSV 栈（页面服务层仓库）               BSV 栈（业务服务层/业务中心仓库）
┌───────────────────────────────┐       ┌───────────────────────────────┐
│ Phase 7: PSV-CSF/adapter      │       │ Phase 5: BSV-CSF/adapter      │
│ Phase 6: PSV-ServiceImpl      │──────▶│ Phase 4-Task: BSV-Task/ET [可选]│
└───────────────────────────────┘       │ Phase 4: BSV-ServiceImpl      │
                                        │ Phase 3: BSV-DAO              │
                                        │ Phase 2: BSV-BO/IValues       │
                                        │ Phase 1: BSV-DDL/DML          │
                                        └───────────────────────────────┘
```

> PSV 通过中台网关或 CSF RPC 调用 BSV-CSF/adapter 暴露的接口，完成业务能力编排。

---

## BSV 栈（业务服务层）

### Phase 1：BSV-数据库层（DDL/DML）

> 触发条件：涉及新增/修改表结构、字段、索引、初始数据时
> 适用仓库：按 `project-profile.yaml` 的 BSV/center 仓库选择。

**任务格式：**

```
任务 X.1：[新增/修改] 表 {TABLE_NAME}
- 操作类型：DDL / DML
- 变更内容：[具体字段/索引/约束描述]
- 约束：遵循 database-conventions（命名、主键、分表规则）
- SQL 文件：落盘到 paths.ddl_directory（.ai-sdd/artifacts/changes/{change-name}/sql/）
- DB 配置：复用 paths.db_config_location 下共享配置文件
- 执行门禁：执行 SQL 前必须先征询用户同意
- 验收标准：DDL 语句可执行，字段名与 data-model 一致
```

**检查要点：**
- 表名/字段名遵循项目域前缀与命名规范
- 主键、分表、枚举默认值符合项目约定
- DDL 脚本已落盘并可按共享配置执行

---

### Phase 2：BSV-实体层（BO/IValues）

> 触发条件：涉及新增/修改实体类或传输对象时
> 适用仓库：按 `project-profile.yaml` 的 BSV/center 仓库选择。

**任务格式：**

```
任务 X.2：[新增/修改] 实体 {EntityName}
- 涉及文件：{仓库名}/src/main/java/{包路径}/{EntityName}.java
- 变更内容：[字段、注解、关联关系描述]
- 依赖：Phase 1 的表结构
- 验收标准：实体字段与表结构一一对应，类型正确
```

**检查要点：**
- 实体字段与 DDL 表结构一致
- DTO 与实体的映射关系明确
- 命名遵循项目编码规范

---

### Phase 3：BSV-数据访问层（DAO）

> 触发条件：涉及新增/修改数据查询或持久化操作时
> 适用仓库：按 `project-profile.yaml` 的 BSV/center 仓库选择。

**任务格式：**

```
任务 X.3：[新增/修改] DAO {DaoName}
- 涉及文件：{仓库名}/src/main/java/{包路径}/{DaoName}.java
- 方法签名：[具体方法及参数]
- 依赖：Phase 2 的实体定义
- 验收标准：DAO 仅负责单表 CRUD，无业务判断逻辑
```

**检查要点：**
- DAO 方法仅封装查询/持久化，不包含业务逻辑
- SQL 映射（MyBatis XML 或注解）与实体字段匹配
- 参考 core-layered-model 的数据访问层章节

---

### Phase 4：BSV-业务服务层（ServiceImpl）

> 触发条件：涉及业务逻辑编排、事务控制时
> 适用仓库：按 `project-profile.yaml` 的 BSV/center 仓库选择。

**任务格式：**

```
任务 X.4：[新增/修改] SV {ServiceName}
- 涉及文件：{仓库名}/src/main/java/{包路径}/{ServiceName}.java
- 方法签名：[具体方法及参数]
- 业务逻辑：[编排描述]
- 事务控制：在 SV 层定义事务边界
- 依赖：Phase 3 的 DAO 接口
- 验收标准：业务规则完整实现，事务边界正确
```

**检查要点：**
- SV 层承担事务控制与业务逻辑编排
- 业务规则检查位于此层
- 调用 DAO 层完成数据访问，不直接操作 SQL
- 可复用接口已通过 API Registry MCP 确认

---

### Phase 4-Task：BSV-后台进程组件层（BSV-Task/ET）[可选]

> **触发条件**：design 判定执行模式为"异步后台任务"时激活；同步流程跳过此 Phase。
> 适用仓库：按业务归属 center 选择（以 project-profile 中的 center 映射为准）。

**任务格式：**

```
任务 X.4T：实现 {ComponentName} 后台组件
- 实现接口：{ET 框架 SPI 接口名}（须先加载 `ET后台调度组件编码指南（et-dispatch-guide）.md` 并调研真实代码确认约定）
- 幂等检查：方法体首行，检查业务单据/任务状态字段，防重复执行
- 业务委托：调用 Phase 4（BSV-ServiceImpl）或 Phase 5（BSV-CSF adapter）实现实际业务
- 状态回写：成功后更新业务单据/任务状态（调用 DAO 或已有 SV）
- 失败处理：显式声明失败策略（fail-closed / 告警 / 重试次数上限）
- 事务说明：独立事务边界，与 BSV-ServiceImpl 解耦
- 验收：单元测试覆盖正常路径、幂等重入路径、失败路径
```

**检查要点：**
- 组件只调用 BSV-CSF 层或 BSV-ServiceImpl，禁止跨层调用 PSV 或前端相关接口。
- 幂等检查落在方法体第一行，不得滞后。
- 事务边界独立于 Phase 4 的 BSV-ServiceImpl。
- Phase 4-Task 后必须追加 ET 后台调度组件配置任务（人类配置，参见 config.yaml tasks rules）。

---

### Phase 5：BSV-对外接口层（CSF/adapter）

> 触发条件：涉及对外暴露 BSV 层 API 接口时
> 适用仓库：按 `project-profile.yaml` 的 BSV/center 仓库选择。

**任务格式：**

```
任务 X.5：[新增/修改] CSF 接口 {InterfaceName}
- 涉及文件：{仓库名}/src/main/java/{包路径}/{InterfaceName}.java
- 方法签名：[具体方法及参数]
- 入参/出参：[参数结构描述]
- 依赖：Phase 4 的 SV 服务
- 验收标准：CSF 层仅做参数转换与委托，不包含业务逻辑
```

**检查要点：**
- CSF 接口仅做参数转换与委托调用 SV 层
- 接口命名与包结构遵循 CSF 规范
- 入参/出参与页面服务层或前端约定匹配

---

## PSV 栈（页面服务层）

### Phase 6：PSV-业务服务层（ServiceImpl）

> 触发条件：涉及页面服务层的业务逻辑编排，调用后端 BSV-CSF 接口实现具体业务能力
> 适用仓库：按 `project-profile.yaml` 的 PSV/BFF 页面服务层仓库选择。

**任务格式：**

```
任务 X.6：[新增/修改] PSV Service {ServiceName}
- 涉及文件：{repo}/src/main/java/{包路径}/{ServiceName}.java
- 方法签名：[具体方法及参数]
- 业务逻辑：[编排描述——聚合多个 BSV 网关调用、数据转换、异常处理]
- 调用的 BSV 接口：[列出本方法调用的 BSV-CSF 接口及其 serviceCode / 网关编码]
- 依赖：Phase 5 的 BSV-CSF 接口（或已有 BSV 接口）
- 验收标准：编排逻辑正确，网关调用参数与 BSV 接口契约匹配
```

**检查要点：**
- PSV-ServiceImpl 聚合多个 BSV 网关调用，执行页面级业务逻辑
- 不直接操作数据库，所有数据能力通过 BSV-CSF 获取
- 数据转换和组装在此层完成
- 遵循 BFF 页面服务层编码指南

---

### Phase 7：PSV-对外接口层（CSF/adapter）

> 触发条件：涉及页面服务层对前端应用暴露服务接口时
> 适用仓库：按 `project-profile.yaml` 的 PSV/BFF 页面服务层仓库选择。

**任务格式：**

```
任务 X.7：[新增/修改] CSV 接口 {InterfaceName}
- 涉及文件：{repo}/src/main/java/{包路径}/{InterfaceName}.java
- 方法签名：[具体方法及参数]
- 入参/出参：[Input/Output POJO 结构描述]
- serviceCode：{中心名}_{接口名}_{方法名}
- 委托目标：Phase 6 的 PSV-ServiceImpl 方法
- 服务注册：csf.services.xml（所有环境目录同步）
- 依赖：Phase 6 的 PSV Service
- 验收标准：CSV 层仅做参数校验与委托，所有异常在此层捕获不外抛
```

**检查要点：**
- CSV 接口仅做参数校验、委托调用 PSV-Service、组装 Output
- 所有异常在 CSV 层捕获并包装为 Output 返回（参见编码规范异常处理模式）
- csf.services.xml 已在所有环境目录同步注册
- serviceCode 命名规则：`{中心名}_{接口名}_{方法名}`

---

## 测试与前端

### Phase 5.T-A / 7.T-A：Mock 单元测试（所有接口）

> 触发条件：编码完成后，为所有新增/修改的接口编写单元测试
> BSV 新增接口触发 5.T-A；PSV 新增接口触发 7.T-A

**任务格式：**

```
任务 X.T-A：单元测试 {TestClassName}
- 测试框架：JUnit + Mockito
- 涉及文件：paths.test_source_directory（.ai-sdd/artifacts/changes/{change-name}/test-sources/{repo}/unit/{TestClassName}.java）
- Mock 对象：Mapper、远程客户端、外部 Bean
- 覆盖范围：核心业务分支、参数校验、异常路径
- 报告路径：paths.test_report_directory（.ai-sdd/artifacts/changes/{change-name}/reports/{repo}/）
- 验收标准：测试通过，覆盖主流程与关键异常分支
```

**检查要点：**
- 测试案例根据变更内容动态生成
- 已有测试文件时仅追加/修改受影响的方法
- 每个测试方法注释标明目的与预期
- 形成闭环：生成 → 执行 → 修复 → 重测

---

### Phase 8：前端任务（如涉及）

> 前端任务不套用分层模板，按功能模块拆分

**任务格式：**

```
任务 X.8：[新增/修改] 前端页面/组件 {ComponentName}
- 涉及文件：{frontend_repo}/src/{path}
- 功能描述：[页面/组件/路由/API 调用]
- 对接后端接口：{PSV-CSF 接口的 serviceCode}
- 依赖：Phase 7 的 PSV-CSF 接口
- 验收标准：页面交互正确，与后端接口出入参匹配
```

**前端 E2E 用例清单模板要求（规范产物）**：

- 当变更包含前端页面/交互时，需补充 E2E 用例清单文档，统一落盘到 `paths.e2e_directory`（`.ai-sdd/artifacts/changes/{change-name}/e2e/`）。
- 用例字段至少包含：`ID`、`用例名称`、`前提条件`、`步骤`、`预期结果` 等可执行、可断言项。用例内标注涉及的前端仓库、后端中心、接口链路和数据准备。
- 步骤避免「检查是否正常」等不可判定描述。
- 当前默认约束：仅要求输出 E2E 用例规范与模板，不默认展开为 tasks，不默认生成自动化脚本。

---

## 使用说明

1. **非必须全部使用**：根据 design.md 的实际变更范围，选择涉及的 Phase 生成任务。例如仅修改 PSV 层时，跳过 BSV 的 Phase 1–5。
2. **每个 Phase 可有多个任务**：同一层涉及多个模块/接口时，拆分为独立任务。
3. **依赖关系**：BSV 栈内 Phase N 依赖 Phase N-1；PSV 栈的 Phase 6 依赖 BSV Phase 5（或已有 BSV 接口）；Phase 7 依赖 Phase 6。在 tasks.md 中标明依赖。
4. **跨栈依赖**：PSV 调用 BSV 的接口必须在 tasks 中注明对应的 BSV-CSF 接口及其来源（已有/本次新增）。
5. **测试任务**：在所有 Phase 之后，按 config.yaml tasks rules 添加测试任务（主流程 / 规则校验 / 异常路径 / 合规校验）。
