<!--
【文档说明】
承载内容：GitNexus repo 映射、impact/detect_changes、调试、重构和索引刷新约束。
适用范围：always/on-demand 上下文；设计、编码和验证阶段按 index 加载。
填充指引：由 ai-sdd-init 技能根据 project-profile.yaml → repositories[] 填写仓库与 repo 参数表；
          后续新增/删除仓库时由 ai-sdd-repo-add / ai-sdd-repo-del 技能同步更新。
-->
# GitNexus 使用规则（gitnexus-rules）

> 用途：承接根目录 `AGENTS.md` 中原有的 GitNexus 详细指令。`AGENTS.md` 只保留启动级硬规则；需要调研、调试、重构、提交自检或刷新索引时读取本文。

## 仓库与 repo 参数

| 仓库 | `repo` 参数值 | 说明 |
| --- | --- | --- |
| （待 ai-sdd-init 根据 project-profile.yaml → repositories[] 填充） | — | — |

## Always Do

- 所有 GitNexus 工具调用必须指定 `repo` 参数。
- 编辑任何函数、类、方法或共享符号前，必须运行 `gitnexus_impact({target: "...", direction: "upstream", repo: "..."})` 并报告影响范围。
- 完成变更后、提交前，必须运行 `gitnexus_detect_changes({repo: "..."})` 验证变更范围。
- 如果 impact 返回 HIGH 或 CRITICAL 风险，必须明确警告用户并处理 d=1 直接依赖者。
- 探索不熟悉代码时，先用 `gitnexus_query({query: "concept", repo: "..."})` 查执行流。
- 需要某个符号完整上下文时，使用 `gitnexus_context({name: "SymbolName", repo: "..."})`。

## Debugging

1. `gitnexus_query({query: "<error or symptom>", repo: "..."})` 查找相关执行流。
2. `gitnexus_context({name: "<suspect function>", repo: "..."})` 查看调用关系和流程参与。
3. 需要逐步追踪时读取 `gitnexus://repo/{repo}/process/{processName}`。
4. 回归问题使用 `gitnexus_detect_changes({scope: "compare", base_ref: "main", repo: "..."})` 查看分支变更。

## Refactoring

- 重命名必须先预览：`gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true, repo: "..."})`；确认后再 `dry_run: false`。
- 提取、拆分、移动共享逻辑前，先用 `gitnexus_context` 和 `gitnexus_impact` 了解引用关系。
- 完成后运行 `gitnexus_detect_changes({scope: "all", repo: "..."})` 验证范围。

## Never Do

- 不省略 `repo` 参数。
- 不跳过 impact 直接编辑函数、类或方法。
- 不忽略 HIGH 或 CRITICAL 风险。
- 不用文本查找替换做符号重命名；使用 `gitnexus_rename`。
- 不跳过 `gitnexus_detect_changes()` 就提交代码。

## 常用工具示例

| Tool | 用途 | 示例 |
| --- | --- | --- |
| `query` | 按概念查找执行流 | `gitnexus_query({query: "{业务关键词}", repo: "{repo}"})` |
| `context` | 查看符号全貌 | `gitnexus_context({name: "CustSVImpl", repo: "{repo}"})` |
| `impact` | 编辑前影响评估 | `gitnexus_impact({target: "X", direction: "upstream", repo: "{repo}"})` |
| `detect_changes` | 变更范围检查 | `gitnexus_detect_changes({scope: "all", repo: "{repo}"})` |
| `rename` | 安全重命名 | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true, repo: "{repo}"})` |
| `cypher` | 自定义图查询 | `gitnexus_cypher({query: "...", repo: "{repo}"})` |

## Impact 风险层级

| Depth | 含义 | 操作 |
| --- | --- | --- |
| d=1 | WILL BREAK：直接调用者/导入者 | 必须更新 |
| d=2 | LIKELY AFFECTED：间接依赖 | 应当测试 |
| d=3 | MAY NEED TESTING：传递依赖 | 关键路径需测试 |

## Resources

按需读取以下资源，不要在无明确问题时全量展开。`{repo}` 必须来自上方仓库表或 `project-profile.yaml`：

- `gitnexus://repo/{repo}/context`
- `gitnexus://repo/{repo}/clusters`
- `gitnexus://repo/{repo}/processes`
- `gitnexus://repo/{repo}/process/{name}`

## Finishing Self-Check

1. 所有修改的符号已运行 impact，且指定正确 `repo`。
2. 未忽略任何 HIGH/CRITICAL 风险。
3. `gitnexus_detect_changes({repo: "..."})` 已确认变更范围符合预期。
4. 所有 d=1 直接依赖者已更新或明确说明无需更新。

## Keeping Index Fresh

各仓库分别刷新索引。`{repo_dir}` 为仓库目录名，按 `project-profile.yaml` 的 repositories 列表逐个执行：

```bash
(cd {repo_dir} && npx gitnexus analyze)
```

检查 embeddings：查看对应 `.gitnexus/meta.json` 的 `stats.embeddings`。如需保留 embeddings，刷新时加 `--embeddings`。
