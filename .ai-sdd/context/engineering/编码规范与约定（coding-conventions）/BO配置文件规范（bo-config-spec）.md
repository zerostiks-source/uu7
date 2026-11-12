<!--
【文档说明】
承载内容：.bo XML 配置规范，承载 BO 模式、字段映射、datasource 规则、XML 样例和检查项。
适用范围：后端 AppFrame2/CSF 设计、任务拆分、编码和 review 阶段使用。
填充指引：由目标仓库代码、defaults.xml、.bo、服务注册、GitNexus 和 context-update 补充；通用框架规则可保留，项目特定值必须占位或注明证据。
加载建议：命中 AppFrame2、BO、Engine、DAO、SV、服务注册、数据源或编码风格时加载。
-->
# BO 配置文件规范（.bo XML）

> **.bo 文件**是 AppFrame2 框架的 ORM 元数据描述文件，定义 BO 对象与数据库表的映射关系。框架在运行时加载这些文件驱动 ORM 行为。典型项目中存在多种 BO 模式（标准模式、POJO 模式和纯元数据模式等），本规范同时覆盖。

---

## 1. 文件位置与命名

### 1.1 存放路径

`.bo` 文件存放在模块的 `src/main/resources/` 下，按 Java 包结构镜像组织。**路径必须与 Bean 类中 `m_boName` 的包路径完全一致**（注意：是 `m_boName` 路径，不要求与 Bean 类本身的包路径一致）。

**典型项目的路径模式**：

| 模块 | 包前缀 | 路径示例 |
|------|--------|---------|
| ability | `{base_package}.mgr.{模块}.bo` | `ability/src/main/resources/{base_package_path}/mgr/{module}/bo/` |
| ability（POJO） | `{base_package}.mgr.{模块}.pojo` | `ability/src/main/resources/{base_package_path}/mgr/{module}/pojo/` |
| structure | `{base_package}.base.ability.{层}.bo` | `structure/src/main/resources/{base_package_path}/base/ability/entity/so/bo/` |

> **Bean 与 .bo 分离模式**：structure 模块中 Bean 类在 `bean/` 子包，.bo 文件在 `bo/` 子包，但 Bean 中 `m_boName` 指向 `bo/` 路径。框架按 `m_boName` 定位 .bo 文件，因此分离不影响运行时。

### 1.2 文件命名

**标准模式（bo/ 目录）**：文件名与 `<sysbo>` 的 `name` 属性一致，后缀 `.bo`，**不得以 `Bean` 结尾**。

| name 属性 | 文件名 | Bean 类名 |
|-----------|--------|----------|
| `BO{Entity}` | `BO{Entity}.bo` | `BO{Entity}Bean.java` |
| `BO{ShardEntity}` | `BO{ShardEntity}.bo` | `BO{ShardEntity}Bean.java` |

**POJO 模式（pojo/ 目录）**：文件名和 `name` 属性**可以含 `Bean` 后缀**，与 POJO 类名对应。

| name 属性 | 文件名 | POJO 类名 |
|-----------|--------|----------|
| `BO{Entity}PojoBean` | `BO{Entity}PojoBean.bo` | `{Entity}PojoBean.java` |

**历史表 .bo 文件**：同一 BO 可有主表和历史表两个 .bo 文件，历史表文件名加 `H` 后缀，但 `name` 属性保持与主表相同（框架按 `m_boName` 全路径区分）。

| 文件名 | name 属性 | 映射表 |
|--------|----------|-------|
| `BO{HistoryEntity}.bo` | `BO{HistoryEntity}` | `DOMAIN_HISTORY` |
| `BO{HistoryEntity}H.bo` | `BO{HistoryEntity}` | `{DOMAIN_HISTORY_C}` |

---

## 2. 三种 BO 模式

### 2.1 标准模式（DataContainer）

Bean 继承 `com.ai.appframe2.bo.DataContainer`，使用 `S_FIELD_NAME` 常量和 `initXxx`/`getXxx`/`setXxx` 方法，配合 Engine 类提供 CRUD 入口。

