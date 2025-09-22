"""集中管理加密凭据的读取与缓存。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from ..security.secret_store import InvalidPassphraseError, SecretStoreError, read_secret_file

DEFAULT_SECRET_PATH = Path("config/secrets.enc")


class SecretManager:
    """提供凭据读取、缓存与口令解析的统一接口。"""

    def __init__(self, *, path: Path | None = None, cache_enabled: bool = True) -> None:
        self._path = path or DEFAULT_SECRET_PATH
        self._cache_enabled = cache_enabled
        self._cache: Dict[str, Any] | None = None

    @classmethod
    def from_settings(
        cls,
        *,
        path: Path,
        passphrase: str | None,
        cache_enabled: bool = True,
    ) -> "SecretManager":
        manager = cls(path=path, cache_enabled=cache_enabled)
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
        if not secret_key:
            raise SecretStoreError("未提供凭据主口令，可设置环境变量 DC_SECRETS_PASSPHRASE")

        payload = read_secret_file(self._path, secret_key)
        if self._cache_enabled:
            self._cache = payload
        return payload

    def clear(self) -> None:
        self._cache = None


__all__ = ["SecretManager", "DEFAULT_SECRET_PATH", "InvalidPassphraseError", "SecretStoreError"]
