<!--
【文档说明】
承载内容：Engine/DAO 代码模板，承载查询、分页、保存、批量、自定义 SQL 和检查项。
适用范围：后端 AppFrame2/CSF 设计、任务拆分、编码和 review 阶段使用。
填充指引：由目标仓库代码、defaults.xml、.bo、服务注册、GitNexus 和 context-update 补充；通用框架规则可保留，项目特定值必须占位或注明证据。
加载建议：命中 AppFrame2、BO、Engine、DAO、SV、服务注册、数据源或编码风格时加载。
-->
# Engine 层代码模板

> **Engine** 是 AppFrame2 框架中 BO 层的静态工具类，封装了对单张数据库表的所有 CRUD 操作。每个 BO 实体对应一个 Engine 类，所有方法均为 **static**。DAO 层通过调用 Engine 的静态方法完成数据库访问。

---

## 1. Engine 标准方法目录

| 方法签名 | 作用 | 返回类型 |
|---------|------|---------|
| `getBeans(String condition, Map parameter)` | 条件查询 | `BO{Entity}Bean[]` |
| `getBeans(String[] cols, String condition, Map parameter, int startNum, int endNum, boolean isShowFK)` | 分页查询（选列、外键） | `BO{Entity}Bean[]` |
| `getBeans(DataContainerInterface dc)` | 按 DataContainer 属性查询 | `BO{Entity}Bean[]` |
| `getBeans(Criteria sql)` | Criteria 条件查询 | `BO{Entity}Bean[]` |
| `getBean(long id)` | 按主键查单条 | `BO{Entity}Bean` |
| `getBeansCount(String condition, Map parameter)` | 条件计数 | `int` |
| `save(BO{Entity}Bean aBean)` | 保存单条 | `void` |
| `save(BO{Entity}Bean[] aBeans)` | 保存数组 | `void` |
| `save(IBO{Entity}Value aValue)` | 保存 IValue | `void` |
| `saveBatch(BO{Entity}Bean[] aBeans)` | 批量保存 | `void` |
| `getBeansFromSql(String sql, Map parameter)` | 自定义 SQL 查询 | `BO{Entity}Bean[]` |
| `getBeansFromQueryBO(String sourceBO, Map parameter)` | QueryBO 查询 | `BO{Entity}Bean[]` |
| `getNewId()` | 获取新 ID | `BigDecimal` |
| `getSysDate()` | 获取系统日期 | `Timestamp` |
| `transfer(IBO{Entity}Value value)` | IValue → Bean 转换 | `BO{Entity}Bean` |
| `wrap(DataContainerInterface, Map, boolean)` | 包装 DataContainer | — |
| `copy(DataContainerInterface, Map, boolean)` | 复制 DataContainer | — |

---

## 2. DAO 层调用 Engine 的标准模式

### 2.1 条件查询（StringBuilder + HashMap）

**最常用的查询模式**。使用 `StringBuilder` 构建 WHERE 条件，`HashMap` 存放命名参数。

```java
public BO{Entity}Bean[] query{Entity}List(String entityId, int state) throws Exception {
    HashMap map = new HashMap();
    StringBuilder sql = new StringBuilder();

    sql.append(IBO{Entity}Value.S_State).append(" = :state ");
    map.put("state", Integer.valueOf(state));

    if (StringUtils.isNotBlank(entityId)) {
        sql.append(" AND ").append(IBO{Entity}Value.S_EntityId).append(" = :entityId ");
        map.put("entityId", Long.valueOf(entityId));
    }

    return BO{Entity}Engine.getBeans(sql.toString(), map);
}
```

**要点**：
- 使用 `IBO{Entity}Value.S_{FieldName}` 常量引用列名，**禁止**硬编码列名字符串
- 参数名使用 `:p_xxx` 或 `:fieldName` 格式（命名参数，非位置参数）
- 参数值使用正确的包装类型：`Long.valueOf()`、`Integer.valueOf()`
- 字符串条件判断使用 `StringUtils.isNotBlank()`