```java
public class BO{Entity}Bean extends DataContainer implements DataContainerInterface {
    private static String m_boName = "{base_package}.mgr.{module}.bo.BO{Entity}";

    public static ObjectType S_TYPE = null;
    static {
        try {
            S_TYPE = ServiceManager.getObjectTypeFactory().getInstance(m_boName);
        } catch(Exception e) {
            throw new RuntimeException(e);
        }
    }

    public BO{Entity}Bean() throws AIException {
        super(S_TYPE);
    }

    public final static String S_EntityId = "ENTITY_ID";
    // ... 字段常量 + init/set/setNull/get/getInitialValue 方法
}
```

### 2.2 POJO 模式

Bean 是纯 POJO（不继承 DataContainer），使用 camelCase 私有字段 + 标准 getter/setter，由 DAO 层直接查询映射。常见于非 DataContainer 映射的数据源（以项目配置为准）。

```java
public class {Entity}PojoBean {
    private Integer id;
    private String entityName;
    // getter/setter
}
```

### 2.3 纯元数据模式

.bo 文件可以独立存在，无需本地 Bean 类。框架通过 `DataContainerFactory` 动态实例化 `DataContainer`，无需类型化包装。

| 模式 | .bo 目录 | Bean 基类 | DB datatype | 表名大小写 | name 含 Bean |
|------|---------|----------|------------|----------|-------------|
| 标准 | `bo/` | `DataContainer` | `NUMBER`/`VARCHAR2`/`DATE`/`CLOB`/`CHAR` | 大写 | 禁止 |
| POJO | `pojo/` | 无 | `INT`/`VARCHAR`/`DATE`/`BPCHAR` | 小写 | 允许 |
| 纯元数据 | `bo/` | 无本地 Bean | 同标准模式 | 大写 | 禁止 |

> **Query BO（type="query"）**：部分存量项目可能存在 query BO（`<mapingenty type="query">`），其 `<mapingenty>` 内容为原始 SQL。query BO 属于遗留模式，新建 BO 时通常不应使用，除非目标项目已有明确约定。

### 2.4 查询条件 BO（QBO，type="custom" + VIRTUAL 字段）

除表映射 BO 外，项目中常见**查询条件 BO**（`QBO...` 前缀），用于封装查询参数。以下为典型样本：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sysbolist>
  <sysbo datasource="base" name="QBO{Entity}QryCdn" mainattr="AREA_ID">
    <mapingenty type="custom">custom</mapingenty>
    <attrlist>
      <attr name="ENTITY_ID" maxlength="20" datatype="Long" type="VIRTUAL" />
      <attr name="ROUTE_KEY" maxlength="20" datatype="String" type="VIRTUAL" />
      <attr name="ITEM_TYPE" maxlength="20" datatype="Integer" type="VIRTUAL" />
      <attr name="REGION_ID" maxlength="20" datatype="String" type="VIRTUAL" />
    </attrlist>
    <relationlist />
    <oplist />
  </sysbo>
</sysbolist>
```

| 特征 | 表映射 BO（§2.1-2.3） | 查询条件 BO（QBO） |
|------|--------------------|--------------------|
| name 前缀 | `BO...` | `QBO...` |
| `<mapingenty>` type | `table` | `custom` |
| `<attr>` type | `PK` / `COL` | `VIRTUAL` |
| `<mapingcol>` | 必需 | 不需要 |
| 对应 Bean | 标准 Bean 或 POJO | 标准 Bean（继承 DataContainer） |

模式要点：
- `sysbo name` 与生成的 Bean/Engine 名称对应
- 字段多为 `type="VIRTUAL"`，用于传递查询参数，不映射物理表列
- `datasource` 通常设为 `base`（不实际访问数据库）
- 对应的 Bean 和 Engine 与标准模式结构一致

---

## 3. 完整 XML Schema

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sysbolist>
  <sysbo datasource="{数据源}" name="{BO名}" mainattr="{主属性名}">
    <mapingenty type="table">{数据库表名}</mapingenty>
    <datafilter />
    <attrlist>
      <attr floatlength="{小数位数}" name="{Java属性名}" maxlength="{最大长度}"
            datatype="{Java数据类型}" type="{字段类型}" remark="{枚举说明}">
        <mapingcol datatype="{DB数据类型}">{数据库列名}</mapingcol>
      </attr>
    </attrlist>
    <relationlist />
    <oplist />
  </sysbo>
</sysbolist>
```

