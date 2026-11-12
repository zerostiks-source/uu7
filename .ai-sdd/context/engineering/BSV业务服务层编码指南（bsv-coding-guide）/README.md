<!--
【文档说明】
承载内容：BSV 业务服务层指南目录入口，说明工程结构、分层职责、跨中心路由和检查清单的文件清单。
适用范围：后端 BSV/业务服务层的 design、tasks、apply 和 review 阶段使用。
填充指引：由目标仓库 package、defaults.xml、服务注册、GitNexus 和人工经验补充；保持泛化，具体包路径用占位或项目证据。
加载建议：任务落到 BSV、SV/DAO/BO/Engine、跨中心或 CenterFactory 时先加载 README。
-->
# BSV 业务服务层编码指南（BSV Coding Guide）目录

> 目录说明：本目录描述 BSV/业务服务层常见工程结构、分层职责、跨中心调用、分库路由和编码自检。具体包路径、模块名、基类、接口和配置必须由目标仓库确认。

## 文件清单与加载策略

| 文件 | 内容概要 | 推荐加载时机 |
|------|---------|-------------|
| [定位与工程结构（structure）.md](定位与工程结构（structure）.md) | BSV 工程结构、模块职责、目录边界 | 需要定位实现落点或判断模块职责时 |
| [分层编码规范（layering）.md](分层编码规范（layering）.md) | service/business/ability/dao/structure/adapter 分层规则 | 编写或调整 BSV 代码前 |
| [跨center与路由（cross-center）.md](跨center与路由（cross-center）.md) | 跨中心调用、远程封装、CenterFactory/路由键 | 涉及下游中心、分库表或路由字段时 |
| [检查清单（checklist）.md](检查清单（checklist）.md) | BSV 编码和交付自检项 | tasks/apply 完成后自检 |

## 推荐加载顺序

1. 先读 README 判断是否命中 BSV/业务服务层。
2. 需要落点时读 structure，需要写代码时读 layering。
3. 涉及跨中心或分库时再读 cross-center。
4. 完成后读 checklist 自检。

## 延迟加载建议

- 只涉及页面服务层、前端或纯文档时不加载本目录。
- 未涉及跨中心调用或分库路由时，延迟加载 cross-center。

## 卸载建议

- BSV 任务完成并通过自检后，可卸载结构/分层细节，仅保留 checklist 结论。

## 填充规则

- 本目录只允许保留泛化结构和通用技术栈知识。
- 项目专属包名、仓库名、类名、配置项必须由 ai-sdd-init 或后续 context-update 写入项目实例上下文。
