<!--
【文档说明】
承载内容：编码规范目录入口，说明通用编码约定、AppFrame2/CSF 规范、BO/Engine/服务注册资料和按需加载顺序。
适用范围：后端设计、任务拆分、编码和 review 阶段用于校准技术栈约定。
填充指引：由通用框架知识、目标项目代码扫描、配置扫描和人工审查更新；新增规范要注明适用技术栈和目标项目确认点。
加载建议：命中编码规范、AppFrame2、BO/Engine/DAO、服务注册或数据源配置时先加载 README。
-->
# 编码规范与约定（Coding Conventions）目录

> 目录说明：本目录存放跨工程通用编码规范，以及按目标技术栈（如 AppFrame2/CSF）沉淀的可选实现结构。目录内既包含通用约定，也包含需按目标仓库确认包路径、版本和配置的编码模板。
>
> 覆盖通用命名、分层边界、数据访问层编码模式、BO 配置、服务注册和 Engine 代码模板等；具体类名、包路径和配置值必须以目标项目证据为准。

---

## 文件清单与加载策略

| 文件 | 内容详述 | 推荐加载时机 |
|------|---------|-------------|
| [概览与通用规范（summary）.md](概览与通用规范（summary）.md) | §一~八 通用编码约定：**优先级**（文档冲突时判断顺序）、**命名**（类名/方法名/变量名/包名规则）、**分层边界**（业务服务层 / 页面服务层各层职责与编码禁止项、Java 版本约束）、**AppFrame2 使用速查**（获取SV/DAO/DB路由/查询写入的正确做法和禁止项）、**对象/集合/Map**（静态方法/覆写/@Override/字符串比较/遍历/判空）、**异常处理**（各层异常捕获与转换规则）、**日志**（日志对象/异常堆栈/敏感信息脱敏）、**注释**（Javadoc/修改说明/TODO）。Agent 生成代码时的基础校验清单。 | 任何涉及后端代码编写的任务（**始终加载**） |
| [AppFrame2数据层（appframe2-data-layer）.md](AppFrame2数据层（appframe2-data-layer）.md) | §十一 AppFrame2 数据驱动层编码规范：**四层架构概览**（SV→DAO→BO→IValues）、**目录结构与包名**（按典型 AppFrame2 BSV 模块抽象，交叉引用 BSV 编码指南）、**类命名约定**（Bean/Engine/DAO/SV/IValue 命名格式与示例）、**数据类型映射**（速查 + 交叉引用 BO配置文件规范完整映射）、**Bean 类**（继承关系/构造函数/字段常量/5 个标准方法模板，仅标准模式，POJO 见 BO配置文件规范）、**Engine 类**（速查 + 交叉引用 Engine层代码模板完整方法目录）、**BO 配置文件 .bo**（交叉引用 BO配置文件规范）、**IValues 接口**（字段常量 + getter/setter 签名模式）、**DAO 层**（接口方法风格含 Bean/Criteria 入参、BeanBridgeHelper 桥接保存、CenterFactory DAO 层设置）、**Service 层**（ServiceFactory 获取 DAO/禁止 new/禁止字段持有/禁止 import impl）、**代码生成检查清单**（11 项逐条检查）。**编写 DAO/Bean/SV 代码时的核心参考。** | 编写 DAO/Bean/SV 代码时 |
| [BO配置文件规范（bo-config-spec）.md](BO配置文件规范（bo-config-spec）.md) | `.bo` XML 配置文件的**结构规范**（基于 AppFrame2 通用模式沉淀）：BO 模式（标准 DataContainer / POJO / 纯元数据 / 查询条件 QBO）对比、标准 Bean 占位示例、元素/属性定义、Oracle + PostgreSQL 数据类型映射、主键声明规则、datasource 三层解析优先级、datasource 样例、XML 占位示例和生成检查清单。⚠️ 标准模式 `.bo` 文件名不得以 `Bean` 结尾；POJO 模式允许。新建 BO 实体时必读，实际 datasource 必须以目标项目配置为准。 | 新建 BO 实体时 |
| [服务注册配置（service-registration）.md](服务注册配置（service-registration）.md) | BSV 层**服务注册配置**指南：SV/DAO 自动发现、显式 XML 注册、defaults.xml（中心路由、事务映射、数据源映射、读写分离、连接池）、DAO 包路径与数据源约定、BO 实体配置（交叉引用 BO 规范）、CenterFactory 路由模式、新增服务检查清单。**新增 SV/DAO/BO 服务时必读。** | 新增 SV/DAO 服务时 |
| [Engine层代码模板（engine-code-template）.md](Engine层代码模板（engine-code-template）.md) | Engine 层 SQL 拼装的**完整代码范式**：标准方法目录（getBeans/getBean/save/saveBatch/getNewId/getSysDate 等全部方法签名）、DAO→Engine 调用的 4 种查询模式（StringBuilder 条件查询、分页查询、计数查询、Criteria 查询 + 常用方法速查表）、保存操作 4 种模式（单条含两种 ID 生成方式、批量循环赋ID、BeanBridgeHelper 桥接保存、查询后更新）、自定义 SQL 查询（多表关联/子查询/聚合）、DAO→Engine 职责分工与获取其他服务方式、完整 DAO 实现类模板、10 条编码风格要点。**编写 DAO/Engine 代码时必读，也是 Engine 方法目录的唯一权威参考。** | 编写 DAO/Engine 代码时 |

## 延迟加载建议

- 若只是修改已有代码逻辑（不新增类/接口）→ 仅加载 `概览与通用规范` 即可
- `AppFrame2数据层` 可延迟到实际编写 DAO/Bean 代码时
- `BO配置文件规范` 仅在需要新建 .bo 文件时加载
- `服务注册配置` 仅在新增 SV/DAO 接口时加载
- `Engine层代码模板` 可与 `AppFrame2数据层` 配合加载，编写 DAO 时提供更丰富的代码范式

## 卸载建议

- 编码完成进入 verify 阶段后，`AppFrame2数据层` 和 `Engine层代码模板` 可卸载
- verify 完成后可全部卸载
- 若持续进行多个 tasks/apply 迭代，建议保留 `概览与通用规范`