### 3.1 元素与属性详解

| 元素 | 父元素 | 必填 | 属性 | 说明 |
|------|--------|------|------|------|
| `<sysbolist>` | — | 是 | — | 根元素 |
| `<sysbo>` | sysbolist | 是 | `datasource` | 数据源标识（见§4），优先级高于 defaults.xml 映射 |
| | | | `name` | BO 名称（与 `m_boName` 最后一段一致，标准模式不含 Bean） |
| | | | `mainattr` | 主属性名称（主键或业务主属性），部分查询类 BO 可省略 |
| | | | `remark` | 可选。BO 级别的业务说明（如 `remark="{业务说明}"`） |
| `<mapingenty>` | sysbo | 是 | `type` | 固定 `"table"` |
| | | | 文本内容 | `{TABLE_NAME}` 分表场景 / `TABLE_NAME` 非分表 |
| `<datafilter>` | sysbo | 是 | — | 数据过滤器，通常空元素 |
| `<attrlist>` | sysbo | 是 | — | 属性列表容器 |
| `<attr>` | attrlist | 是 | `name` | Java 属性名（大写下划线风格） |
| | | | `maxlength` | 最大长度 |
| | | | `datatype` | Java 数据类型：`Long` / `Integer` / `String` / `DateTime` |
| | | | `type` | `COL`（普通列）或 `PK`（主键） |
| | | | `floatlength` | 小数位数（通常 `0`） |
| | | | `remark` | 可选。枚举值说明或业务含义 |
| `<mapingcol>` | attr | 是 | `datatype` | DB 列类型（见§3.2） |
| | | | 文本内容 | 数据库列名（大写） |
| `<relationlist>` | sysbo | 是 | — | 保留空元素 |
| `<oplist>` | sysbo | 是 | — | 保留空元素 |

### 3.2 数据类型映射

**Oracle 数据库（标准模式）**：

| Java datatype（attr） | DB datatype（mapingcol） | Java 实际类型 |
|----------------------|------------------------|-------------|
| `Long` | `NUMBER` | `long` |
| `Integer` | `NUMBER` | `int` |
| `String` | `VARCHAR2` | `String` |
| `String` | `CHAR` | `String`（定长字符串） |
| `String` | `NVARCHAR2` | `String`（Unicode） |
| `String` | `CLOB` | `String`（大文本） |
| `DateTime` | `DATE` | `java.sql.Timestamp` |

**POJO 模式（非 DataContainer，按项目 datasource 配置）**：

| Java datatype（attr） | DB datatype（mapingcol） | 说明 |
|----------------------|------------------------|------|
| `Integer` | `INT` / `INT4` | PostgreSQL 整数 |
| `Long` | `INT8` / `NUMERIC` | PostgreSQL 长整数 |
| `String` | `VARCHAR` | PostgreSQL 变长字符串 |
| `String` | `BPCHAR` | PostgreSQL 定长字符串 |
| `DateTime` | `DATE` / `TIMESTAMP` | PostgreSQL 时间戳 |

### 3.3 主键声明规则

- **单主键**：一个 `<attr>` 设 `type="PK"`，其余 `type="COL"`。`mainattr` 指向该字段名。
- **复合主键**：多个 `<attr>` 设 `type="PK"`。`mainattr` 指向其中一个（通常是逻辑主属性）。
- `mainattr` 也可指向非 PK 字段（业务主属性），用于框架 ID 生成器绑定。

---

## 4. datasource 数据源规则

### 4.1 三层解析优先级

| 优先级 | 层次 | 配置位置 | 说明 |
|--------|------|---------|------|
| **1（最高）** | `.bo` 文件 `datasource` 属性 | BO 级别 | 精确指定，覆盖一切映射 |
| **2** | `<datasource><mapping>` | `defaults.xml` | 按 Java 包名最长前缀匹配 |
| **3（最低）** | `<transaction><mapping>` | `defaults.xml` | 按 Java 包名最长前缀匹配 |

`.bo` 文件中的 `datasource` 会**覆盖** defaults.xml 的包名映射。当 BO 虽在某包路径下但需连接不同数据库时，直接在 .bo 文件中指定即可。

### 4.2 数据源配置加载

