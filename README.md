# AIGC 检测润色工作台

论文/文档的 AI 痕迹自检与润色工具：本地规则 + GLM 双引擎检测行文特征，支持术语锁定的语义保持改写，纯单页前端由后端直接托管。

## 目录结构

```
├── backend/                  # FastAPI 后端
│   ├── app/                  # 全部 Python 模块（见下表）
│   ├── models/               # 本地分类器权重（xiaoyu-v3.3，git 忽略，不提交）
│   ├── .env                  # 本机密钥（git 忽略）
│   ├── providers.json        # LLM 供应商配置（key 在此）
│   ├── requirements.txt      # 主依赖（FastAPI/uvicorn/python-docx/pypdf…）
│   ├── requirements-detector.txt  # 分类器额外依赖（transformers/torch 等）
│   └── tmp-server.log/err    # 手动启动时的重定向日志（git 忽略，运行时生成）
├── frontend/
│   ├── index.html            # 唯一前端文件（样式+逻辑+页面全内嵌）
│   └── avatar.jpg            # 左上角品牌头像
├── .gitignore
└── README.md
```

## 启动

```powershell
cd backend
D:\python\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 局域网共享时把 --host 改为 0.0.0.0（需防火墙放行 8000）
```

浏览器打开 `http://127.0.0.1:8000`（前端由后端 `/` 与 `/static` 直接托管，无需单独起前端服务）。

## 后端模块（backend/app/）

| 文件 | 职责 | 关键符号 |
| --- | --- | --- |
| `main.py` | FastAPI 入口：全部 HTTP 端点 + 前端静态托管 | `/api/health` `/api/providers` `/api/detect` `/api/rewrite` `/api/rewrite-segment` `/api/extract` |
| `config.py` | 读取 `.env` 与 `providers.json`，构建 `settings` | `Settings` `ProviderConfig` |
| `schemas.py` | 全部 Pydantic 请求/响应模型（API 契约） | `DetectRequest/Response` `RewriteRequest/Response` 等 |
| `detector.py` | 本地规则评分引擎：句长分布/词汇重复/套话密度/句式模板四信号加权；逐句风险定位 | `analyze_text` `score_text` `_signals`(170) `_sentence_risk`(270) |
| `segmenter.py` | 标题识别与空行分段 | `split_paragraphs` `is_title` |
| `locking.py` | 术语锁定：提取不可改写片段（数字/引用/术语），改写后校验 | `extract_locked_spans` `verify_locked_spans` |
| `provider.py` | LLM HTTP 客户端（httpx），供应商就绪检测 | `LLMProvider` `LLMError` |
| `local_rewriter.py` | 离线规则改写：双语模板替换、句式重排、锁定片段掩码保护 | `local_rewrite`(267) |
| `rewriter.py` | 改写编排：选引擎→分段→逐段改写→锁定校验→重新计分 | `rewrite_text` `rewrite_paragraph` `proxy_detect` |
| `ai_judge.py` | GLM 模型评估：逐段四维度（套话/机械度/信息密度/风格缺失）打分与证据 | `analyze_with_model` |
| `model_detector.py` | 本地开源分类器（xiaoyu-v3.3）：懒加载+预热+失败降级，分段推理聚合段落疑似度 | `warmup`；环境变量见文件头(1-17) |
| `__init__.py` | 空（包标记） | — |

**依赖分层**（谁 import 谁）：

```
main ──> rewriter / ai_judge / model_detector / detector / provider / schemas / config
rewriter ──> local_rewriter / locking / segmenter / detector / provider / config / schemas
ai_judge ──> detector / provider / segmenter / config
model_detector ──> segmenter          provider ──> config
detector / segmenter / locking / schemas / config  ← 基础层，仅标准库，无内部依赖
```

## API 一览

| 端点 | 方法 | 用途 |
| --- | --- | --- |
| `/api/health` | GET | 服务状态、供应商就绪、分类器加载情况 |
| `/api/providers` | GET | 可用模型供应商列表（前端引擎下拉用） |
| `/api/detect` | POST | 自检报告：特征指数、四维分解、逐句风险、命中证据 |
| `/api/rewrite` | POST | 全文润色：选引擎/强度/风格/术语锁定/精准模式，返回改写前后对照 |
| `/api/rewrite-segment` | POST | 单段"换一种写法"（variant 控制变体） |
| `/api/extract` | POST | 上传文档解析：.txt/.md 直读，.docx 用 python-docx，.pdf 用 pypdf |
| `/` `/static/*` | GET | 前端页面与静态资源托管 |

## 双引擎说明

- **检测**：`detector.py` 本地规则（毫秒级、可复现）与 `model_detector.py` 本地分类器（疑似度读数）并行；`ai_judge.py` 走 GLM（慢、消耗额度）。
- **改写**：`engine=local` 走 `local_rewriter.py` 离线规则；`engine=llm` 走 `provider.py` 调 GLM；`auto` 优先模型、未配置回落本地。
- 两者都受 `locking.py` 保护：数字、年份、百分比、引用标记、术语表条目逐字保留。

## 开发注意

- `models/`、`.env`、`tmp-server.*` 已被 `.gitignore` 忽略，永远不会提交。
- 改动 `detector.py` 的评分公式后必须重启后端才生效（uvicorn 无 --reload）。
- 供应商 key 在 `backend/providers.json`，局域网开放时所有使用者共享该 key 的额度，且服务无鉴权。
- 前端是单 HTML 文件，改动后强刷浏览器即可（Ctrl+Shift+R），无需重启后端。
