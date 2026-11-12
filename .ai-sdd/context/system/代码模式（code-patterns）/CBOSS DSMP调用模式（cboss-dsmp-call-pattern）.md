<!--
【文档说明】
承载内容：BSV 层通过统一 DSMP 客户端（`DsmpSoUtil` 类工具）调用 CBOSS（业务运营支撑系统）DSMP 网关的代码模式骨架。
适用范围：apply 编码和 code review 阶段用于新增通过 DSMP 网关调用 CBOSS 的接口方法。
不负责：能开 OPF 路由调用（参见 `能开OPF调用模式（opf-call-pattern）.md`）；DSMP 连接地址/超时（`DsmpSoUtil` 内部处理）；BIPCode/ActiveCode 维护（由 CBOSS 接口文档提供）。
填充指引：模板仅给出代码骨架与通用约定；具体业务对象名、BIPCode/ActiveCode、信道方法、请求 JSON 字段、签名算法等以目标项目的 CBOSS 接口文档为准。
加载建议：涉及 `DsmpSoUtil`、`dealTranc2{信道}`、`HttpClientCbossRsp`、`BIPCode`/`ActiveCode`、CBOSS DSMP 直连调用时加载。
-->
# CBOSS DSMP 直连调用模式（CBOSS DSMP Call Pattern）

> **通用化说明**：CBOSS（业务运营支撑系统）是中国移动集团规范的业务运营支撑平台；DSMP（数据业务管理平台）是其对外接口网关。BSV 层通过 `crm-base/utils-common` 类共享基础组件库中的 `DsmpSoUtil`（CRITICAL 影响级别，修改前必做 impact）调用 DSMP。本骨架展示标准调用模式；具体业务字段、信道选择、BIPCode/ActiveCode、签名算法、JSON 结构以目标项目的"CBOSS 接口文档"为准。

## 何时加载

当前问题涉及以下关键词时加载本文：

- `DsmpSoUtil`、`dealTranc2WLW` / `dealTranc2N2N` / `dealTranc2SOAP` / `dealTranc2CbossNew`、`HttpClientCbossRsp`
- `BIPCode`、`ActiveCode`、`PlatSign`、`PlatCode`
- CBOSS 直连、DSMP 网关调用、满意度调研、服务评价、电商渠道处理
- 在 BSV 层新增通过 DSMP 网关调用 CBOSS 的接口方法

不适用：

- 能开 OPF 路由调用（`IOpfClientPublicSV`）→ 参见 `能开OPF调用模式（opf-call-pattern）.md`
- 补换卡 BSV 落单 → 参见 `补换卡BSV落单模式（sim-card-replace-bsv-pattern）.md`（项目实例）
- 开通系统 `I_OPEN_*` 配置表调用 → 参见开通系统接口相关文档

## 调用链全景

```
调用方（ET/BSV/PSV）
  └── {XXX}SVImpl.{方法名}(map)
        ├── [可选] Step1: CenterFactory 分库路由（仅需 DAO 操作时）
        ├── [可选] Step2: 查询内部业务数据
        ├── 构建请求 JSON（字段须从 CBOSS 接口文档获取）
        ├── DsmpSoUtil.[dealTranc2XXX](jsonStr, BIPCode, ActiveCode)
        │     └── deal2CbossCoreNew(json, bip, act, flag)
        │           └── HttpUtil.doPost([HTTP信道代码], {bipCode, activityCode, busiData})
        └── HttpClientCbossRsp（respCode/respDesc/respData）
```

## 信道选择

| 方法 | 信道 | 典型场景 | 备注 |
|------|------|---------|------|
| `dealTranc2WLW(json, bip, act)` | WLW → CBOSS HTTP | 满意度调研 / 服务评价 / 通用 WLW 接口 | 最常用 |
| `dealTranc2N2N(json, bip, act)` | N2N → CBOSS HTTP | 通用 N2N 接口 | 自动按 BIPCode 路由（如亲情网/区块链信道） |
| `dealTranc2SOAP(json, bip, act)` | SOAP → CBOSS HTTP | SOAP 协议接口 | |
| `dealTranc2CbossNew(json, bip, act)` | CENTER → CBOSS HTTP | 中心直连 | 优先用 New 版，避免使用旧版 `dealTranc2Cboss` |

> 选择方法：查 CBOSS 接口文档确认信道类型 → 对应上表 → 代码骨架中替换 `[dealTranc2XXX]`。

## 职责边界

| 本组件负责 | 本组件不负责 |
|-----------|------------|
| 按接口文档构建请求 JSON（业务节点 + 必要的渠道/签名字段） | 维护 DSMP 连接地址/超时（`DsmpSoUtil` 内部） |
| 按接口文档决定是否需要签名及签名算法 | 修改 `DsmpSoUtil`（CRITICAL 级别，改前做 impact） |
| 选择正确的信道方法（`dealTranc2XXX`） | 维护 BIPCode/ActiveCode（从 CBOSS 接口文档获取） |
| 解析 `HttpClientCbossRsp` 响应 | DSMP 超时/重试逻辑（已封装在 `DsmpSoUtil`） |
| 记录调用耗时日志 | 上游业务流程编排 |