`LocalMutilDataSourceImpl` 从两个来源合并加载数据源：
1. **数据库配置表**：`cfg_db_acct` / `cfg_db_url` / `cfg_db_relat`（运行时动态加载）
2. **defaults.xml**：`<pool>` 连接池定义

部分 datasource 值仅在数据库配置表中注册，defaults.xml 中不可见。

### 4.3 datasource 清单模板

> 本表为项目 datasource 登记模板，**不是可直接使用的清单**。实际可用值必须以目标仓库 `defaults.xml`、数据库配置表和运行时配置为准。

| datasource | 数据域/用途 | 数据库类型 | 分片规则 | 证据 |
|-----------|------------|-----------|----------|------|
| 待补充 | 待补充 | 待补充 | 待补充 | defaults.xml/配置表 |

> 分片 datasource 中的 `{CENTER}` / `{N}` 等为运行时分片模板；`.bo` 中写目标环境允许的逻辑名。**禁止硬编码环境专属分片号**。部分 datasource 仅在数据库配置表中注册，使用前须确认目标环境已配置。

### 4.4 确定 datasource 的方法

1. 确定 BO 对应的数据库表所在的物理库
2. 查找 `defaults.xml` 中对应的 `<pool>` 或 `<datasource><mapping>` 值
3. 如果包名映射已匹配正确库，可省略（使用默认映射）；如果需要覆盖，显式写入 `.bo` 文件

---

## 5. 表名格式

| 格式 | 示例 | 说明 |
|------|------|------|
| `{TABLE_NAME}` | `{DOMAIN_SHARD_ENTITY}` | 花括号包裹，分表场景 |
| `TABLE_NAME` | `{ENTITY_TABLE}` | 直接写表名，非分表（Oracle，大写） |
| `table_name` | `{table_name}` | 小写表名（部分 POJO 模式） |

> 主业务表（数据量大需分表）使用 `{}`；配置表、管理表直接写表名。

---

## 6. 常见设计模式

### 6.1 操作审计字段

典型项目中最常见的审计字段组合：

```xml
<attr floatlength="0" name="CREATE_DATE" maxlength="20" datatype="DateTime" type="COL">
  <mapingcol datatype="DATE">CREATE_DATE</mapingcol>
</attr>
<attr floatlength="0" name="DONE_DATE" maxlength="20" datatype="DateTime" type="COL">
  <mapingcol datatype="DATE">DONE_DATE</mapingcol>
</attr>
```

操作员和组织字段的数据类型因模块而异：

```xml
<!-- ability 模块（旧数据模型）：Long / NUMBER -->
<attr floatlength="0" name="OP_ID" maxlength="12" datatype="Long" type="COL">
  <mapingcol datatype="NUMBER">OP_ID</mapingcol>
</attr>
<attr floatlength="0" name="ORG_ID" maxlength="12" datatype="Long" type="COL">
  <mapingcol datatype="NUMBER">ORG_ID</mapingcol>
</attr>

<!-- structure/unifybox 模块（新数据模型）：String / VARCHAR2 -->
<attr floatlength="0" name="OPRT_ID" maxlength="32" datatype="String" type="COL">
  <mapingcol datatype="VARCHAR2">OPRT_ID</mapingcol>
</attr>
<attr floatlength="0" name="ORG_ID" maxlength="32" datatype="String" type="COL">
  <mapingcol datatype="VARCHAR2">ORG_ID</mapingcol>
</attr>
```

> **注意**：新建 BO 时，`OP_ID`/`ORG_ID` 的数据类型必须与目标表的实际列类型一致。ability 模块多用 `Long`/`NUMBER`，structure 模块多用 `String`/`VARCHAR2`。

部分业务域可能有专属审计字段组合，新建 BO 时以目标表实际列为准，勿照搬其他域惯例。

### 6.2 生命周期字段

```xml
<attr floatlength="0" name="VALID_DATE" maxlength="20" datatype="DateTime" type="COL">
  <mapingcol datatype="DATE">VALID_DATE</mapingcol>
</attr>
<attr floatlength="0" name="EXPIRE_DATE" maxlength="20" datatype="DateTime" type="COL">
  <mapingcol datatype="DATE">EXPIRE_DATE</mapingcol>
</attr>
```

