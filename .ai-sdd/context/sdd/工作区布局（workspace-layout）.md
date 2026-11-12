<!--
【文档说明】
承载内容：工作区目录结构、仓库映射、路径约定和上下文位置说明。
适用范围：always/on-demand 上下文；设计、编码和验证阶段按 index 加载。
填充指引：由 ai-sdd-init 技能根据 project-profile.yaml → repositories[] 填写仓库表和路径示例；
          后续新增/删除仓库时由 ai-sdd-repo-add / ai-sdd-repo-del 技能同步更新。
-->
# 工作区布局（Workspace Layout）

本工作区采用**多仓库并行**结构，代码仓库共享上下文文档与 OpenSpec 制品。

仓库类型包括：
- **backend**：后端服务仓库（CSF/Spring Boot 等），通过远程调用对外暴露接口
- **frontend-h5 / frontend-pc**：前端仓库，通过网关调用后端
- **fullstack**：同仓多层仓库（前端 + PSV + BSV），各组件运行时仍独立部署
- **components**：共享组件库，可被多仓库通过构建期依赖直接引用（import/包引用），无需远程调用

---

## 仓库与目录

| 仓库目录 | 说明 | GitNexus repo |
| --- | --- | --- |
| （待 ai-sdd-init 根据 project-profile.yaml → repositories[] 填充） | — | — |
| `.ai-sdd/context/` | SDD 上下文文档（按阶段/范围加载） | - |
| `.ai-sdd/raw/` | 原始需求文档落点（待 context-update 消化） | - |
| `.ai-sdd/requirements/` | 需求特定资料（按 change 组织） | - |
| `.ai-sdd/artifacts/changes/{change-name}/` | 测试与验证资产（按 change 组织） | - |
| `openspec/` | OpenSpec 制品（不属于任何 repo） | - |
| `AGENTS.md` / `CLAUDE.md` | Agent 统一指令（覆盖前后端） | - |

---

## 路径约定

| 场景 | 路径格式 | 示例 |
|------|----------|------|
| 代码路径 | `{仓库名}/...` | （待 ai-sdd-init 根据 project-profile 填充） |
| 上下文文档 | `.ai-sdd/context/{分类}/{文件名}.md` | `.ai-sdd/context/business/业务规则.md` |
| OpenSpec 制品 | `openspec/changes/{change-name}/{文件}` | `openspec/changes/add-feature/design.md` |

**规则：** design 和 tasks 中涉及具体代码路径时，**必须包含仓库目录前缀**，确保无歧义。

---

## GitNexus 索引

各仓库在自己的根目录下含 `.gitnexus/` 索引；统一通过同一个 GitNexus MCP server 对外服务，调用时通过 `repo` 参数区分（参见 `GitNexus使用规则（gitnexus-rules）.md`）。

---

## Git 管理

本工作区根目录为工作区级别 git 仓库；各子仓库均为独立 git 仓库（各自拥有 `.git/` 目录）。每个仓库独立提交；工作区根目录管理 `.ai-sdd/`、`openspec/`、`AGENTS.md` 等共享文件。

---

## 统一管理原则

- **Agent 指令**：根目录 `AGENTS.md` / `CLAUDE.md` 是唯一权威来源，覆盖前后端
- **GitNexus**：一个 MCP server 服务所有索引，工具调用必须指定 `repo` 参数
- **上下文文档**：`.ai-sdd/context/` 统一管理，代码路径必须使用仓库目录前缀
- **OpenSpec**：`openspec/` 统一管理，变更制品可同时涉及前后端任务

---

## 项目补充说明

> 此节用于补充本项目特有的目录结构、子模块布局或 git 管理特殊约定。

（待补充）