## 通用代码骨架

```java
public class [XXX]SVImpl implements I[XXX]SV {
    private static transient Log log = LogFactory.getLog([XXX]SVImpl.class);

    @Override
    public Map [methodName](Map input) throws Exception {
        long startTime = System.currentTimeMillis();
        log.error("{center}_I[XXX]SV_[methodName]入参:" + input);
        String rspCode = "0000", rspDesc = "";
        Map result = new HashMap();

        try {
            // Step 1: [可选] CenterFactory 分库路由（仅需 DAO 查询时保留，否则删除此步）
            String billId = MapUtils.getString(input, "BILL_ID");
            CenterFactory.setCenterInfoByTypeAndValue(CenterUtil.BILL_ID, billId);

            // Step 2: [可选] 查询内部业务数据

            // Step 3: 构建请求 JSON（字段名和必填项须从 CBOSS 接口文档获取）
            String timestamp = String.valueOf(System.currentTimeMillis());
            // [占位: 若接口需要签名（如某些 BIPCode 族），PlatCode/PlatSign/CbossExtendInfo 按接口文档组装；
            //        PlatKey 禁止硬编码，须从 BS_PARA_DETAIL 配置表或常量类取]
            // [占位: 若接口需要请求 ID 字段，字段名按 CBOSS 接口文档设置]

            JSONObject reqJson = new JSONObject();
            // [占位: 按 CBOSS 接口文档组装字段（渠道字段 LChannelID/ChannelForm/ChannelFeature/CcsBizCode
            //        按渠道类型动态设置，不同接口族字段集差异很大，必须以接口文档为准）]
            // [占位: 按 CBOSS 接口文档组装业务节点 BizInfo / ServiceRequestInfo]

            // Step 4: 调用 CBOSS（信道方法从 CBOSS 接口文档确认，见信道选择表；BIPCode/ActiveCode 从 CBOSS 接口文档取）
            // dealTranc2WLW → WLW 信道；dealTranc2N2N → N2N 信道；dealTranc2SOAP → SOAP 信道；dealTranc2CbossNew → CENTER 信道
            HttpClientCbossRsp dsmpRsp = DsmpSoUtil.[dealTranc2XXX](
                reqJson.toJSONString(), "[BIP_CODE]", "[ACTIVE_CODE]"
            );

            // Step 5: 解析响应（respCode "0000"/"0" 为成功）
            if (dsmpRsp == null) {
                rspCode = "2998"; rspDesc = "DSMP 网关未返回响应";
            } else if (!"0000".equals(dsmpRsp.getRespCode()) && !"0".equals(dsmpRsp.getRespCode())) {
                rspCode = "2998"; rspDesc = "CBOSS侧错误 请联系CBOSS解决:" + dsmpRsp.getRespDesc();
            }
            // else: [占位: 可选解析 dsmpRsp.getRespData()]

        } catch (Exception e) {
            log.error("{center}_I[XXX]SV_[methodName] 异常", e);
            rspCode = "2998"; rspDesc = "调用DSMP接口发生异常";
        }

        result.put("RspCode", rspCode);
        result.put("RspDesc", rspDesc);
        log.error("{center}_I[XXX]SV_[methodName]出参(" + (System.currentTimeMillis()-startTime) + "ms):" + result);
        return result;
    }
}
```

## 占位变量说明

| 占位符 | 含义 | 替换规则 |
|--------|------|---------|
| `[XXX]` | 接口/类业务名 | 按需求中的业务对象命名 |
| `[methodName]` | 方法名 | 与 CSF serviceCode 中的方法名一致 |
| `[dealTranc2XXX]` | `DsmpSoUtil` 信道方法 | 查 CBOSS 接口文档确认信道：WLW → `dealTranc2WLW`；N2N → `dealTranc2N2N`；SOAP → `dealTranc2SOAP`；CENTER → `dealTranc2CbossNew` |
| `[BIP_CODE]` | CBOSS BIPCode | 从 CBOSS 接口文档获取 |
| `[ACTIVE_CODE]` | CBOSS ActiveCode | 从 CBOSS 接口文档获取 |
| `[PLAT_KEY]` | MD5 签名密钥（仅在接口需要签名时适用） | 从 `BS_PARA_DETAIL` 配置表或常量类获取；键值**不得硬编码**；若接口不需要签名则删除骨架中 PlatSign 相关代码 |
| `[RequestID_FIELD]` | 请求 ID 字段名 | 不同 BIPCode 族字段名不同（如满意度调研为 `SurveyReqID`）；其他接口查 CBOSS 接口文档；若不要求则删除 |
| `[业务字段]` | 业务节点中的字段名 | 从 CBOSS 接口文档获取 |
| `{center}` | 调用方中心编码 | 用目标仓库中心编码替换（CSF serviceCode 前缀） |

