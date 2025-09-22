from pathlib import Path

import json

from dreamcanvas.cli import main


def test_cli_encrypt_decrypt(tmp_path: Path) -> None:
    plaintext = {"session": "foo", "api_key": "bar"}
    plain_path = tmp_path / "secrets.json"
    plain_path.write_text(json.dumps(plaintext), encoding="utf-8")

    enc_path = tmp_path / "secrets.enc"

    exit_code = main(
        [
            "secrets",
            "encrypt",
            "--input",
            str(plain_path),
            "--output",
            str(enc_path),
            "--passphrase",
            "123456",
            "--no-confirm",
        ]
    )
    assert exit_code == 0
    assert enc_path.exists()

    output_path = tmp_path / "output.json"
    exit_code = main(
        [
            "secrets",
            "decrypt",
            "--input",
            str(enc_path),
            "--output",
            str(output_path),
            "--passphrase",
            "123456",
        ]
    )
    assert exit_code == 0
    restored = json.loads(output_path.read_text(encoding="utf-8"))
    assert restored == plaintext
