<!--
【文档说明】
承载内容：BSV 分层编码规范，承载门面层、业务编排、管理服务、DAO/Engine 和适配层职责。
适用范围：后端 BSV/业务服务层 design、tasks、apply 和 review 阶段使用。
填充指引：由目标仓库 package、调用链、服务注册、defaults.xml、GitNexus 和 context-update 补充；只保留可迁移结构，具体中心和业务名用项目证据填充。
加载建议：任务落到 BSV、业务服务、DAO/BO/Engine、跨中心或分库路由时加载。
-->
# 分层编码规范（Layering）

> 本文只定义 BSV 类工程常见分层和填充规则。具体模块名、包路径、接口后缀、注册方式、异常类、日志类和基础工具必须以目标仓库为准。

---

## 一、分层职责与调用规则

> 分层规范的权威定义见 [核心业务分层模型（core-layered-model）](../../system/核心业务分层模型（core-layered-model）.md)。本节为 BSV 工程实现视角的摘要，以 core-layered-model 为准。

```text
外部调用方 / 页面服务 / 其他中心
  -> CSF/CSV/GW 门面层
    -> 业务编排 SV
      -> 管理服务 / 领域服务
        -> DAO / Engine / BO
      -> 跨中心适配接口
        -> 适配实现 / 远程调用
```

| 层次 | 职责 | 禁止事项 |
|------|------|----------|
| 门面层 | 协议适配、参数校验、异常转换、响应包装 | 承载复杂业务规则或直接写库 |
| 业务编排层 | 编排本中心能力、事务边界、幂等和流程控制 | 直接拼 SQL 或绕过适配层远程调用 |
| 管理/领域服务 | 封装本领域数据操作和领域规则 | 依赖页面协议对象 |
| DAO/Engine | 数据访问、BO/SQL、分库路由内的数据读写 | 承载跨系统流程和页面语义 |
| 适配层 | **封装跨中心/外部系统调用**（权威规则见 core-layered-model）| 让业务层感知远程协议细节 |

---

## 二、业务域分区与包路径

| 项 | 填充方式 |
|----|----------|
| 基础包名 | 从 project-profile、源码目录或既有接口包路径确认 |
| 业务域 | 以目标项目模块、bounded context 或既有 package 命名为准 |
| 接口路径 | 参考同业务域 `interfaces/` 包 |
| 实现路径 | 参考同业务域 `impl/` 包 |
| DAO 路径 | 按逻辑库、数据源或既有 defaults.xml 映射确认 |

---

## 三、标准编码模式

### 3.1 门面层

CSV（CSF 门面）方法签名统一使用 `Map` 裸类型入参和出参，详见 [接口设计规范 §2.1 CSV/SV 对外方法签名约定](../接口设计规范（api-style-guide）.md)。

```java
public class XxxCSVImpl implements IXxxCSV {
    public Map doSomething(Map input) throws Exception {
        try {
            IXxxSV sv = ServiceFactory.getService(IXxxSV.class);
            return sv.doSomething(input);
        } catch (Exception e) {
            // 使用目标项目统一异常转换方式
            throw convertException(e);
        } finally {
            // 清理项目约定的线程上下文
            clearContext();
        }
    }
}
```

### 3.2 业务编排层

SV 业务编排层可使用强类型入参或 `Map`，跟随目标仓库同域既有 SV 风格（不强制统一）。

```java
public class XxxSVImpl implements IXxxSV {
    public Map doSomething(Map input) throws Exception {
        validate(input);
        ensureIdempotent(input);
        DomainResult result = domainService.process(input);
        return buildOutput(result);
    }
}
```

### 3.3 管理服务/DAO 层

```java
public class XxxMgrSVImpl implements IXxxMgrSV {
    public BO{Entity}Bean queryByKey(String key) throws Exception {
        I{Entity}DAO dao = ServiceFactory.getService(I{Entity}DAO.class);
        return dao.queryByKey(key);
    }
}
```

```java
public class {Entity}DAOImpl implements I{Entity}DAO {
    public BO{Entity}Bean queryByKey(String key) throws Exception {
        String condition = "{COLUMN_NAME} = ?";
        Object[] params = new Object[]{key};
        return BO{Entity}Engine.getBean(condition, params);
    }
}
```

### 3.4 跨中心适配层

