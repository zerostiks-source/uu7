<!--
【文档说明】
承载内容：AppFrame2 数据层规范，承载 BO/Engine/DAO/SV/IValue 架构、职责和生成检查项。
适用范围：后端 AppFrame2/CSF 设计、任务拆分、编码和 review 阶段使用。
填充指引：由目标仓库代码、defaults.xml、.bo、服务注册、GitNexus 和 context-update 补充；通用框架规则可保留，项目特定值必须占位或注明证据。
加载建议：命中 AppFrame2、BO、Engine、DAO、SV、服务注册、数据源或编码风格时加载。
-->
## 十一、数据驱动层编码规范（AppFrame2）

> 本节规范适用于基于 AppFrame2 框架的数据驱动层代码，包括 BO 层、DAO 层、Service 层和 IValues 数据接口层。具体包路径以目标项目为准。
> 所有文件统一使用 **UTF-8** 编码。

### 11.1 四层架构概览

```
┌──────────────────────────────────────────────────────────┐
│  Service 层 (SV)  — 业务逻辑封装                         │
│    I{EntityName}SV / {EntityName}SVImpl                  │
├──────────────────────────────────────────────────────────┤
│  DAO 层           — 数据访问                              │
│    I{EntityName}DAO / {EntityName}DAOImpl                │
├──────────────────────────────────────────────────────────┤
│  BO 层            — 业务对象（Bean + Engine）             │
│    BO{EntityName}Bean / BO{EntityName}Engine             │
├──────────────────────────────────────────────────────────┤
│  IValues 层       — 数据接口                              │
│    IBO{EntityName}Value                                  │
└──────────────────────────────────────────────────────────┘
```

### 11.2 目录结构与包名

> **本项目实际的模块划分与包路径以 [BSV业务服务层编码指南/定位与工程结构](../bsv-coding-guide/定位与工程结构（structure）.md) 为准。** 以下仅说明 AppFrame2 四层组件在典型 BSV 工程模块中的分布规律。

在典型 AppFrame2 BSV 项目中，AppFrame2 各层组件按职责拆分到不同工程模块：

| 层 | 所属工程模块 | 典型包路径模式 | 说明 |
|---|---|---|---|
| Bean / Engine / .bo | `structure/` | `{base_package}.mgr.{业务域}.bo` | BO 数据结构定义，通常由框架生成 |
| IValues 接口 | `structure/` | 同 Bean 所在包的 `ivalues` 子包 | 数据接口定义 |
| DAO 接口 | `ability/` | `{base_package}.mgr.{业务域}.dao.interfaces` 或 `dao.{逻辑库}.interfaces` | 数据访问接口（具体按同业务域既有代码确认） |
| DAO 实现 | `ability/` | `{base_package}.mgr.{业务域}.dao.{逻辑库}.impl` | 如 `dao.{master_suffix}.impl`、`dao.{shard_suffix}.impl` |
| SV（mgr 级）接口 | `ability/` | `{base_package}.mgr.{业务域}.service.interfaces` | 数据能力 SV |
| SV（mgr 级）实现 | `ability/` | `{base_package}.mgr.{业务域}.service.impl` | 基础 CRUD 封装 |

> `{业务域}` 为业务域包名。`{逻辑库}` 为数据源逻辑库子包，决定 DAO 操作的数据源路由，详见 `defaults.xml` 映射和 [服务注册配置](服务注册配置（service-registration）.md)。

新增 AppFrame2 实体时，`{业务域}` 和 `{逻辑库}` 需根据既有同类代码确定，禁止自行创建新的顶级包路径。`{EntityName}` 为表名驼峰式命名（如 `OrderInfo`、`ResExchangeConfig`）。

### 11.3 类命名约定

| 类型         | 命名格式                 | 示例                 |
| ------------ | ------------------------ | -------------------- |
| Bean 类      | `BO{EntityName}Bean`   | `BOComplainBean`   |
| Engine 类    | `BO{EntityName}Engine` | `BOComplainEngine` |
| DAO 接口     | `I{EntityName}DAO`     | `IComplainDAO`     |
| DAO 实现     | `{EntityName}DAOImpl`  | `ComplainDAOImpl`  |
| IValues 接口 | `IBO{EntityName}Value` | `IBOComplainValue` |
| Service 接口 | `I{EntityName}SV`      | `IComplainSV`      |
| Service 实现 | `{EntityName}SVImpl`   | `ComplainSVImpl`   |

### 11.4 数据类型映射

