<!--
【文档说明】
承载内容：BSV 定位与工程结构，承载工程分层、目录组织、包路径占位和落点判断。
适用范围：后端 BSV/业务服务层 design、tasks、apply 和 review 阶段使用。
填充指引：由目标仓库 package、调用链、服务注册、defaults.xml、GitNexus 和 context-update 补充；只保留可迁移结构，具体中心和业务名用项目证据填充。
加载建议：任务落到 BSV、业务服务、DAO/BO/Engine、跨中心或分库路由时加载。
-->
# 定位与工程结构（Structure）

> 本文用于帮助 AI 判断 BSV/业务服务层代码应落在哪一层。具体模块名和目录名以目标仓库为准。

---

## 一、定位

| 维度 | 说明 |
|---|---|
| 系统层级 | BSV/业务服务层，承载权威业务规则、领域服务、数据访问和对外能力 |
| 上游调用方 | BFF/PSV、其他业务中心、后台任务或外部适配 |
| 下游依赖 | DAO/Engine、缓存、配置、跨中心服务、外部系统 |
| 产物类型 | SV/CSV、DAO、BO/.bo、适配接口、后台任务和测试 |

---

## 二、技术栈确认项

| 层次 | 需确认内容 |
|---|---|
| 服务框架 | CSF/CSV、ServiceFactory/DI、服务注册方式 |
| 数据框架 | AppFrame2、BO/Engine/DAO、datasource 映射 |
| 构建测试 | Maven/Gradle/Ant、测试框架、runner 命令 |
| 集成方式 | CSF/HTTP/MQ、本地适配或脚本任务 |

---

## 三、工程结构占位

```text
{repo}/
├── {service_module}/          # 主业务服务模块
│   ├── service/               # 对外门面接口与实现
│   ├── business/              # 业务编排
│   ├── ability/               # 管理服务、DAO、基础能力
│   ├── structure/             # BO/IValue/.bo 等数据结构
│   ├── adapter/               # 跨中心/外部系统适配接口
│   └── adapter/impl/          # 适配实现
├── {client_module}/           # 对外 client、POJO 或公共接口
├── {task_module}/             # 定时任务、消费者或后台执行模块
└── {resource_module}/         # 配置、服务注册、defaults.xml 等
```

---

## 四、落点判断

| 需求点 | 推荐落点 | 判断依据 |
|--------|----------|----------|
| 新增页面调用能力 | service 门面 + business 编排 | 是否对上游暴露新接口 |
| 新增业务规则 | business 或领域 SV | 是否涉及事务、状态或主流程 |
| 新增表访问 | ability DAO + structure BO | 是否需要落库或查询数据 |
| 调用其他中心 | adapter 接口与实现 | 是否跨系统/跨协议 |
| 异步处理 | task/exe/consumer 或 ET 组件 | 是否需要重试、补偿、状态推进 |

---

## 五、模块职责表

| 模块 | 职责 | 禁止 |
|---|---|---|
| service | 协议门面、参数校验、异常转换 | 写复杂业务规则 |
| business | 业务编排、事务、幂等、规则 | 直接拼 SQL |
| ability | 管理服务、DAO、基础数据能力 | 调用页面协议对象 |
| structure | BO/IValue/.bo 数据结构 | 承载业务流程 |
| adapter | 跨中心和外部系统适配 | 泄露远程协议到 business |

---

## 六、context-update 更新要求

发现目标仓库真实结构后，应补充：

1. 实际顶层模块和职责。
2. 关键包路径、接口命名和实现命名。
3. 服务注册、datasource 和 CenterFactory 配置位置。
4. 常用测试命令和代码模式入口。
