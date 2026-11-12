<!--
【文档说明】
承载内容：BSV 层通过统一能开 OPF 客户端调用能力开放平台的代码模式骨架。
适用范围：apply 编码和 code review 阶段用于新增能开 OPF 接口方法。
不负责：CBOSS DSMP 直连（参见 `CBOSS DSMP调用模式（cboss-dsmp-call-pattern）.md`）；能开路由编号清单维护（由能开平台侧维护）；OPF 客户端实现本身（属于 crm-base 类共享组件库）。
填充指引：模板仅给出代码骨架与通用约定；具体业务对象名、路由编号、必填字段、响应节点名以目标项目的能开接口文档为准。
加载建议：涉及 `IOpfClientPublicSV`、`invokeOpfClientOfUppercase`、`INTERFACEMETHOD`、OPF 路由编号、在 BSV 层新增能开接口方法时加载。
-->
# 能开 OPF 调用模式（OPF Call Pattern）

> **通用化说明**：能开 OPF（能力开放平台）是中国移动集团规范的业务能力开放接口平台。BSV 层通过共享基础组件库中的统一 OPF 客户端调用平台。本骨架展示标准调用模式；具体业务对象名、OPF 路由编号、响应节点名以目标项目的"能开接口文档"为准。

## 何时加载

当前问题涉及以下关键词时加载本文：

- `IOpfClientPublicSV`、`invokeOpfClientOfUppercase`、`invokeOpfClient`
- `INTERFACEMETHOD`、OPF 路由编号、能开 OPF 接口
- 在 BSV 层新增能开接口方法

不适用：

- CBOSS DSMP 直连 → 参见 `CBOSS DSMP调用模式（cboss-dsmp-call-pattern）.md`
- 开通系统 `I_OPEN_*` 配置表调用 → 参见开通系统接口相关文档

## 真实来源参考

> 模板不绑定具体仓库；项目实例应基于目标仓库的"BSV CSF 接口实现类"和 `crm-base/utils-common` 类共享组件库中的 `IOpfClientPublicSV` 接口做本地化裁剪。

## 职责边界

| 本组件负责 | 本组件不负责 |
|-----------|------------|
| 组装 OPF 请求（`PARAM` + `INTERFACEMETHOD`） | 解析 OPF 路由配置（由能开侧维护） |
| 调用 `IOpfClientPublicSV.invokeOpfClientOfUppercase` / `.invokeOpfClient` | 维护 OPF 路由编号清单（从接口文档获取） |
| 逐层解析嵌套响应（root → result → RESPONSE → RETINFO） | 修改 `IOpfClientPublicSV` 实现（共享组件库，改动前评估影响） |
| 聚合外部数据 + 内部数据（可选） | 路由到非能开 OPF 的外部系统 |

## 组件元信息

| 要素 | 说明 |
|------|------|
| 基类/接口 | 自定义 `I{XXX}SV` 接口（不强制继承） |
| 实现包路径 | 项目既定的 BSV 业务包 `impl/` 目录 |
| 核心方法签名 | 遵循 CSV/SV 通用签名约定（见 `接口设计规范 §2.1`）：`public Map {方法名}(Map input) throws Exception` |

## 通用代码骨架

```java
// === CSF 接口（interfaces 包）===
public interface I[XXX]SV {
    Map [methodName](Map input) throws Exception;
}

// === CSF 实现（impl 包）===
public class [XXX]SVImpl implements I[XXX]SV {
    private static transient Log log = LogFactory.getLog([XXX]SVImpl.class);

    @Override
    public Map [methodName](Map input) throws Exception {
        log.error("{center}_I[XXX]SV_[methodName]入参:" + input.toString());
        String rspCode = "0000", rspDesc = "";
        Map result = new HashMap();
        // Map bizData = null; // 仅需要返回业务数据时保留

        // Step 2: 组装请求（PARAM 透传，INTERFACEMETHOD 从 OPF 接口文档取）
        Map inParam = new HashMap();
        inParam.put("PARAM", input);
        inParam.put("INTERFACEMETHOD", "[OPF_ROUTE_CODE]");

        try {
            // Step 3: 调用（invokeOpfClientOfUppercase 对参数键做大写转换，见裁剪指南）
            IOpfClientPublicSV opfClient = ServiceFactory.getService(IOpfClientPublicSV.class);
            IData retInfo = opfClient.invokeOpfClientOfUppercase(inParam).getData(ParamOutConst.resultInfo);

            // Step 4: 双层解析，每层必须 MapUtil.isNotEmpty() 判空
            // 路径：root.respCode("00000"/"0") → result → RESPONSE → RETINFO.RspCode("0000")
            // bizData = MapUtils.getMap(retInfos, "[业务节点名]"); // 节点名从 OPF 接口文档取

        } catch (Exception e) {
            log.error("{center}_I[XXX]SV_[methodName] 异常", e);
            rspCode = "2998"; rspDesc = "调用OPF接口发生异常";
        }

        // Step 5: [可选] 内部数据补充（ServiceFactory 获取相关查询 SV）

        result.put("RspCode", rspCode);
        result.put("RspDesc", rspDesc);
        // result.put("[业务数据键]", bizData);
        log.error("{center}_I[XXX]SV_[methodName]出参:" + result);
        return result;
    }
}
```

