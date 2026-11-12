"""应用配置：支持按语言路由的多供应商配置。

providers.json 中每条配置可用 language 标记 zh / en / any；
改写时按段落语言选择对应供应商，未命中的语言回退 any，再回退本地引擎。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_language(value: str) -> str:
    lang = (value or "any").strip().lower()
    return lang if lang in ("zh", "en") else "any"


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.8
    timeout: float = 60.0
    language: str = "any"

    def is_ready(self) -> bool:
        if not (self.base_url and self.model):
            return False
        # 本地端点（Ollama 等）通常不需要 API Key
        if self.api_key:
            return True
        return "127.0.0.1" in self.base_url or "localhost" in self.base_url

    def serves(self, language: str) -> bool:
        return self.language == "any" or self.language == language


@dataclass
class Settings:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    default_provider: str = ""
    # 改写后语义保持的相似度阈值占位（后续可接入真实语义相似度计算）
    rewrite_timeout: float = 60.0
    max_retry: int = 2

    def get_provider(self, name: str | None = None) -> ProviderConfig | None:
        key = name or self.default_provider
        if key and key in self.providers:
            return self.providers[key]
        return None

    def get_provider_for_language(self, language: str) -> ProviderConfig | None:
        """按语言选供应商：显式默认项 → 同语言专用项 → any 通用项。"""
        lang = _normalize_language(language)
        default = self.providers.get(self.default_provider) if self.default_provider else None
        if default and default.is_ready() and default.serves(lang):
            return default
        for cfg in self.providers.values():
            if cfg.is_ready() and cfg.language == lang:
                return cfg
        for cfg in self.providers.values():
            if cfg.is_ready() and cfg.language == "any":
                return cfg
        return None

    def routing(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for lang in ("zh", "en"):
            cfg = self.get_provider_for_language(lang)
            result[lang] = cfg.name if cfg else ""
        return result


def _load_providers_file(path: Path) -> dict[str, ProviderConfig]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    result: dict[str, ProviderConfig] = {}
    for item in raw.get("providers", []):
        name = item.get("name")
        if not name:
            continue
        result[name] = ProviderConfig(
            name=name,
            base_url=item.get("base_url", ""),
            api_key=item.get("api_key", ""),
            model=item.get("model", ""),
            temperature=float(item.get("temperature", 0.8)),
            timeout=float(item.get("timeout", 60.0)),
            language=_normalize_language(item.get("language", "any")),
        )
    return result


def load_settings() -> Settings:
    providers = _load_providers_file(BASE_DIR / "providers.json")

    # 环境变量提供的默认供应商（优先级低于 providers.json 中的同名项）
    env_base = os.getenv("LLM_BASE_URL", "")
    env_key = os.getenv("LLM_API_KEY", "")
    env_model = os.getenv("LLM_MODEL", "")
    env_name = os.getenv("LLM_PROVIDER_NAME", "default")
    if env_base and env_model and env_name not in providers:
        providers[env_name] = ProviderConfig(
            name=env_name,
            base_url=env_base,
            api_key=env_key,
            model=env_model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.8")),
            language=_normalize_language(os.getenv("LLM_LANGUAGE", "any")),
        )

    default = os.getenv("LLM_DEFAULT_PROVIDER", "")
    if not default:
        default = next((n for n, p in providers.items() if p.is_ready()), "")

    return Settings(providers=providers, default_provider=default)


settings = load_settings()
