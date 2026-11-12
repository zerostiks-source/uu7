<!--
【文档说明】
承载内容：前端通信协议规范，承载 H5/PC 到页面网关/BFF 的请求协议、Header、安全、响应和 mock 约定。
适用范围：前端编码、接口联调、BFF 契约设计和验收阶段使用。
填充指引：由前端请求封装、网关配置、接口文档、抓包和 context-update 补充；环境地址、密钥和租户身份不得写入通用上下文。
加载建议：命中前端调用、网关协议、Header、加解密、响应处理或 mock 映射时加载。
-->
# 前端通信协议规范（Frontend Gateway Protocol）

> 本文描述前端到页面网关/BFF 的通用协议结构。具体域名、路径、Header、加密算法、appCode、pageCode 和 serviceCode 必须从目标项目代码或网关配置确认。

---

## 一、HTTP 请求规范

| 项 | 填充要求 |
|---|---|
| 请求方法 | 记录目标项目实际使用的 GET/POST 或封装方法 |
| 请求路径 | 使用占位路径，不写入真实环境地址 |
| Content-Type | 以项目请求封装和网关要求为准 |
| 请求体 | 说明是明文 JSON、加密串、表单还是项目自定义结构 |
| 超时/重试 | 记录前端封装默认值和业务是否允许重试 |

### 1.1 请求目标占位

```http
POST {gateway_path}
```

`{gateway_path}` 由网关配置或前端请求封装确认，禁止在通用上下文中写入真实域名、IP、端口和环境标识。

### 1.2 请求体结构

```json
{
  "serviceCode": "{service_code}",
  "params": {
    "{field_name}": "{field_value}"
  }
}
```

如果项目使用加密报文，应在初始化后补充：加密范围、算法、编码格式、密钥来源、失败处理和调试开关。

---

## 二、请求头字段规范

| 请求头 | 必填 | 说明 | 来源 |
|---|---|---|---|
| `{route_header}` | 待确认 | 接口路由或 serviceCode | 网关配置/请求封装 |
| `{app_header}` | 待确认 | 前端应用标识 | 项目配置 |
| `{version_header}` | 待确认 | 接口版本 | 接口文档/代码 |
| `{trace_header}` | 建议 | 链路追踪 | 前端公共封装 |
| `{auth_header}` | 按需 | Token、会话或签名 | 登录态/安全模块 |

### Header 填充注意

- Header 名称和值必须来自目标项目证据。
- 真实 token、密钥、cookie、租户标识和生产环境值不得进入 context。
- 链路追踪字段应说明格式和生成位置，便于排障。

---

## 三、安全与加解密规范

| 维度 | 填充要求 |
|---|---|
| 加密范围 | body、指定字段、Header 或无加密 |
| 算法 | AES/RSA/SM 系列或项目自定义，必须来自代码证据 |
| 密钥来源 | 前端配置、运行时下发、会话协商或安全模块 |
| 编码格式 | Base64、Hex、URL encode 等 |
| 异常处理 | 加密失败、解密失败、签名失败和过期处理 |

### 加密流程占位

```text
业务参数 -> 序列化 -> 加密/签名 -> 网关请求 -> BFF 解密/验签 -> 入参对象
```

不要在上下文中写入真实密钥、盐值、私钥、公钥或可复用的生产报文。

---

## 四、页面服务接收端契约

| 环节 | 说明 |
|---|---|
| 网关解析 | 将前端请求映射到 BFF/PSV serviceCode 或方法 |
| 参数转换 | 把 JSON/报文转换为 Input DTO/VO |
| 会话注入 | 注入操作员、组织、渠道、区域、租户等上下文 |
| 响应包装 | 将业务结果包装为前端统一响应 |
| 异常转换 | 将业务异常、系统异常、鉴权异常转换为前端口径 |

### 入参契约模板

| 字段 | 类型 | 必填 | 来源 | 说明 |
|---|---|---|---|---|
| `{field_name}` | `{type}` | 是/否 | 页面/会话/配置 | 待确认 |

### 响应契约模板

| 字段 | 类型 | 说明 |
|---|---|---|
| `{code_field}` | String/Number | 成功或失败编码 |
| `{message_field}` | String | 错误提示或成功信息 |
| `{data_field}` | Object/Array | 业务数据 |

---

## 五、前端调用示例

### H5 / Vue 类封装

```javascript
api.post('{service_code}', {
  businessKey: '{business_key}'
}).then((res) => {
  if (res.{code_field} === '{success_code}') {
    // handle success
  }
});
```

### PC / jQuery 类封装

```javascript
$.ajax({
  url: '{service_code}',
  type: 'POST',
  dataType: 'json',
  data: { businessKey: '{business_key}' },
  success: function(res) {
    // handle response
  }
});
```

示例只保留调用形态，真实字段名、成功码和封装方法由目标前端项目确认。

---

## 六、H5 与 PC 差异对照

| 维度 | H5 前端 | PC 前端 | 填充来源 |
|---|---|---|---|
| 请求封装 | 待确认 | 待确认 | 前端源码 |
| 路由/页面编码 | 待确认 | 待确认 | 路由配置 |
| 登录态 | 待确认 | 待确认 | 登录模块 |
| mock 机制 | 待确认 | 待确认 | mock 目录/代理配置 |
| 错误提示 | 待确认 | 待确认 | UI 组件/公共拦截器 |

---

## 七、请求报文占位示例

```http
POST {gateway_path} HTTP/1.1
Content-Type: {content_type}
{route_header}: {service_code}
{app_header}: {frontend_app_code}
{trace_header}: {trace_id}

{request_body_or_ciphertext}
```

明文业务参数示例：

```json
{
  "businessKey": "{business_key}",
  "regionCode": "{region_code}"
}
```

响应示例：

```json
{
  "{code_field}": "{success_code}",
  "{message_field}": "",
  "{data_field}": {}
}
```

---

## 八、关键约束与注意事项

| 约束 | 说明 |
|---|---|
| 不写真实环境值 | 域名、IP、端口、token、密钥、cookie 必须占位 |
| 不写真实个人信息 | 示例号码、姓名、证件号、地址必须脱敏或占位 |
| 契约可追溯 | 字段、Header、成功码、错误码必须能追溯到代码或文档 |
| 前后端同步 | 新增/修改接口需同步前端调用、BFF 契约、mock 和测试 |
| 异常一致 | 网络失败、业务失败、登录失效、权限不足要有统一处理 |