> 适配层是中心内部 SV（不通过 CSF 对外暴露），入参/出参可以使用强类型。若该适配层的调用入口是 CSV 门面，则 CSV 方法签名仍须为 `Map`，适配层内做参数转换。

```java
public class ExternalCapabilitySVImpl implements IExternalCapabilitySV {
    public Map invoke(Map input) throws Exception {
        // 从 Map 转换为远程调用所需参数
        String raw = remoteCaller.call({SERVICE_CODE}, input);
        Map result = new HashMap();
        result.put("result", raw);
        return result;
    }
}
```

---

## 四、服务实例获取规则 【强制】

**所有 SV、DAO 实例的获取必须通过 `ServiceFactory.getService(Interface.class)`，禁止直接 `new XxxImpl()`。**

此规则覆盖以下全部场景，无一例外：

| 场景 | 正确写法 | 错误写法 |
|------|----------|----------|
| CSV 门面调用 SV | `ServiceFactory.getService(IXxxSV.class)` | `new XxxSVImpl()` |
| SV 编排层调用同模块另一个 SV | `ServiceFactory.getService(IYyySV.class)` | `new YyySVImpl()` |
| SV 调用 DAO | `ServiceFactory.getService(IXxxDAO.class)` | `new XxxDAOImpl()` |
| CSV 门面调用外部系统客户端 SV | `ServiceFactory.getService(IOpfClientPublicSV.class)` | `new OpfClientPublicSVImpl()` |

**原因**：CSF/AppFrame2 框架通过 ServiceFactory 管理服务注册、生命周期、事务上下文和会话传播。直接 `new` 会绕过这些机制，导致事务失效、会话丢失或 DAO 路由异常。

---

## 五、工作流/异步组件调用外部接口规则 【强制】

工作流子流程、ET 后台任务组件、异步消费者中调用外部系统接口时，必须遵守以下规则：

1. **参数完整性**：对照 api-catalog（或接口规范文档）列出目标接口的全部必填字段，逐字段在代码中拼装到请求 Map 中。禁止仅传入内部标识而遗漏接口规范要求的业务字段。
2. **参数来源明确**：工作流上下文往往只有内部业务主键（如订单 ID）和区域标识，其余业务字段（如用户号码 / 卡标识 / 业务类型 / 设备标识等）需从订单表/实例表/用户表通过 DAO 或 CSF 查出后再拼入请求。编码时须注明每个字段的取值来源。
3. **缺失字段处理**：若当前上下文确实无法获取某必填字段，须在 `review-notes.md` 中标记 PENDING，并在代码中以 `// PENDING: 字段 xxx 来源待确认` 注释，禁止静默忽略。

**反模式**：

```java
// ❌ 只传内部业务主键，缺失多个必填字段
Map outboundInput = new HashMap();
outboundInput.put("customerOrderId", customerOrderId);
CenterClient.call("...", outboundInput);

// ✅ 先查出业务字段，再按接口规范逐字段拼装
IData orderInfo = queryOrderInfo(customerOrderId, regionId);
Map outboundInput = new HashMap();
outboundInput.put("reqBizCode", "002");
outboundInput.put("bizType", orderInfo.getString("BIZ_TYPE"));
outboundInput.put("orderId", orderInfo.getString("ORDER_ID"));
outboundInput.put("msisdn", orderInfo.getString("MSISDN"));
// ... 其他接口规范要求字段
CenterClient.call("...", outboundInput);
```

---

## 六、AI 编码检查清单

| # | 检查项 |
|---|--------|
| 1 | 新增逻辑放在正确层次，门面层没有堆业务规则 |
| 2 | 包路径、接口命名、实现命名与同业务域既有代码一致 |
| 3 | DAO/BO/Engine 访问前已确认数据源、路由和事务边界 |
| 4 | 跨中心调用经过适配层封装 |
| 5 | 异常、日志、返回码和上下文清理遵循目标项目约定 |
| 6 | 所有示例中的占位符已替换为源码证据确认的真实值 |
| 7 | **所有 SV/DAO 实例通过 `ServiceFactory.getService()` 获取，无 `new XxxImpl()` 用法** |
| 8 | **调用外部系统接口时，请求参数已对照 api-catalog 逐字段组装，所有必填字段均已填入且来源明确** |