### 2.2 分页查询

```java
public BO{Entity}Bean[] query{Entity}Page(String entityId,
        int startRowIndex, int endRowIndex) throws Exception {
    HashMap map = new HashMap();
    StringBuilder sql = new StringBuilder();
    sql.append("1 = 1");

    if (StringUtils.isNotBlank(entityId)) {
        sql.append(" AND ").append(IBO{Entity}Value.S_EntityId).append(" = :entityId ");
        map.put("entityId", Long.valueOf(entityId));
    }

    sql.append(" ORDER BY ").append(IBO{Entity}Value.S_CreateDate).append(" DESC");

    // 分页参数：null=不选列、sql条件、参数Map、起始行、结束行、false=不带外键统计
    return BO{Entity}Engine.getBeans(null, sql.toString(), map,
            startRowIndex, endRowIndex, false);
}
```

**分页方法签名解读**：
```java
getBeans(String[] cols,     // 选择列（null=全部列）
         String condition,  // WHERE 条件
         Map parameter,     // 命名参数
         int startNum,      // 起始行号（1-based）
         int endNum,        // 结束行号
         boolean isShowFK)  // 是否显示外键（通常 false）
```

### 2.3 计数查询

```java
public int query{Entity}Count(String entityId) throws Exception {
    HashMap map = new HashMap();
    StringBuilder sql = new StringBuilder();
    sql.append("1 = 1");

    if (StringUtils.isNotBlank(entityId)) {
        sql.append(" AND ").append(IBO{Entity}Value.S_EntityId).append(" = :entityId ");
        map.put("entityId", Long.valueOf(entityId));
    }

    return BO{Entity}Engine.getBeansCount(sql.toString(), map);
}
```

### 2.4 Criteria 方式查询

**替代 StringBuilder 的面向对象查询方式**，适用于条件组合较复杂、需要类型安全构建的场景。

```java
public BO{Entity}Bean query{Entity}ById(long id) throws Exception {
    Criteria criteria = new Criteria();
    criteria.addEqual(BO{Entity}Bean.S_Id, id);
    criteria.addLESSThan(BO{Entity}Bean.S_EffectiveDate,
            BO{Entity}Engine.getSysDate());
    criteria.addGREATEREqual(BO{Entity}Bean.S_ExpireDate,
            BO{Entity}Engine.getSysDate());

    BO{Entity}Bean[] beans = BO{Entity}Engine.getBeans(criteria);
    if (beans != null && beans.length > 0) {
        return beans[0];
    }
    return null;
}
```

**Criteria 常用方法**：

| 方法 | SQL 等价 |
|------|---------|
| `addEqual(field, value)` | `field = value` |
| `addNotEqual(field, value)` | `field != value` |
| `addLESSThan(field, value)` | `field < value` |
| `addLESSEqual(field, value)` | `field <= value` |
| `addGREATERThan(field, value)` | `field > value` |
| `addGREATEREqual(field, value)` | `field >= value` |
| `addLike(field, value)` | `field LIKE value` |
| `addIn(field, values)` | `field IN (...)` |
| `addIsNull(field)` | `field IS NULL` |
| `addIsNotNull(field)` | `field IS NOT NULL` |

---

## 3. 保存操作模式

### 3.1 单条保存（含 ID 生成）

**模式 A：Engine 内置序列（简单场景）**

```java
public long save{Entity}Info(BO{Entity}Bean bean) throws Exception {
    long id = BO{Entity}Engine.getNewId().longValue();
    bean.setId(id);
    BO{Entity}Engine.save(bean);
    return id;
}
```

**模式 B：命名序列 + 区域编码组合（参考目标项目既有代码）**

```java
public long getNewId(String regionId) throws Exception {
    if (StringUtils.isBlank(regionId)) {
        ExceptionUtil.throwBusinessException("...", "生成标识区域编号不能为空!");
    }
    long sequence = ServiceManager.getIdGenerator()
        .getNewId(("STANDARD_{ENTITY}_ID_" + regionId).toUpperCase()).longValue();
    String fixedSequence = String.format("%015d", sequence);
    return Long.parseLong(regionId + fixedSequence);
}
```

