<!--
【文档说明】
承载内容：AppFrame2/CSF 服务注册配置，承载自动发现、XML 注册、defaults.xml、数据源映射和 CenterFactory 模式。
适用范围：后端 AppFrame2/CSF 设计、任务拆分、编码和 review 阶段使用。
填充指引：由目标仓库代码、defaults.xml、.bo、服务注册、GitNexus 和 context-update 补充；通用框架规则可保留，项目特定值必须占位或注明证据。
加载建议：命中 AppFrame2、BO、Engine、DAO、SV、服务注册、数据源或编码风格时加载。
-->
# BSV 层服务注册配置指南

> AppFrame2 框架通过**约定优于配置**的方式管理 BSV 层服务端的 SV/DAO 注册。内部业务服务由框架自动发现，仅跨系统适配类服务需要 XML 显式注册。数据源路由通过 `defaults.xml` 中的包路径映射实现。

---

## 1. 配置文件体系

### 1.1 文件位置

各仓库的服务注册配置统一位于以下目录：

```
{仓库}/resources/src/main/resources/system/service/
  ├── defaults.xml           ← 全局配置（中心路由、事务映射、数据源、DAO 映射）
  ├── appframe-service.xml   ← 框架级服务注册（通常仅 RemoteDataStore 等极少数条目）
  └── pluginservice.xml      ← CSF 插件/客户端适配服务注册
```

### 1.2 加载顺序

1. `defaults.xml` — 加载全局配置（中心路由、事务映射、数据源连接池、DAO 数据源映射）
2. `appframe-service.xml` — 加载框架级显式注册服务
3. `pluginservice.xml` — 加载 CSF 插件客户端注册服务
4. AppFrame2 自动扫描 — 按命名约定发现内部 SV/DAO 实现类

---

## 2. SV/DAO 服务注册

### 2.1 自动发现（内部业务服务）

BSV 层内部业务 SV 和 DAO **不需要在 XML 中注册**。AppFrame2 框架根据命名约定自动发现并注册：

| 接口命名 | 实现命名 | 接口包 | 实现包 |
|---------|---------|--------|-------|
| `I{Name}SV` | `{Name}SVImpl` | `service.interfaces` | `service.impl` |
| `I{Name}DAO` | `{Name}DAOImpl` | `dao.{ds}.interfaces` | `dao.{ds}.impl` |

使用方式：

```java
I{Entity}SV sv = (I{Entity}SV) ServiceFactory.getService(I{Entity}SV.class);
I{Entity}DAO dao = (I{Entity}DAO) ServiceFactory.getService(I{Entity}DAO.class);
```

### 2.2 显式 XML 注册（插件/适配服务）

跨系统适配类服务必须在 `pluginservice.xml` 中显式注册：

```xml
<service id="{接口类全限定名}" invoke="pojo" type="primitive">
  <property name="interfaceClass" value="{接口类全限定名}" />
  <property name="implClass" value="{实现类全限定名}" />
</service>
```

属性说明：

| 属性 | 值 | 说明 |
|------|------|------|
| `id` | 接口类全限定名 | 唯一标识，与 `interfaceClass` 相同 |
| `invoke` | `pojo` | 固定值，本地 Java 对象调用 |
| `type` | `primitive` | 固定值，基础服务类型 |
| `interfaceClass` | 接口类全限定名 | `ServiceFactory.getService()` 传入的 Class 参数 |
| `implClass` | 实现类全限定名 | 实际实例化的实现类 |

### 2.3 注册方式判断规则

| 条件 | 注册方式 |
|------|---------|
| 仓库内部的 SV（`service.interfaces/impl`） | 自动发现，无需 XML |
| 仓库内部的 DAO（`dao.*.interfaces/impl`） | 自动发现，无需 XML |
| CSF 插件客户端（`client.plugin.service.*`） | `pluginservice.xml` 显式注册 |
| 接口与实现不在约定包结构中 | `appframe-service.xml` 显式注册 |

---

## 3. defaults.xml 全局配置

### 3.1 中心路由（center）

`<center>` 定义中心类型到路由实现类的映射，各仓库的实现类可能不同：

```xml
<center>
  <property name="{RouteKeyA}"        value="{base_package}.common.center.{RouteKeyACenterImpl}"/>
  <property name="{EntityId}:{ENTITY_ID_COLUMN}" value="{base_package}.common.center.{EntityIdCenterImpl}"/>
  <property name="{RouteKeyB}"        value="{base_package}.common.center.{RouteKeyBCenterImpl}"/>
  <property name="{RouteKeyC}:{COLUMN}" value="{base_package}.common.center.{RouteKeyCCenterImpl}"/>
</center>
```

> 路由键名与实现类以目标项目 `defaults.xml` 和 `CenterUtil`（或等价工具）为准；上表仅为结构占位。

每种中心类型对应一个实现类，根据传入的业务标识动态确定数据应路由到哪个分库实例。

### 3.2 事务映射（transaction）

