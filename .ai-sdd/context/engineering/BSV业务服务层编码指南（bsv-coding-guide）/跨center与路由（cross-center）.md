<!--
【文档说明】
承载内容：跨中心与路由规范，承载跨中心调用分层、CenterFactory 路由、配置证据和检查项。
适用范围：后端 BSV/业务服务层 design、tasks、apply 和 review 阶段使用。
填充指引：由目标仓库 package、调用链、服务注册、defaults.xml、GitNexus 和 context-update 补充；只保留可迁移结构，具体中心和业务名用项目证据填充。
加载建议：任务落到 BSV、业务服务、DAO/BO/Engine、跨中心或分库路由时加载。
-->
# 跨 Center 与路由规范（Cross-Center & Routing）

> 本文只保留通用结构。具体中心枚举、服务码、适配类、路由键、CenterUtil 常量和 datasource 名称必须从目标仓库既有代码、配置和 project-profile 中确认。

---

## 一、跨中心调用体系

### 1.1 中心/系统枚举

| 枚举或常量类 | 目标中心/系统 | 调用协议 | 证据来源 |
|--------------|---------------|----------|----------|
| 待补充 | 待补充 | CSF / HTTP / MQ / 本地适配 | 源码、配置、API Registry |

### 1.2 标准调用分层

```text
业务编排层
  -> 适配接口（隐藏远程协议）
    -> 适配实现（CSF/HTTP/MQ 调用）
      -> 目标中心/外部系统
```

| 层次 | 要求 |
|------|------|
| 业务编排层 | 依赖稳定的适配接口，不直接拼远程服务码 |
| 适配接口 | 用业务语义命名方法，入参出参保持清晰 |
| 适配实现 | 集中处理远程调用、序列化、异常转换和日志 |
| 目标能力 | 以 API 文档、方法级下钻或源码证据确认契约 |

### 1.3 serviceCode 实证验证（禁止推导）

> 适用场景：使用跨中心客户端（如 `CenterClient.call` / `CsfServiceCaller.call` / 项目约定的等价 API）发起跨中心调用前，必须完成以下实证验证，**禁止仅凭命名规则推导**：

| # | 验证项 | 验证方式 |
|---|--------|---------|
| 1 | 目标 CSV 接口类存在 | GitNexus context/query 或 grep `I{Name}CSV.java` |
| 2 | 目标 CSV 实现类存在 | GitNexus context/query 或 grep `{Name}CSVImpl.java` |
| 3 | 目标方法在 CSV 中声明 | 读取 CSV 接口确认方法签名 |
| 4 | serviceCode 中心编码正确 | 中心编码 = 目标 CSV 所在仓库/中心的编码，**不是调用方的中心编码** |
| 5 | CSV → SV → DAO 链路可达 | 确认 CSV 委托的 SV 和 DAO 在同一仓库中存在 |

**禁止**：仅根据"存在 `I{Name}SV` 和 `I{Name}DAO`"就推导 `CenterClient.call("{center}_I{Name}CSV_{method}")` 可达。SV/DAO 是中心内部服务，跨中心调用必须经过 CSV 层封装和 CSF 注册。

### 1.4 跨中心调用占位模板

```java
IExternalCapabilitySV capability =
        ServiceFactory.getService(IExternalCapabilitySV.class);
ExternalOut out = capability.invoke(buildExternalIn(request));
```

> 具体接口名、服务码、常量类和序列化方式不得在结构中预设。

---

## 二、多中心分库路由

### 2.1 路由机制

| 路由维度 | 典型来源 | 使用前需要确认 |
|----------|----------|----------------|
| 区域/中心 | 区域、组织、租户或业务上下文 | 项目使用的 CenterUtil 常量和字段名 |
| 业务主键 | 业务实体标识、实例号或项目自定义路由键 | 是否能推导分片 |
| 数据源 | `.bo` datasource、defaults.xml、运行时配置 | 是否需要设置 CenterFactory |

### 2.2 路由调用模式

```java
try {
    CenterFactory.setCenterInfoByTypeAndValue({ROUTE_TYPE}, routeValue);
    return daoOrService.doWork(input);
} finally {
    CenterFactory.setCenterInfoEmpty();
}
```

### 2.3 路由规范

| 规则 | 说明 |
|------|------|
| 进入分库表访问前设置路由 | 使用项目确认的 route type 和 route value |
| finally 中清理路由上下文 | 避免线程复用导致串库 |
| 批量跨中心操作分组处理 | 同一路由值一组，避免频繁切换 |
| 读写同一业务对象保持路由一致 | 避免读写落到不同分片 |
| 不确定分片时先查询主数据或映射表 | 禁止猜测路由值 |

---

## 三、新增跨中心能力步骤

1. 先查找目标项目是否已有适配接口或同类调用模式。
2. 确认目标接口契约、服务码、入参、出参、异常和超时策略。
3. 在适配层新增接口与实现，封装远程协议细节。
4. 在业务层只依赖适配接口，不直接引用远程协议常量。
5. 补充服务注册、权限、超时、重试、日志和监控配置。
6. 编写成功、失败、超时、重复调用和路由错误场景验证。

---

## 四、AI 编码检查清单

| # | 检查项 |
|---|--------|
| 1 | 跨中心调用没有绕过适配层直接散落服务码 |
| 2 | 路由键和 route type 已由源码/配置确认 |
| 3 | CenterFactory 设置和清理成对出现 |
| 4 | 下游异常已转换为本项目统一异常或错误码 |
| 5 | 日志记录了调用目标、业务主键、耗时和失败摘要 |
| 6 | 未把具体中心名、服务码或配置值写死在模板结构中 |
| 7 | 跨中心调用客户端的 serviceCode 已通过源码或 GitNexus 实证确认目标 CSV 存在（见 §1.3），未凭命名规则推导 |
| 8 | serviceCode 中心编码前缀与目标 CSV 所在仓库/中心一致 |
