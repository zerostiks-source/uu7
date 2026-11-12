<!--
【文档说明】
承载内容：SDD/OpenSpec 工作流规则、阶段模板或检查清单，指导需求、设计、任务、实现和验证产物质量。
适用范围：按 context-index 对应 stage 加载；stage-end 检查清单用于阶段产物自检。
填充指引：由 SDD 方法论、项目实践复盘和 context-update 维护；保持规则可执行，避免写入单项目业务事实。
加载建议：进入对应阶段或执行阶段自检时加载；always 文档在任务启动时加载。
-->
# 多 Agent 并行编码规范（multi-agent-parallel）

> 本文档定义 OpenSpec apply 阶段中多 Agent 分层并行编码的规则。
> 由 `openspec/config.yaml` rules.apply 引用，仅在用户明确启动多 Agent 并行编码时生效。

---

## Agent 分工

| Agent | 负责范围 | Phase 范围 |
|-------|----------|-----------|
| backend-agent | BSV 栈全层（DDL/实体/DAO/ServiceImpl/CSF）+ PSV 栈（ServiceImpl/CSF）+ 测试 | BSV Phase 1–5, PSV Phase 6–7, T-A |
| frontend-h5-agent | H5 前端页面/组件/API 联调（Vue 2.x） | Phase 8（H5） |
| frontend-pc-agent | PC 前端页面/组件/API 联调（jQuery） | Phase 8（PC） |

## 启动前准备

- 必须从 design.md 提取 contracts.md（接口契约摘要），放入 change 目录，作为所有 agent 的共享只读制品。
- contracts.md 须包含：数据结构定义、BSV-DAO 接口签名、BSV-ServiceImpl 接口签名、BSV-CSF 接口签名、PSV-ServiceImpl 接口签名、PSV-CSF 接口签名、API 网关路由映射、跨栈复用接口清单

## 并行规则

- 各 agent 只处理本职责范围内的任务，严禁越界实现其他层的代码。
- contracts.md 和 design.md 在并行编码期间为只读，任何 agent 不得修改。需要调整契约时须暂停并行，由用户协调后统一更新。
- 各 agent 各自产出独立的 review-notes 文件（review-notes-backend.md / review-notes-frontend-h5.md / review-notes-frontend-pc.md），不共享写入。

## Fullstack 仓库并行约束

Fullstack 仓库（`repo-type: fullstack`）内同时包含 PSV/BSV/frontend 等多层代码。当不同 subagent 同时修改同一 fullstack 仓库的不同模块时，存在 git 冲突风险。

- **默认串行**：同一 fullstack 仓库内不同层（PSV/BSV/frontend）的任务，默认按层串行执行，避免并发写入同一 git 工作树。
- **有条件并行**：若确认各层代码位于完全独立的子目录中，且无共享文件（如根级 `pom.xml`、`package.json`、`build.gradle`、通用配置文件等），可允许并行执行。启用前须在 tasks 中明确标注隔离判定依据。
- **共享文件冲突**：并行时需特别注意共享构建文件（多模块 `pom.xml`、workspace `package.json`）和配置文件（`application.yml`、`.env`、路由配置等）的冲突风险。若任务涉及修改任何共享文件，必须回退为串行。

## 收尾合并

- 并行编码完成后，必须在单一 agent 会话中合并 review-notes、检查前后端契约一致性、统一执行 openspec-verify-change。