## 占位变量说明

| 占位符 | 含义 | 替换规则 |
|--------|------|---------|
| `[XXX]` | 接口/类业务名 | 按需求中的业务对象命名 |
| `[methodName]` | 方法名 | 与 CSF serviceCode 中的方法名一致 |
| `[OPF_ROUTE_CODE]` | OPF 路由编号 | 从能开接口文档获取，格式如 `OPF_{center}_{module}_{action}_{seq}` |
| `[业务节点名]` | RETINFO 下的业务数据节点名 | 从 OPF 接口文档获取 |
| `{center}` | 调用方中心编码 | 用目标仓库中心编码替换（CSF serviceCode 前缀） |

## 裁剪指南

| 条件 | 裁剪动作 |
|------|---------|
| 不需要内部数据补充 | 删除 Step 5（内部查询块） |
| 响应只需成功/失败标志 | 删除业务节点提取，只返回 `{RspCode, RspDesc}`；删除 `bizData` 声明 |
| 扩展已有接口（如 `I{XXX}SV` 加方法） | 只在接口和 Impl 各加一个方法 |
| 多次 OPF 调用聚合 | 在同一方法内顺序多次调用，修改 `interfaceMethod` 后复用 Step 2–4 |
| OPF 接口要求参数保持原始大小写 | Step 3 改用 `.invokeOpfClient(inParam)` 代替 `.invokeOpfClientOfUppercase(inParam)`；查 OPF 接口文档确认是否大小写敏感 |

裁剪原则：

- Step 1（日志）、Step 2（参数组装）、Step 3（OPF 调用）、Step 4（嵌套解析）、Step 6（组装返回）为固定必留步骤
- Step 5（内部数据补充）按业务需要增删
- `bizData` 变量仅在需要返回业务数据时保留，否则删除声明及 Step 6 中的引用

## 编码约定

- 日志级别统一用 `log.error()`（项目约定，不论级别）
- 空值安全：每层解析前 `MapUtil.isNotEmpty()` 判空，不直接 `get`
- 错误码：平台成功 `"00000"/"0"`，业务成功 `"0000"`，异常 `"2998"`
- **所有 SV/DAO 实例获取**统一通过 `ServiceFactory.getService(IXxxSV.class)` 或 `ServiceFactory.getService(IXxxDAO.class)`，**禁止直接 `new XxxSVImpl()` 或 `new XxxDAOImpl()`**。此规则不仅适用于外部系统客户端（如 `IOpfClientPublicSV`），同样适用于同模块内自定义 SV 的互调。
- 方法签名遵循 CSV/SV 通用约定（`接口设计规范 §2.1`）：`Map {方法名}(Map input) throws Exception`

## 编码前确认

- [ ] OPF 路由编号已从能开接口文档确认
- [ ] 业务数据节点名（RETINFO 下）已从接口文档确认
- [ ] **请求参数已对照 api-catalog（或接口规范文档）逐字段组装**：所有"是否必填=是"的字段均已在 `PARAM` Map 中赋值，且字段来源明确（入参传递 / DAO 查询 / 订单上下文），不允许仅传入内部标识而遗漏接口规范要求的业务字段
- [ ] 在工作流/异步组件中调用时，已确认字段值的获取路径（可能需要先从订单表 / 实例表查出业务字段再拼装）

## 检查点

- [ ] `PARAM` 和 `INTERFACEMETHOD` 均已放入 `inParam`
- [ ] `invokeOpfClientOfUppercase(inParam).getData(ParamOutConst.resultInfo)` 正确获取 retInfo
- [ ] 双层成功判断：`root.respCode`（00000/0）+ `RETINFO.RspCode`（0000）
- [ ] 每层解析前有判空
- [ ] 异常 catch 后设置 `rspCode = "2998"` 且不静默吞掉
- [ ] 入参/出参均有 `log.error()` 日志

## 反模式

- **混用 `invokeOpfClient` 和 `invokeOpfClientOfUppercase`**：后者对请求参数做大写转换，两者行为不同，选择时需查 OPF 接口文档确认
- **只判断平台层 respCode 不判断业务层 RspCode**：两层含义不同，必须都判断
- **不判空直接链式 getMap**：嵌套 Map 中任一层为 null 会 NPE
- **硬编码 OPF 路由编号为字符串常量但未注释来源**：难以维护，应注释路由编号含义和来源文档

## 关联文档

- `接口设计规范 §2.1 CSV/SV 对外方法签名约定`
- `接口设计规范 §八 CSF 服务编码（serviceCode）规范与验证`
- `设计手册/能开OPF接口调用（opf-integration）.md`（项目实例补充）