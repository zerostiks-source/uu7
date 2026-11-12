# 论文 AI 率降低工具 — AI 助手简要指引（CLAUDE.md）

## 工作区仓库

| 目录 | 说明 |
|------|------|
| `./` | 全栈（Python/Vue，frontend-pc+PSV+BSV） |
| `.ai-sdd/context/` | SDD 上下文文档 |
| `openspec/` | OpenSpec 制品 |

## SDD 上下文加载

处理 SDD / OpenSpec / 需求分析 / 设计 / 编码任务时，**以 `.ai-sdd/context/context-index.yaml` 为上下文入口**：按当前阶段（stage）、scope 筛选条目，再按 `load_policy` 最小加载（`always` 与匹配的 `stage-start` 优先读取）。

> 无 aispec 工作流不使用 `aispec MCP resolve_context`。若工作区另行部署了独立上下文检索 MCP，可优先调用其 `resolve_context`（传入任务、stage、scope、change_name、`budget_tokens=4000`），证据不足时再按 `context://...` URI 渐进读取，不可用时回退本文件加载方式。

- `stage-start`：进入匹配阶段时读取。
- `stage-end`：阶段产物完成后读取并自检。
- `on-demand`：当前问题、业务场景、技术层次、产物类型、候选探索、证据需求或仓库落点明确命中时才读取。
- 目录型 `on-demand` 上下文触发后只先读取 README/索引文件，再按 README、候选项或证据需求读取具体文件；不得全量展开目录。
- `scope: all` 仅表示适用于所有 scope，不表示始终加载。
- 目录型上下文先读 README.md，再按 README 和当前问题读取具体文件。

## GitNexus — 核心规则

**MUST** 所有 GitNexus 工具调用必须指定 `repo` 参数：

- 论文 AI 率降低工具（全栈） → `repo: "ai-rate-reducer"`

## 常用指令

```bash
# 查找概念
gitnexus_query({query: "业务关键词", repo: "<repo>"})

# 查看符号
gitnexus_context({name: "ClassName", repo: "<repo>"})

# 编辑前评估影响
gitnexus_impact({target: "symbolName", direction: "upstream", repo: "<repo>"})

# 提交前验证范围
gitnexus_detect_changes({repo: "<repo>"})
```

## Never Do

- NEVER 省略 `repo` 参数
- NEVER 不运行 `gitnexus_impact` 就编辑函数、类或方法
- NEVER 忽略 HIGH 或 CRITICAL 风险警告
