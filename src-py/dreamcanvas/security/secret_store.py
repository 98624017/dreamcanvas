"""对项目敏感凭据进行加密存储与解密读取的工具。"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from hashlib import pbkdf2_hmac
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

__all__ = [
    "SecretStoreError",
    "InvalidPassphraseError",
    "EncryptionResult",
    "encrypt_payload",
    "decrypt_payload",
    "load_encrypted_file",
    "save_encrypted_file",
    "read_secret_file",
]

KDF_ALGORITHM = "pbkdf2-hmac-sha256"
KDF_ITERATIONS = 240_000
SALT_BYTES = 16
FILE_VERSION = 1


class SecretStoreError(RuntimeError):
    """密钥文件处理过程中出现的通用异常。"""


class InvalidPassphraseError(SecretStoreError):
    """当解密密码错误或密文被破坏时抛出。"""

@dataclass(slots=True)
class EncryptionResult:
    """封装加密后的密文与元数据。"""

    version: int
    algorithm: str
    iterations: int
    salt: str
    ciphertext: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "kdf": {
                "algorithm": self.algorithm,
                "iterations": self.iterations,
                "salt": self.salt,
            },
            "ciphertext": self.ciphertext,
        }


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    key = pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, KDF_ITERATIONS, dklen=32)
    return base64.urlsafe_b64encode(key)


def encrypt_payload(payload: Dict[str, Any], passphrase: str) -> EncryptionResult:
    """使用用户口令对 JSON 结构进行加密。"""

    salt = os.urandom(SALT_BYTES)
    key = _derive_key(passphrase, salt)
    fernet = Fernet(key)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    token = fernet.encrypt(plaintext)
    return EncryptionResult(
        version=FILE_VERSION,
        algorithm=KDF_ALGORITHM,
        iterations=KDF_ITERATIONS,
        salt=base64.b64encode(salt).decode("ascii"),
        ciphertext=base64.b64encode(token).decode("ascii"),
    )


def decrypt_payload(data: Dict[str, Any], passphrase: str) -> Dict[str, Any]:
    """使用密钥解密密文并返回 JSON 对象。"""

    try:
        metadata = data["kdf"]
        if data.get("version") != FILE_VERSION:
            raise SecretStoreError("密钥文件版本不受支持")
        if metadata.get("algorithm") != KDF_ALGORITHM:
            raise SecretStoreError("未知的密钥派生算法")
        iterations = int(metadata.get("iterations", KDF_ITERATIONS))
        salt = base64.b64decode(metadata["salt"])
        ciphertext = base64.b64decode(data["ciphertext"])
    except (KeyError, ValueError, TypeError) as exc:
        raise SecretStoreError("密钥文件格式不正确") from exc

    key = base64.urlsafe_b64encode(
        pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, iterations, dklen=32)
    )
    fernet = Fernet(key)
    try:
        plaintext = fernet.decrypt(ciphertext)
    except InvalidToken as exc:
        raise InvalidPassphraseError("解密失败，请检查口令是否正确") from exc
    return json.loads(plaintext.decode("utf-8"))


def load_encrypted_file(path: Path) -> Dict[str, Any]:
    """读取磁盘上的密钥文件。"""

    if not path.exists():
        raise SecretStoreError(f"未找到密钥文件：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SecretStoreError("密钥文件不是合法的 JSON") from exc


def save_encrypted_file(path: Path, result: EncryptionResult) -> None:
    """将加密结果写入磁盘。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def read_secret_file(path: Path, passphrase: str) -> Dict[str, Any]:
    """组合读取与解密操作。"""

    data = load_encrypted_file(path)
    return decrypt_payload(data, passphrase)