定义**包路径 → 事务数据源**的映射，控制事务边界归属：

```xml
<transaction type="Required">
  <clazz name="com.ai.appframe2.complex.transaction.impl.LocalMutilTransactionImpl" />
  <mapping>
    <property name="{base_package}.baseService" value="{master_ds}"/>
    <property name="{base_package}.mgr.{domain}.bo" value="{master_ds}" />
    <property name="com.asiainfo.appframe.ext.exeframe" value="{config_ds}"/>
    <property name="{base_package}.common.{module}" value="{shard_ds}{CENTER}"/>
    <property name="{base_package}.{message_module}" value="{shard_ds}{CENTER}" />
    <!-- ... -->
  </mapping>
</transaction>
```

### 3.3 数据源映射（datasource mapping）

定义 **DAO 包路径 → 数据库连接**的映射，控制 DAO/Engine 实际的数据库连接路由：

```xml
<datasource>
  <!-- 连接池配置（见 3.5 节）... -->
  <mapping>
    <property name="{base_package}.mgr.{domain}.dao.{shard_suffix}" value="{shard_ds}{CENTER}" readonly="ro_{shard_ds}{CENTER}"/>
    <property name="{base_package}.mgr.{domain}.dao.{master_suffix}" value="{master_ds}" />
    <property name="{base_package}.cache.dao" value="{config_ds}" />
    <property name="{base_package}.common" value="{config_ds}"/>
    <!-- ... -->
  </mapping>
</datasource>
```

> **双层映射**：事务映射（`<transaction><mapping>`）和数据源映射（`<datasource><mapping>`）配置格式相同但作用不同。新增 DAO 时**两层都需要**检查/配置。匹配规则为最长包路径前缀优先。

### 3.4 读写分离

通过 `readonly` 属性指定只读数据源，框架自动根据操作类型路由：

```xml
<!-- 写操作 → {shard_ds}{CENTER}，只读查询 → ro_{shard_ds}{CENTER} -->
<property name="{base_package}.mgr.{domain}.dao.{shard_suffix}" value="{shard_ds}{CENTER}" readonly="ro_{shard_ds}{CENTER}"/>

<!-- 不需要读写分离 -->
<property name="{base_package}.mgr.{domain}.dao.{master_suffix}" value="{master_ds}" />
```

### 3.5 数据源连接池（datasource pool）

BSV 层使用 `LocalMutilDataSourceImpl`，从数据库配置表动态加载，并在 `defaults.xml` 中定义连接池参数：

```xml
<datasource>
  <clazz name="com.ai.appframe2.complex.datasource.impl.LocalMutilDataSourceImpl">
    <property name="tableName" value="cfg_db_acct"/>
    <property name="urlTableName" value="cfg_db_url"/>
    <property name="relatTableName" value="cfg_db_relat"/>
    <!-- prefetch 预取配置... -->
  </clazz>

  <pool name="base" primary="true" type="dbcp" db="oracle" init="true" isAdvanceUrl="true">
    <property name="initialSize" value="1"/>
    <property name="maxTotal" value="2"/>
    <!-- ... -->
  </pool>

  <pool name="{master_ds}" init="true" isAdvanceUrl="true" read="{master_ds}-r">
    <!-- read 属性指定只读副本池 -->
  </pool>

  <pool name="{shard_ds}1-1" init="true" template="{shard_ds}{CENTER}" isAdvanceUrl="true">
    <!-- template 属性表示继承动态中心模板 -->
  </pool>
</datasource>
```

连接池关键属性：

| 属性 | 说明 |
|------|------|
| `primary` | 标识主数据源（通常为 `base` 池） |
| `template` | 继承动态中心模板（如 `{shard_ds}{CENTER}`），运行时按中心编号解析 |
| `isAdvanceUrl` | 从数据库表读取连接 URL |
| `read` | 指定只读副本池名（如 `{master_ds}-r`） |
| `init` | 启动时初始化连接池 |

### 3.6 动态数据源模板

数据源名称使用 `{CENTER}` 占位符，运行时根据中心路由动态替换：

| 模板 | 实际解析（示例） | 用途 |
|------|----------------|------|
| `{shard_ds}{CENTER}` | `{shard_ds}1-1`、`{shard_ds}2-1` 等 | 主分片库（读写） |
| `ro_{shard_ds}{CENTER}` | `ro_{shard_ds}1-1` 等 | 分片只读副本 |
| `{history_ds}{CENTER}` | `{history_ds}1-1` 等 | 历史库（若存在） |
| `{domain_ds}{CENTER}` | `{domain_ds}1-1` 等 | 项目自定义业务分片库 |
| `{external_ds}{CENTER}` | `{external_ds}1-1` 等 | 项目自定义外部/专项分片库 |

---

## 4. DAO 包路径与数据源约定

BSV 层 DAO 采用**包名后缀区分数据源**：