> Oracle + PostgreSQL 完整数据类型映射见 [BO配置文件规范 §3.2](BO配置文件规范（bo-config-spec）.md#32-数据类型映射)。以下为 Bean 代码中常用的 DataType 读写方法速查。

| 数据库类型                       | BO 配置 datatype | Java 类型              | DataType 读取方法            | set 包装方式          |
| -------------------------------- | ---------------- | ---------------------- | ---------------------------- | --------------------- |
| NUMBER(整数)                     | Long             | `long`               | `DataType.getAsLong()`     | `new Long(value)`   |
| NUMBER(小数)                     | —               | `double`             | `DataType.getAsDouble()`   | `new Double(value)` |
| VARCHAR2 / VARCHAR / CHAR / CLOB | String           | `String`             | `DataType.getAsString()`   | 直接使用              |
| DATE                             | DateTime         | `java.sql.Timestamp` | `DataType.getAsDateTime()` | 直接使用              |

### 11.5 BO 层 — Bean 类

> **本节仅描述标准模式（DataContainer 继承）的 Bean 编码规范。** POJO 模式与纯元数据模式的 Bean 不使用此模板，详见 [BO配置文件规范 §2](BO配置文件规范（bo-config-spec）.md#2-三种-bo-模式)。

**继承关系：** `extends DataContainer implements DataContainerInterface`

**结构要点：**

1. **`m_boName`** — 完整 BO 类名字符串：`"{base_package}.mgr.{业务域}.bo.BO{EntityName}"`（按实际包路径）
2. **`S_TYPE`** — 静态初始化块中通过 `ServiceManager.getObjectTypeFactory().getInstance(m_boName)` 获取
3. **字段常量** — 格式 `public final static String S_{FieldName} = "{COLUMN_NAME}";`（FieldName 首字母大写驼峰，COLUMN_NAME 为数据库原始列名大写）
4. **构造函数** — `public BO{EntityName}Bean() throws AIException { super(S_TYPE); }`

**每个字段必须固定生成 5 个方法：**

| 方法            | 签名（以 long 类型 `Id` 为例）                                             | 说明       |
| --------------- | ---------------------------------------------------------------------------- | ---------- |
| init            | `void initId(long value)` → `this.initProperty(S_Id, new Long(value))`  | 初始化属性 |
| set             | `void setId(long value)` → `this.set(S_Id, new Long(value))`            | 设置属性   |
| setNull         | `void setIdNull()` → `this.set(S_Id, null)`                             | 置空       |
| get             | `long getId()` → `DataType.getAsLong(this.get(S_Id))`                   | 获取当前值 |
| getInitialValue | `long getIdInitialValue()` → `DataType.getAsLong(this.getOldObj(S_Id))` | 获取初始值 |

> String 类型的 init/set 方法直接传入值，无需包装类。Timestamp 类型同理。

### 11.6 BO 层 — Engine 类

Engine 是 BO 层的静态工具类，封装对单张表的所有 CRUD 操作，所有方法均为 `static`。

> Engine 标准方法的完整签名目录、返回类型以及详细调用模式和代码示例见 [Engine层代码模板](Engine层代码模板（engine-code-template）.md)。

常用方法速查：`getBeans(condition, map)` 条件查询 / `getBean(long id)` 按主键查单条（未找到时返回空 Bean 而非 null） / `getBeansCount(condition, map)` 计数 / `save(bean)` 保存（自动判断 INSERT/UPDATE） / `saveBatch(beans)` 批量保存 / `getNewId()` 获取序列 ID / `getSysDate()` 系统时间。

> 所有涉及 `Connection` 的方法通过 `ServiceManager.getSession().getConnection()` 获取，`finally` 块中确保连接释放。

### 11.7 BO 配置文件（.bo）

`.bo` 文件是 AppFrame2 ORM 元数据描述文件，定义 BO 对象与数据库表的映射关系。

> ⚠️ **完整 `.bo` XML Schema（含 `floatlength`、`maxlength`、`type`、`<mapingcol>` 等必填属性）、三种 BO 模式（标准/POJO/纯元数据）、datasource 三层解析优先级、常用 datasource 值列表和多种完整示例见 [BO配置文件规范](BO配置文件规范（bo-config-spec）.md)**。生成 .bo 文件时必须参考 BO配置文件规范，不可使用本节简化描述。

### 11.8 IValues 接口

**继承：** `extends DataStructInterface`

接口仅定义：

- 与 Bean 相同的字段常量 `S_{FieldName}`
- 每个字段的 getter / setter 方法签名

```java
public interface IBO{EntityName}Value extends DataStructInterface {
    public final static String S_{FieldName} = "{COLUMN_NAME}";
    public {Type} get{FieldName}();
    public void set{FieldName}({Type} value);
}
```

### 11.9 DAO 层

**接口方法风格（以目标仓库既有代码为准）：**

DAO 接口方法应使用强类型入参（非 Map），保存方法直接传 Bean（非 IValue 接口）。以下为参考实际代码归纳的典型方法签名：

```java
public interface I{EntityName}DAO {
    BO{EntityName}Bean[] query{EntityName}(Criteria criteria, String regionId) throws Exception;
    BO{EntityName}Bean[] query{EntityName}List(String condition, Map parameter) throws Exception;
    void save{EntityName}(BO{EntityName}Bean bean) throws Exception;
    long getNewId(String regionId) throws Exception;
    int query{EntityName}Count(String condition, Map parameter) throws Exception;
}
```

> 具体方法签名应参考同业务域既有 DAO 接口确定，以上仅为常见模式。

**实现要点：**

- 查询：用 `StringBuilder` 构建条件，调用 `BO{EntityName}Engine.getBeans()`；也可使用 `Criteria` 方式构建查询
- 保存：调用 `BO{EntityName}Engine.save()` 或 `saveBatch()`
- **桥接保存**：部分涉及跨库/跨模块数据同步的场景，可能需要**同时调用** `BeanBridgeHelper.save(bean)` 和 `BO{EntityName}Engine.save(bean)`。是否需要桥接保存取决于目标表的业务场景，新增时需参考同业务域 DAO 的既有保存方法
- 删除：使用逻辑删除（设状态为失效），再 `save()` 持久化
- 计数：调用 `BO{EntityName}Engine.getBeansCount()`
- **CenterFactory**：涉及分库表（SO 库）的 DAO 方法，可在方法内部基于入参自行设置 `CenterFactory`（try-finally），也可由上层 SV 设置

> 完整 DAO 实现类模板和各种查询/保存模式见 [Engine层代码模板](Engine层代码模板（engine-code-template）.md)。

### 11.10 Service 层

**接口标准方法：** 与 DAO 接口方法一致，写操作可额外声明 `RemoteException`。

**实现要点：**

- 通过 `ServiceFactory.getService(I{EntityName}DAO.class)` 获取 DAO 实例
- DAO 实例应在**方法内按需获取**（局部变量），**禁止**作为类成员字段持有——避免类加载时机问题，且与框架的请求级生命周期管理保持一致
- **禁止** `new` DAO 实现类——`ServiceFactory` 负责实例管理和框架级拦截（事务、日志等），直接 `new` 会绕过这些机制
- **禁止** 使用 `FwzlToCsfServiceFactory.getService()`（历史遗留，新代码一律使用 `ServiceFactory`）
- **禁止** 在 SVImpl 中 import DAO 实现类（`dao.impl.*`），只应 import DAO 接口（`dao.interfaces.*`）；若发现 SVImpl 导入了 `*DAOImpl`，即为代码异味
- 方法实现委托给 DAO 层，可在此层添加业务逻辑

```java
// 正确 — 在方法内通过 ServiceFactory 按需获取 DAO（局部变量）
public class {EntityName}SVImpl implements I{EntityName}SV {
    @Override
    public IBO{EntityName}Value[] query{EntityName}List(Map input) throws Exception {
        I{EntityName}DAO dao = (I{EntityName}DAO) ServiceFactory.getService(I{EntityName}DAO.class);
        return dao.query{EntityName}List(input);
    }
}
```

```java
// 错误 — 禁止直接 new DAO 实现类，禁止作为类字段持有
public class BadExampleSVImpl implements IBadExampleSV {
    private IXxxDAO dao = new XxxDAOImpl();  // 违规：new 实现类 + 字段持有
}
```

### 11.11 代码生成检查清单

| #  | 检查项                                                                                         |
| -- | ---------------------------------------------------------------------------------------------- |
| 1  | 所有文件生成在正确模块下（structure / ability），包名与模块对应                                 |
| 2  | Bean 类正确继承 `DataContainer` 并实现 `DataContainerInterface`（标准模式不实现 IValues 接口） |
| 3  | Bean 类包含构造函数 `public BO{EntityName}Bean() throws AIException { super(S_TYPE); }`        |
| 4  | Bean 类每个字段固定 5 个方法（init/set/setNull/get/getInitialValue）                           |
| 5  | Engine 类包含所有标准 CRUD 方法                                                                |
| 6  | DAO 接口与实现类方法签名一致，保存方法入参参考同业务域既有 DAO                                 |
| 7  | Service 接口与实现类方法签名一致                                                               |
| 8  | IValues 接口字段常量与 Bean 类一致                                                             |
| 9  | 字段类型映射正确（NUMBER→long、VARCHAR→String、DATE→Timestamp）                             |
| 10 | 所有引用类可正确导入                                                                           |
| 11 | BO 配置文件 `.bo` 的 `datasource`、`mainattr`、字段映射与数据库表一致（详见 BO配置文件规范）   |
