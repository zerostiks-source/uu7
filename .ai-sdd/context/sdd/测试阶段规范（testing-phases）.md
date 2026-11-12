<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 测试阶段规范（testing-phases）

> 本文档定义 OpenSpec apply 阶段中后端测试的子阶段规范。
> 由 `openspec/config.yaml` rules.tasks 引用，生成 tasks 时按此规范拆分测试任务。

---

## Phase 5.T-A：BSV Mock 单元测试（BSV 接口）

**触发条件**：BSV Phase 5（BSV-CSF/adapter）有新增/修改接口时
**测试框架**：JUnit + Mockito

**配置要求：**
- Mock 对象：Mapper、远程客户端、外部 Bean
- 使用 `@Mock` / `@InjectMocks` 注入依赖
- 测试类放置于 `paths.test_source_directory`（`.ai-sdd/artifacts/changes/{change-name}/test-sources/{repo}/unit/`）

**覆盖范围：**
- 核心业务分支（正常路径 + 条件分支）
- 参数校验（空值、非法值、边界值）
- 异常路径（业务异常、系统异常）

**执行流程：**
1. 根据变更内容生成测试案例
2. 已有测试文件时仅追加/修改受影响的方法
3. 每个测试方法注释标明目的与预期
4. 形成闭环：生成 → 执行 → 修复 → 重测

**产出物：**
- 测试用例文件：`paths.test_source_directory`（`.ai-sdd/artifacts/changes/{change-name}/test-sources/{repo}/unit/{TestClassName}.java`）
- 测试报告：`paths.test_report_directory`（`.ai-sdd/artifacts/changes/{change-name}/reports/{repo}/`）

---

## Phase 7.T-A：PSV Mock 单元测试（PSV 接口）

**触发条件**：PSV Phase 7（PSV-CSF/adapter）有新增/修改接口时
**测试框架**：JUnit + Mockito

**配置要求：**
- Mock 对象：BSV 网关调用（ServiceTool）、外部 HTTP 客户端、Redis 缓存
- 使用 `@Mock` / `@InjectMocks` 注入依赖
- 测试类放置于 `paths.test_source_directory`（`.ai-sdd/artifacts/changes/{change-name}/test-sources/{repo}/unit/`）

**覆盖范围：**
- PSV-ServiceImpl 的编排逻辑分支
- BSV 网关调用的返回值处理（正常 + 异常）
- PSV-CSF/adapter 的参数校验与异常捕获

**执行流程：**
1. 根据变更内容生成测试案例
2. 已有测试文件时仅追加/修改受影响的方法
3. 每个测试方法注释标明目的与预期
4. 形成闭环：生成 → 执行 → 修复 → 重测

**产出物：**
- 测试用例文件：`paths.test_source_directory`（`.ai-sdd/artifacts/changes/{change-name}/test-sources/{repo}/unit/{TestClassName}.java`）
- 测试报告：`paths.test_report_directory`（`.ai-sdd/artifacts/changes/{change-name}/reports/{repo}/`）

---

## 与分层任务模板的关系

- BSV 单元测试（5.T-A）对应分层任务模板中 BSV Phase 5 后的测试编号。
- PSV 单元测试（7.T-A）对应分层任务模板中 PSV Phase 7 后的测试编号。
- 具体脚本路径、报告目录以实际工程为准，在 tasks 中写清命令与产出物。