### 6.3 预留扩展字段

```xml
<attr floatlength="0" name="EXT1" maxlength="255" datatype="String" type="COL" remark="ext1">
  <mapingcol datatype="VARCHAR2">EXT1</mapingcol>
</attr>
```

### 6.4 区域编码字段

常见项目使用 `REGION_ID`（字符串）或 `REGION_CODE`（数字）作为区域标识；是否使用 `SPLIT_REGION_CODE` 以目标表设计为准：

```xml
<attr floatlength="0" name="REGION_ID" maxlength="6" datatype="String" type="COL">
  <mapingcol datatype="VARCHAR2">REGION_ID</mapingcol>
</attr>
```

或数字类型：

```xml
<attr floatlength="0" name="REGION_CODE" maxlength="6" datatype="Integer" type="COL" remark="区域编码">
  <mapingcol datatype="NUMBER">REGION_CODE</mapingcol>
</attr>
```

---

## 7. 完整示例

### 7.1 标准模式 — 单主键 + 分表（Oracle）

> 场景：通用分片业务表，数据源 `{shard_ds}`，分表 `{DOMAIN_SHARD_ENTITY}`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sysbolist>
  <sysbo datasource="{shard_ds}" name="BO{ShardEntity}" mainattr="ENTITY_ID">
    <mapingenty type="table">{DOMAIN_SHARD_ENTITY}</mapingenty>
    <datafilter />
    <attrlist>
      <attr floatlength="0" name="ENTITY_ID" maxlength="18" datatype="Long" type="PK" remark="实体标识">
        <mapingcol datatype="NUMBER">ENTITY_ID</mapingcol>
      </attr>
      <attr floatlength="0" name="OWNER_ID" maxlength="18" datatype="Long" type="COL" remark="归属对象标识">
        <mapingcol datatype="NUMBER">OWNER_ID</mapingcol>
      </attr>
      <attr floatlength="0" name="BUSINESS_KEY" maxlength="40" datatype="String" type="COL" remark="业务键">
        <mapingcol datatype="VARCHAR2">BUSINESS_KEY</mapingcol>
      </attr>
      <attr floatlength="0" name="STATUS" maxlength="2" datatype="Integer" type="COL"
           remark="按目标项目枚举填写">
        <mapingcol datatype="NUMBER">STATUS</mapingcol>
      </attr>
      <attr floatlength="0" name="CREATE_DATE" maxlength="20" datatype="DateTime" type="PK" remark="创建日期">
        <mapingcol datatype="DATE">CREATE_DATE</mapingcol>
      </attr>
      <attr floatlength="0" name="REGION_CODE" maxlength="6" datatype="Integer" type="COL" remark="区域编码">
        <mapingcol datatype="NUMBER">REGION_CODE</mapingcol>
      </attr>
    </attrlist>
    <relationlist />
    <oplist />
  </sysbo>
</sysbolist>
```

### 7.2 标准模式 — 显式主键 + 非分表

> 场景：通用主数据表，数据源 `{master_ds}`，直接表名

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sysbolist>
  <sysbo datasource="{master_ds}" name="BO{Entity}" mainattr="PARENT_ENTITY_ID">
    <mapingenty type="table">DOMAIN_ENTITY</mapingenty>
    <datafilter />
    <attrlist>
      <attr floatlength="0" name="ENTITY_ID" maxlength="12" datatype="Long" type="PK">
        <mapingcol datatype="NUMBER">ENTITY_ID</mapingcol>
      </attr>
      <attr floatlength="0" name="PARENT_ENTITY_ID" maxlength="12" datatype="Long" type="COL">
        <mapingcol datatype="NUMBER">PARENT_ENTITY_ID</mapingcol>
      </attr>
      <attr floatlength="0" name="ENTITY_NAME" maxlength="255" datatype="String" type="COL">
        <mapingcol datatype="VARCHAR2">ENTITY_NAME</mapingcol>
      </attr>
      <attr floatlength="0" name="ENTITY_STATUS" maxlength="2" datatype="Integer" type="COL">
        <mapingcol datatype="NUMBER">ENTITY_STATUS</mapingcol>
      </attr>
      <attr floatlength="0" name="REGION_ID" maxlength="6" datatype="String" type="COL">
        <mapingcol datatype="VARCHAR2">REGION_ID</mapingcol>
      </attr>
    </attrlist>
    <relationlist />
    <oplist />
  </sysbo>
</sysbolist>
```

