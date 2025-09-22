from pathlib import Path

from dreamcanvas.security.secret_store import (
    InvalidPassphraseError,
    decrypt_payload,
    encrypt_payload,
    read_secret_file,
    save_encrypted_file,
)


def test_encrypt_and_decrypt_roundtrip(tmp_path: Path) -> None:
    payload = {"session": "abc", "api_key": "xyz"}
    result = encrypt_payload(payload, "pass123")
    enc_path = tmp_path / "secrets.enc"
    save_encrypted_file(enc_path, result)
    restored = read_secret_file(enc_path, "pass123")
    assert restored == payload


def test_invalid_passphrase_raises(tmp_path: Path) -> None:
    payload = {"session": "abc"}
    enc_path = tmp_path / "secrets.enc"
    save_encrypted_file(enc_path, encrypt_payload(payload, "correct"))
    try:
        read_secret_file(enc_path, "wrong")
    except InvalidPassphraseError:
        pass
    else:
        raise AssertionError("Should raise InvalidPassphraseError")
