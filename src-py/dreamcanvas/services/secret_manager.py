"""集中管理加密凭据的读取与缓存。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from ..security.secret_store import InvalidPassphraseError, SecretStoreError, read_secret_file

DEFAULT_SECRET_PATH = Path("config/secrets.enc")
DEFAULT_PLAINTEXT_PATH = Path("config/secrets.local.json")

logger = logging.getLogger(__name__)


class SecretManager:
    """提供凭据读取、缓存与口令解析的统一接口。"""

    def __init__(
        self,
        *,
        path: Path | None = None,
        plaintext_path: Path | None = None,
        cache_enabled: bool = True,
    ) -> None:
        self._path = path or DEFAULT_SECRET_PATH
        self._plaintext_path = plaintext_path or DEFAULT_PLAINTEXT_PATH
        self._cache_enabled = cache_enabled
        self._cache: Dict[str, Any] | None = None

    @classmethod
    def from_settings(
        cls,
        *,
        path: Path,
        passphrase: str | None,
        plaintext_path: Path | None = None,
        cache_enabled: bool = True,
    ) -> "SecretManager":
        manager = cls(
            path=path,
            plaintext_path=plaintext_path,
            cache_enabled=cache_enabled,
        )
        if passphrase:
            # 预加载缓存，确保口令可用；失败时立即抛错方便定位。
            manager.load(passphrase=passphrase, refresh=True)
        return manager

    @property
    def path(self) -> Path:
        return self._path

    def load(self, passphrase: str | None = None, *, refresh: bool = False) -> Dict[str, Any]:
        if self._cache_enabled and self._cache is not None and not refresh:
            return self._cache

        secret_key = passphrase or os.getenv("DC_SECRETS_PASSPHRASE")
        payload: Dict[str, Any] | None = None

        if secret_key:
            try:
                payload = read_secret_file(self._path, secret_key)
            except InvalidPassphraseError:
                raise
            except SecretStoreError as exc:
                logger.warning(
                    "读取加密凭据失败，将尝试使用明文副本 %s：%s",
                    self._plaintext_path,
                    exc,
                )
        else:
            logger.warning(
                "未提供 DC_SECRETS_PASSPHRASE，尝试使用未加密凭据文件：%s",
                self._plaintext_path,
            )

        if payload is None:
            payload = self._load_plaintext()

        if self._cache_enabled:
            self._cache = payload
        return payload

    def _load_plaintext(self) -> Dict[str, Any]:
        path = self._plaintext_path
        if not path.exists():
            raise SecretStoreError(
                "未找到可用的凭据文件，请确认已生成 config/secrets.enc 或在 config/secrets.local.json 中填写明文配置",
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SecretStoreError("未加密的凭据文件不是合法的 JSON") from exc

        logger.warning(
            "正在使用未加密的本地凭据文件 %s，建议尽快执行 dc-cli secrets encrypt 以提升安全性",
            path,
        )
        return data

    def clear(self) -> None:
        self._cache = None


__all__ = [
    "SecretManager",
    "DEFAULT_SECRET_PATH",
    "DEFAULT_PLAINTEXT_PATH",
    "InvalidPassphraseError",
    "SecretStoreError",
]