### 7.3 标准模式 — 配置表

> 场景：通用类型配置表，数据源 `{config_ds}`，无 PK 标记

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sysbolist>
  <sysbo datasource="{config_ds}" name="BO{ConfigEntity}" mainattr="TYPE_CODE">
    <mapingenty type="table">DOMAIN_TYPE_CONFIG</mapingenty>
    <datafilter />
    <attrlist>
      <attr floatlength="0" name="TYPE_CODE" maxlength="16" datatype="String" type="COL" remark="类型编码">
        <mapingcol datatype="VARCHAR2">TYPE_CODE</mapingcol>
      </attr>
      <attr floatlength="0" name="TYPE_NAME" maxlength="256" datatype="String" type="COL" remark="类型名称">
        <mapingcol datatype="VARCHAR2">TYPE_NAME</mapingcol>
      </attr>
    </attrlist>
    <relationlist />
    <oplist />
  </sysbo>
</sysbolist>
```

### 7.4 POJO 模式

> 场景：非 DataContainer 映射表，数据源 `{pojo_ds}`，POJO Bean

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sysbolist>
  <sysbo datasource="{pojo_ds}" name="BO{Entity}PojoBean" mainattr="ID">
    <mapingenty type="table">{table_name}</mapingenty>
    <datafilter />
    <attrlist>
      <attr floatlength="0" name="ID" maxlength="20" datatype="Integer" type="PK" remark="记录id">
        <mapingcol datatype="INT">ID</mapingcol>
      </attr>
      <attr floatlength="0" name="ENTITY_NAME" maxlength="255" datatype="String" type="COL" remark="实体名称">
        <mapingcol datatype="VARCHAR">ENTITY_NAME</mapingcol>
      </attr>
      <attr floatlength="0" name="CREATE_DATE" maxlength="50" datatype="DateTime" type="COL" remark="录入时间">
        <mapingcol datatype="DATE">CREATE_DATE</mapingcol>
      </attr>
      <attr floatlength="0" name="STATE" maxlength="10" datatype="String" type="COL" remark="状态">
        <mapingcol datatype="VARCHAR">STATE</mapingcol>
      </attr>
    </attrlist>
    <relationlist />
    <oplist />
  </sysbo>
</sysbolist>
```

---

## 8. 生成检查清单

| # | 检查项 | 适用模式 |
|---|--------|---------|
| 1 | `.bo` 文件路径与 `m_boName` 包路径一致（不要求与 Bean 类路径一致） | 全部 |
| 2 | `name` 属性与 `m_boName` 最后一段一致 | 全部 |
| 3 | 标准模式 `name` 不以 `Bean` 结尾 | 标准 |
| 4 | `datasource` 指向正确的物理库（注意三层优先级，.bo 级别可覆盖映射） | 全部 |
| 5 | `datasource` 不硬编码环境专属分片号（反例：`{shard_ds}570574`），使用项目配置的逻辑名（如 `{shard_ds}1`） | 全部 |
| 6 | `mainattr` 指向主键或业务主属性字段名（查询类 BO 可选） | 全部 |
| 7 | `<mapingenty>` 表名正确（分表用 `{}`，非分表直接写；Oracle 大写，PostgreSQL 小写） | 全部 |
| 8 | 每个 `<attr>` 的 `name`、`datatype`、`type` 均已填写 | 全部 |
| 9 | `<mapingcol>` 的 `datatype` 与目标数据库实际列类型一致 | 全部 |
| 10 | `<mapingcol>` 文本内容（列名）与数据库列名一致（Oracle 大写） | 全部 |
| 11 | `type="PK"` 的字段数量和位置与数据库主键约束一致 | 全部 |
| 12 | 枚举字段的 `remark` 包含完整枚举值说明 | 全部 |
| 13 | `<relationlist>` 和 `<oplist>` 保留为空元素 | 全部 |
| 14 | XML 编码声明为 `UTF-8` | 全部 |
| 15 | `datasource` 值小写（禁止 `SO1`，使用 `so1`） | 全部 |
