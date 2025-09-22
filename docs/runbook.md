# DreamCanvas 本地运行与诊断手册

## 0. 凭据初始化
1. 将 `config/secrets.template.json` 复制到安全位置并填写 sessionid、API Token 等信息。
2. Shell=PowerShell > `dc-cli secrets encrypt --input config/secrets.template.json --output config/secrets.enc`
3. 在当前终端或系统环境中设置 `DC_SECRETS_PASSPHRASE="<你的主口令>"`，后端启动时即可加载密文。

## 1. 启动流程
1. Shell=PowerShell > `pnpm install`
2. Shell=PowerShell > `pnpm backend`（后台启动 FastAPI，默认启用 `--reload`）或 `scripts/start-backend.ps1 -Reload`
3. Shell=PowerShell > `pnpm tauri`

> 如需自定义监听地址/端口，可执行 `scripts/start-backend.ps1 -Reload -ListenHost 0.0.0.0 -Port 18501`。`-Detached` 已在 `pnpm backend` 默认启用。

## 2. 后端诊断
- 桌面端首页展示实时健康状态与日志面板。
- 需要查看更多信息时，运行 `scripts/collect-logs.ps1 -IncludeSelfTest -IncludePoetryTree` 生成诊断包，或订阅 `backend://stdout`、`backend://stderr` 事件。

## 3. 自检与自动化测试
- Shell=PowerShell > `scripts/self-test.ps1` 生成 `self-test-report.json`，串行执行前端 lint、Markdown lint、Vitest 与 Pytest。
- Shell=PowerShell > `scripts/self-test.ps1 -IncludeE2E -InstallBrowsers` 追加 Playwright E2E 并安装依赖。
- 独立命令：
  - `pnpm --filter @dreamcanvas/desktop lint`
  - `pnpm --filter @dreamcanvas/desktop test`
  - `cd src-py; python -m poetry run pytest`
  - `scripts/run-e2e.ps1 -InstallBrowsers`

## 4. 常见问题
- **后台未启动**：检查是否安装 Poetry，并配置 `DC_PYTHON_BIN`。
- **端口占用**：确认 18500 端口空闲，必要时调整 `scripts/start-backend.ps1` 的 `-Port`。
- **日志未刷新**：确保 Tauri 环境就绪，或运行 `scripts/collect-logs.ps1` 收集诊断信息。
- **CI 告警**：`scripts/self-test.ps1` 失败时查看 JSON 报告对应步骤与错误信息。
