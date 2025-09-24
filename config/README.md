# DreamCanvas 配置说明

- `default.env`：公共配置模板，CI 与本地默认加载。
- `secrets.enc`：通过 `dc-cli secrets encrypt` 生成的密文，存放 sessionid 等敏感信息。
- `secrets.template.json`：示例明文，可在本地填写后配合 CLI 加密。
- `secrets.local.json`：建议的本地明文副本，仓库已忽略，请勿提交远端。
- `profiles/`：按阶段覆盖配置（可选），例如 `profiles/p1.env`。

> 不要提交解密后的敏感文件；如需更新密钥，请使用 `dc-cli secrets encrypt --input config/secrets.template.json` 重建密文，并在 PR 中说明影响范围。