> 新增实体时需先确认目标表的 ID 生成规则（是否包含区域前缀、序列名命名约定），参考同业务域 DAO 的既有 `getNewId` 实现。

### 3.2 批量保存（循环赋 ID）

```java
public void save{Entity}Batch(BO{Entity}Bean[] beans) throws Exception {
    for (int i = 0; i < beans.length; i++) {
        beans[i].setId(BO{Entity}Engine.getNewId().longValue());
        beans[i].setDoneDate(BO{Entity}Engine.getSysDate());
    }
    BO{Entity}Engine.saveBatch(beans);
}
```

### 3.3 桥接保存

保存实体资料且涉及数据同步的场景，可能需要**同时调用** `BeanBridgeHelper.save()` 和 `Engine.save()`：

```java
public void save{Entity}(BO{Entity}Bean bean) throws Exception {
    try {
        CenterFactory.setCenterInfoByTypeAndValue(
            CenterUtil.REGION_ID, String.valueOf(bean.getRegionCode()));
        BeanBridgeHelper.save(bean);
        BO{Entity}Engine.save(bean);
    } finally {
        CenterFactory.setCenterInfoEmpty();
    }
}
```

> 是否需要桥接保存取决于目标表的业务场景，新增时需参考同业务域 DAO 的既有保存方法。

### 3.4 查询后更新

```java
public void update{Entity}Status(long id, int newStatus) throws Exception {
    IBO{Entity}Value value = BO{Entity}Engine.getBean(id);

    value.setStatus(newStatus);
    value.setModifyDate(BO{Entity}Engine.getSysDate());

    // 框架自动判断 insert/update
    BO{Entity}Engine.save(value);
}
```

---

## 4. 自定义 SQL 查询

当标准 `getBeans()` 无法满足需求（如多表关联、子查询、聚合）时，使用 `getBeansFromSql()`：

```java
public IBO{Entity}Value[] queryWithCustomSql(long entityId) throws Exception {
    HashMap map = new HashMap();
    StringBuilder sql = new StringBuilder();
    sql.append("SELECT a.* FROM {TABLE_A} a ");
    sql.append("INNER JOIN {TABLE_B} b ON a.ID = b.A_ID ");
    sql.append("WHERE a.ENTITY_ID = :entityId ");
    sql.append("AND b.STATUS = :status");
    map.put("entityId", Long.valueOf(entityId));
    map.put("status", Integer.valueOf(1));

    return BO{Entity}Engine.getBeansFromSql(sql.toString(), map);
}
```

> 自定义 SQL 的 SELECT 列必须与 `.bo` 文件中定义的字段对应，以便框架正确将结果映射为 Bean。

---

## 5. DAO → Engine 交互关系

### 5.1 职责分工

| 层 | 职责 |
|----|------|
| **DAO** | 接收业务参数 → 构建 WHERE 条件 → 调用 Engine 方法 → 返回结果 |
| **Engine** | 封装 ORM 操作 → 连接数据库 → 执行 SQL → 返回 Bean/IValues |

### 5.2 DAO 内获取其他服务

DAO 实现类中可以通过 `ServiceFactory.getService()` 获取**其他 DAO 或 SV**：

```java
public void doComplexOperation(IBO{Entity}Value value) throws Exception {
    ISoCommDAO commDao = (ISoCommDAO) ServiceFactory.getService(ISoCommDAO.class);

    long newId = commDao.getNewIdBySeqName("SEQ_{ENTITY}");
    value.setId(newId);

    IExternalCapabilitySV externalSV = (IExternalCapabilitySV) ServiceFactory.getService(IExternalCapabilitySV.class);
    // ...

    BO{Entity}Engine.save(value);
}
```

---

## 6. 完整 DAO 实现类模板