| DAO 包路径后缀 | 对应数据源 | 示例 |
|---------------|----------|------|
| `.dao.{shard_suffix}` | 分片库（`{shard_ds}{CENTER}`） | `{base_package}.mgr.{domain}.dao.{shard_suffix}` |
| `.dao.{master_suffix}` | 主数据/非分片库 | `{base_package}.mgr.{domain}.dao.{master_suffix}` |
| `.dao` (无后缀) | 取决于映射配置 | `{base_package}.cache.dao` → `{config_ds}` |

同一业务领域的 DAO 可按数据源拆分为多个包，分别在 `defaults.xml` 映射中配置不同数据源。具体后缀名以目标项目为准。

---

## 5. BO 实体配置

BO（Bean + Engine + .bo）**不需要在 XML 中注册**，框架通过类加载和 `.bo` 配置文件自动发现。

> `.bo` 文件的完整 XML Schema、三种 BO 模式、Query BO、datasource 三层解析优先级、datasource 样例和多种占位示例见 [BO配置文件规范](BO配置文件规范（bo-config-spec）.md)。新建 `.bo` 文件时**必须参考 BO配置文件规范**，本节仅说明服务注册层面的要点。

关键要点：
- `datasource` — 数据源标识，需与 DAO 包路径在 `defaults.xml` 中的映射一致
- `name` — BO 名称（带 `BO` 前缀），需与 Bean 类的 `m_boName` 最后一段一致
- `mainattr` — 主属性名称（主键或业务主属性），在分库场景下框架也据此辅助路由
- `.bo` 文件路径必须与 `m_boName` 的包路径完全一致（注意：是 `m_boName` 路径，不要求与 Bean 类本身的包路径一致）

---

## 6. CenterFactory 中心路由编码模式

> 以下编码模式适用于使用 CenterFactory 进行分库路由的 BSV 层仓库；具体路由键、数据源和清理方法需参照目标仓库实际代码。

涉及分库表的操作，必须遵循以下模式。CenterFactory 可以在 **SV 层**设置，**也可以由 DAO 方法基于入参自行设置**，关键是必须在 `finally` 中清理。

**SV 层设置示例：**

```java
public List<BO{Entity}Bean> query{Entity}ByRouteKey(String routeKey, Integer validType)
        throws Exception, RemoteException {
    try {
        CenterFactory.setCenterInfoByTypeAndValue({ROUTE_TYPE}, routeKey);
        List<BO{Entity}Bean> entityList = get{Entity}Dao().query{Entity}Beans(
            condition.toString(), parameter);
        // ...
    } finally {
        CenterFactory.setCenterInfoEmpty();
    }
}
```

**DAO 层设置示例（占位模板）：**

```java
public void save{Entity}(BO{Entity}Bean bean) throws Exception {
    try {
        CenterFactory.setCenterInfoByTypeAndValue(
            {ROUTE_TYPE}, String.valueOf(bean.getRouteValue()));
        BeanBridgeHelper.save(bean);
        BO{Entity}Engine.save(bean);
    } finally {
        CenterFactory.setCenterInfoEmpty();
    }
}
```

**规则**：
- 涉及分库表的操作**前**，必须调用 `CenterFactory.setCenterInfoByTypeAndValue()` 设置中心路由。
- 必须在 `finally` 块中调用 `CenterFactory.setCenterInfoEmpty()` 清除中心信息。
- 支持的路由类型必须以目标项目 `CenterUtil` 或等价常量为准，常见维度包括业务键、实体标识、区域、租户或用户实例。
- 不涉及分库表的操作（如 `{master_ds}`、`{config_ds}`）可省略。
- 批量跨区域/分片操作时需逐条/分组重设 CenterFactory。

---

## 7. 新增服务检查清单

| # | 检查项 | 适用范围 |
|---|--------|---------|
| 1 | SV/DAO 遵循命名约定（`I{功能}SV`/`{功能}SVImpl`、`I{功能}DAO`/`{功能}DAOImpl`），接口放 `interfaces/` 包、实现放 `impl/` 包，无需 XML 注册 | 所有 BSV 层 |
| 2 | CSF 插件/客户端适配服务在 `pluginservice.xml` 中显式注册 | 所有 BSV 层 |
| 3 | 新增 DAO 的包路径在 `defaults.xml` 的 `<datasource><mapping>` 和 `<transaction><mapping>` 中都有对应条目 | 所有 BSV 层 |
| 4 | DAO 包名后缀与数据源映射一致（分片后缀 → 分片库，主数据后缀 → 主库） | 所有 BSV 层 |
| 5 | `.bo` 文件 `datasource` 与 DAO 包路径数据源映射一致 | 所有 BSV 层 |
| 6 | `.bo` 文件表名用花括号包裹（如 `{TABLE_NAME}`），`mainattr` 指定分库路由属性 | 所有 BSV 层 |
| 7 | 需要读写分离的 DAO 映射增加 `readonly` 属性 | 所有 BSV 层 |
| 8 | 涉及分库表的操作（SV 或 DAO 层），操作前设置 `CenterFactory`，`finally` 中清除 | 使用 CenterFactory 的 BSV 层 |
