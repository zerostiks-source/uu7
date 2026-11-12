# 工作区 Agent 指令

本文件只保留启动入口、仓库映射和不可违反的硬规则。OpenSpec 阶段规则集中在 `openspec/config.yaml`；GitNexus 操作手册、上下文治理规则、模板和检查清单按 `context-index.yaml` 加载。

## 仓库与路径

| 目录 | 说明 | GitNexus repo |
| --- | --- | --- |
| `./` | 论文 AI 率降低工具（fullstack frontend-pc+PSV+BSV，Vue） | `ai-rate-reducer` |
| `.ai-sdd/context/` | SDD 上下文文档 | - |
| `.ai-sdd/raw/` | 原始需求文档 | - |
| `.ai-sdd/requirements/` | 需求特定资料 | - |
| `openspec/` | OpenSpec 制品 | - |

代码路径必须带仓库前缀，例如 `./...`、`./...`。各代码仓库独立 git 管理；共享上下文、OpenSpec 制品和 Agent 指令在工作区根目录统一管理。

## SDD 上下文加载

处理需求、设计、任务、编码或验证前，**以 `.ai-sdd/context/context-index.yaml` 为上下文入口**，按 `stage`、`scope`、`load_policy` 最小加载上下文：

> 无 aispec 工作流不使用 `aispec MCP resolve_context`。若工作区另行部署了独立上下文检索 MCP，可优先调用其 `resolve_context`（传入任务、`stage`、`scope`、`change_name`、`budget_tokens=4000`），证据不足时再按返回的 `context://...` URI 渐进读取，不可用时回退下列加载方式。

- `always`：任务启动时读取。
- `stage-start`：进入匹配阶段时读取。
- `stage-end`：阶段产物完成后读取并自检。
- `on-demand`：当前问题、业务场景、技术层次、产物类型、候选探索、证据需求或仓库落点明确命中时读取。
- 目录型 `on-demand` 只先读 README/索引，再按 README、候选项或证据需求读取具体文件；禁止全量展开目录。
- `scope: all` 只表示适用于所有 scope，不表示始终加载。

上下文可信度、冲突处理和证据顺序见 `.ai-sdd/context/sdd/上下文治理规则（context-governance）.md`。

## OpenSpec

本项目使用 OpenSpec 进行规格驱动开发：proposal → specs → design → tasks → apply → verify → archive。

- 配置入口：`openspec/config.yaml`
- 变更制品：`openspec/changes/{change-name}/`
- 当前 change 专属上下文：仅在处理同名 change 时加载 `.ai-sdd/context/changes/{change-name}/README.md`

OpenSpec 阶段任务必须遵循 `openspec/config.yaml`、对应阶段 checklist/template，以及 context-index 命中的上下文。

## GitNexus 硬规则

- 所有 GitNexus 工具调用必须指定正确 `repo` 参数。
- 编辑任何函数、类、方法或共享符号前，必须运行 impact analysis 并报告影响范围。
- 完成变更后、提交前，必须运行 `gitnexus_detect_changes({repo: "..."})` 验证变更范围。
- impact 返回 HIGH 或 CRITICAL 风险时，必须警告用户并处理直接依赖者。
- 重命名必须使用 `gitnexus_rename`，禁止文本查找替换式重命名。

详细调试、重构、资源、示例和索引刷新规则见 `.ai-sdd/context/sdd/GitNexus使用规则（gitnexus-rules）.md`。

## Self-Check

完成代码或制品变更前确认：

1. 所有 GitNexus 调用都指定了正确 `repo`。
2. 修改现有符号前已运行 impact，且未忽略 HIGH/CRITICAL 风险。
3. 完成后已运行 detect_changes 验证范围。
4. SDD/OpenSpec 产物已按 `stage-end` checklist 自检。
