"""DreamCanvas 命令行工具入口。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any, Callable, Dict

from ..security.secret_store import (
    InvalidPassphraseError,
    SecretStoreError,
    decrypt_payload,
    encrypt_payload,
    load_encrypted_file,
    save_encrypted_file,
)

DEFAULT_SECRET_PATH = Path("config/secrets.enc")


@dataclass(slots=True)
class CommandContext:
    passphrase_loader: Callable[[bool], str]


def _load_passphrase(provided: str | None, confirm: bool, ctx: CommandContext) -> str:
    if provided:
        return provided
    first = ctx.passphrase_loader(True)
    if confirm:
        second = ctx.passphrase_loader(False)
        if first != second:
            raise SecretStoreError("两次输入的口令不一致")
    return first


def _prompt_passphrase(is_primary: bool) -> str:
    prompt = "请输入凭据主口令: " if is_primary else "请再次输入以确认: "
    value = getpass(prompt)
    if not value:
        raise SecretStoreError("口令不能为空")
    return value


def _load_plaintext(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SecretStoreError(f"未找到待加密文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SecretStoreError("待加密文件不是合法 JSON") from exc


def _write_plaintext(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _cmd_secrets_encrypt(args: argparse.Namespace, ctx: CommandContext) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output or DEFAULT_SECRET_PATH)
    payload = _load_plaintext(input_path)
    passphrase = _load_passphrase(args.passphrase, not args.no_confirm, ctx)
    result = encrypt_payload(payload, passphrase)
    save_encrypted_file(output_path, result)
    print(f"已生成加密文件: {output_path}")
    return 0


def _cmd_secrets_decrypt(args: argparse.Namespace, ctx: CommandContext) -> int:
    input_path = Path(args.input or DEFAULT_SECRET_PATH)
    output_path = Path(args.output) if args.output else None
    passphrase = _load_passphrase(args.passphrase, False, ctx)
    encrypted = load_encrypted_file(input_path)
    plaintext = decrypt_payload(encrypted, passphrase)
    if output_path:
        _write_plaintext(output_path, plaintext)
        print(f"已写入解密结果: {output_path}")
    else:
        json.dump(plaintext, sys.stdout, ensure_ascii=False, indent=2)
        print()  # 末尾换行
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dc-cli", description="DreamCanvas 命令行工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    secrets_parser = subparsers.add_parser("secrets", help="管理加密凭据")
    secrets_sub = secrets_parser.add_subparsers(dest="action", required=True)

    encrypt_parser = secrets_sub.add_parser("encrypt", help="根据 JSON 输入生成密文文件")
    encrypt_parser.add_argument("--input", required=True, help="待加密的 JSON 文件路径")
    encrypt_parser.add_argument("--output", help="输出密文路径，默认 config/secrets.enc")
    encrypt_parser.add_argument("--passphrase", help="直接提供主口令（不建议在命令行历史中保留）")
    encrypt_parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="跳过口令二次确认（仅在非交互环境使用）",
    )
    encrypt_parser.set_defaults(func=_cmd_secrets_encrypt)

    decrypt_parser = secrets_sub.add_parser("decrypt", help="解密并输出 JSON")
    decrypt_parser.add_argument("--input", help="待解密文件路径，默认 config/secrets.enc")
    decrypt_parser.add_argument("--output", help="将解密结果写入文件，缺省时输出到 stdout")
    decrypt_parser.add_argument("--passphrase", help="主口令，可通过环境变量或交互输入")
    decrypt_parser.set_defaults(func=_cmd_secrets_decrypt)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = CommandContext(passphrase_loader=_prompt_passphrase)
    try:
        return args.func(args, ctx)
    except (SecretStoreError, InvalidPassphraseError) as exc:
        parser.exit(status=1, message=f"错误：{exc}\n")
    except KeyboardInterrupt:
        parser.exit(status=130, message="操作被中断\n")


if __name__ == "__main__":
    sys.exit(main())