```java
package {base_package}.mgr.{业务域}.dao.{逻辑库}.impl;

import java.util.HashMap;
import org.apache.commons.lang.StringUtils;
import {base_package}.mgr.{业务域}.bo.BO{Entity}Engine;
import {base_package}.mgr.{业务域}.dao.interfaces.I{功能}DAO;
import {base_package}.mgr.{业务域}.ivalues.IBO{Entity}Value;

public class {功能}DAOImpl implements I{功能}DAO {

    @Override
    public BO{Entity}Bean[] query{Entity}List(String entityId,
            int startRowIndex, int endRowIndex) throws Exception {
        HashMap map = new HashMap();
        StringBuilder sql = new StringBuilder();
        sql.append("1 = 1");

        if (StringUtils.isNotBlank(entityId)) {
            sql.append(" AND ").append(IBO{Entity}Value.S_EntityId)
               .append(" = :entityId ");
            map.put("entityId", Long.valueOf(entityId));
        }

        sql.append(" ORDER BY ")
           .append(IBO{Entity}Value.S_CreateDate).append(" DESC");

        return BO{Entity}Engine.getBeans(null, sql.toString(), map,
                startRowIndex, endRowIndex, false);
    }

    @Override
    public int query{Entity}Count(String entityId) throws Exception {
        HashMap map = new HashMap();
        StringBuilder sql = new StringBuilder();
        sql.append("1 = 1");

        if (StringUtils.isNotBlank(entityId)) {
            sql.append(" AND ").append(IBO{Entity}Value.S_EntityId)
               .append(" = :entityId ");
            map.put("entityId", Long.valueOf(entityId));
        }

        return BO{Entity}Engine.getBeansCount(sql.toString(), map);
    }

    @Override
    public long save{Entity}Info(BO{Entity}Bean bean) throws Exception {
        long id = BO{Entity}Engine.getNewId().longValue();
        bean.setId(id);
        BO{Entity}Engine.save(bean);
        return id;
    }

    @Override
    public void save{Entity}Batch(BO{Entity}Bean[] beans) throws Exception {
        for (int i = 0; i < beans.length; i++) {
            beans[i].setId(BO{Entity}Engine.getNewId().longValue());
        }
        BO{Entity}Engine.saveBatch(beans);
    }

    @Override
    public void update{Entity}Status(long id, int status) throws Exception {
        BO{Entity}Bean bean = BO{Entity}Engine.getBean(id);
        bean.setStatus(status);
        bean.setModifyDate(BO{Entity}Engine.getSysDate());
        BO{Entity}Engine.save(bean);
    }

    @Override
    public void delete{Entity}ById(long id) throws Exception {
        BO{Entity}Bean bean = BO{Entity}Engine.getBean(id);
        bean.setStatus(0);  // 0=失效
        bean.setModifyDate(BO{Entity}Engine.getSysDate());
        BO{Entity}Engine.save(bean);
    }
}
```

---

## 7. 编码风格要点

| # | 要点 |
|---|------|
| 1 | 新代码使用 `StringBuilder`（与目标项目既有代码风格一致）。存量 DAO 中的 `StringBuffer` 无需主动替换 |
| 2 | 条件拼接起始用 `"1 = 1"` 简化后续 `AND` 拼接 |
| 3 | 使用 `IBO{Entity}Value.S_{FieldName}` 常量引用列名 |
| 4 | 参数命名用 camelCase（如 `:entityId`），参数值用对应包装类型 |
| 5 | DAO 方法统一抛出 `throws Exception` |
| 6 | 分页查询 `getBeans` 第 6 个参数 `isShowFK` 通常传 `false` |
| 7 | Engine 的 `save()` 方法自动判断 INSERT/UPDATE — 新对象 INSERT，已有对象 UPDATE |
| 8 | 批量操作前用循环为每条记录赋 ID（`getNewId()`）和系统时间（`getSysDate()`） |
| 9 | 查询单条记录用 `getBeans()` + 取第一个元素，或用 `getBean(id)` 按主键查询 |
| 10 | 删除操作使用逻辑删除（设状态为失效）而非物理删除 |