## 裁剪指南

| 场景 | 裁剪动作 |
|------|---------|
| 不需要内部业务数据 | 删除 Step 1（CenterFactory）和 Step 2（内部查询），二者可独立删除 |
| 接口不需要业务信息节点 | 删除对应业务节点 JSONArray 组装部分 |
| 响应不需要解析 `respData` | 删除 `getRespData()` 调用，只判断 `respCode` |
| 需要渠道校验 | 在 Step 3 前增加渠道类型判断 |
| 新增接口（相同 SVImpl，不同 BIPCode） | 在已有 Impl 新增方法，修改 `bipCode` / `activeCode` / 业务节点结构 |
| 接口不需要请求 ID 字段 | 将 `[RequestID_FIELD]` 替换为 CBOSS 接口文档要求的字段名；若接口不要求请求 ID 则删除该行 |
| 接口要求 `ServiceRequestInfo` 替代 `BizInfo` | 将 `BizInfo` JSONArray 换为 `ServiceRequestInfo` 结构，字段按 CBOSS 接口文档 |

## 编码约定

- 日志统一 `log.error()`，方法入口/出口各记一次，含耗时
- `DsmpSoUtil` 是 CRITICAL 级别共享工具类，禁止直接修改其实现（131+ 上游依赖）
- 请求 JSON 的字段集、签名方式（是否需要 `PlatCode`/`PlatSign`）由 CBOSS 接口文档决定，**不能照搬示例字段**
- 渠道字段（`LChannelID`/`ChannelForm`/`ChannelFeature`/`CcsBizCode`）若接口需要，须按渠道类型动态赋值，不是固定常量
- DSMP 超时由 `DsmpSoUtil` 内部处理，返回 `DSMP_BUSI_RESULT_SYS_ERROR` 时需识别
- 调用 `CenterFactory.setCenterInfoByTypeAndValue` 后才可进行分库 DAO 操作
- 多个日期格式化（如 `SimpleDateFormat`）注意线程安全（建议每次 `new` 或使用 `DateTimeFormatter`）

## 编码前确认

- [ ] BIPCode/ActiveCode 已从 CBOSS 接口文档确认
- [ ] CBOSS 信道类型已确认（WLW/N2N/SOAP/CENTER），`[dealTranc2XXX]` 已替换为对应方法
- [ ] 请求 JSON 结构（节点名和字段）已从接口文档确认
- [ ] 若接口需要签名，签名算法和密钥来源已从接口文档确认，禁止硬编码
- [ ] 若接口需要请求 ID 字段，字段名已按接口文档确认；若不需要则从骨架中删除

## 检查点

- [ ] `DsmpSoUtil.[dealTranc2XXX](jsonStr, bipCode, activeCode)` 信道方法已按接口文档选择，三参数均正确
- [ ] `HttpClientCbossRsp` 不为 null 才取 `getRespCode()`
- [ ] DSMP 超时返回码已处理（如 `DSMP_BUSI_RESULT_SYS_ERROR`）
- [ ] 若接口需要签名，签名拼接顺序正确，密钥从配置取
- [ ] 若接口需要请求 ID 字段，字段名已按接口文档替换（或已确认并删除）
- [ ] 方法入参/出参/耗时均有日志
- [ ] `CenterFactory` 调用（若存在）在任何 DAO 操作之前

## 反模式

- **直接修改 `DsmpSoUtil` 实现**：CRITICAL 级别，100+ 上游依赖，改动前必须做 impact analysis
- **MD5 签名字段拼接顺序错误**：拼接顺序由 CBOSS 接口文档规定，不得自行调整；密钥从配置取，禁止硬编码
- **照搬某一 BIPCode 族字段到其他接口**：不同 BIPCode 族的 JSON 字段集差异极大，必须从 CBOSS 接口文档获取实际字段名和必填项
- **不判断 `HttpClientCbossRsp` 是否 null**：DSMP 超时或异常时可能返回 null
- **不记录调用耗时**：CBOSS 接口耗时是关键排查指标，必须在日志中输出
- **在循环中反复 `new SimpleDateFormat`**：`SimpleDateFormat` 非线程安全，高并发场景建议使用 `ThreadLocal` 或 `DateTimeFormatter`

## 关联文档

- `接口设计规范 §2.1 CSV/SV 对外方法签名约定`
- `接口设计规范 §八 CSF 服务编码（serviceCode）规范与验证`
- `能开OPF调用模式（opf-call-pattern）.md`（另一种外部系统调用方式）
- 设计手册 `CBOSS DSMP接口调用（cboss-dsmp-integration）.md`（项目实例补充）