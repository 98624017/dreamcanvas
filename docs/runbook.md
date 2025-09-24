# DreamCanvas 本地运行与诊断手册

## 0. 凭据初始化
1. 将 `config/secrets.template.json` 复制到安全位置并填写 sessionid、API Token 等信息（如需本地代理，可在 `proxy.http/https` 中写入 `http://127.0.0.1:7897`）。
2. Shell=PowerShell > `dc-cli secrets encrypt --input config/secrets.template.json --output config/secrets.enc`
3. 在当前终端或系统环境中设置 `DC_SECRETS_PASSPHRASE="<你的主口令>"`，后端启动时即可加载密文。

> 若暂未生成密文或设置口令，后端会尝试读取 `config/secrets.local.json` 的明文配置并在日志中给出警告。请在验证后尽快执行加密流程，避免敏感数据长期明文存储。

## 1. 启动流程
1. Shell=PowerShell > `pnpm install`
2. Shell=PowerShell > `pnpm backend`（后台启动 FastAPI，默认启用 `--reload`）或 `scripts/start-backend.ps1 -Reload`
3. （可选）启动前设置 `DC_WEB_APP_URL`，或在客户端启动器内填写“浏览器访问地址”并保存，即可统一管理入口（示例：`http://127.0.0.1:3000`）。
4. Shell=PowerShell > `pnpm tauri`（启动客户端启动器，可在界面内保存地址、选择是否开机自动打开浏览器）

> 如需自定义监听地址/端口，可执行 `scripts/start-backend.ps1 -Reload -ListenHost 0.0.0.0 -Port 18501`。`-Detached` 已在 `pnpm backend` 默认启用。

## 2. 后端诊断
- 浏览器主界面展示实时健康状态与日志面板；客户端窗口提供启动器与诊断入口。
- 即梦任务接口会在 `metadata.queueMessage` 中提示排队耗时，`metadata.historyId` 可用于与官网工单对齐；失败时可在 `metadata` 中查看 `JimengService` 记录的 trace。
- `/tools/segment_image` 已通过示例脚本验证，结果文件保存在 `tests/output/segment_alpha.png`，可用于演示抠图透明通道效果。
- 即梦成功任务会自动写入 `%APPDATA%/DreamCanvas/projects/<projectId>`，生成的 PNG 存放在 `assets/images/`；`metadata.downloaded=true` 表示已落地本地文件。
- 需要查看更多信息时，运行 `scripts/collect-logs.ps1 -IncludeSelfTest -IncludePoetryTree` 生成诊断包，或订阅 `backend://stdout`、`backend://stderr` 事件。

## 3. 自检与自动化测试
- Shell=PowerShell > `scripts/self-test.ps1 -IncludeE2E -InstallBrowsers` 生成 `self-test-report.json` 并执行 Playwright；本地可省略 `-IncludeE2E` 加快迭代。
- Shell=PowerShell > `scripts/self-test.ps1 -InstallBrowsers` 在需要时仅运行单元/集成测试。
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
- **即梦错误码 1015/1016/1003**：持续轮询同一账号会自动记录在 `JimengService` trace；遇到限频或积分不足时，保留 `metadata.historyId` 并在日志中搜索对应 `errorCode`，按 `docs/获取认证参数指南.md` 操作刷新凭据或补充积分。
