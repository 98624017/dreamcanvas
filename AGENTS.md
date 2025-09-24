# Repository Guidelines

## 项目结构与模块组织
- `apps/desktop/`：Next.js + Tauri 桌面端，`src/app/` 为 App Router 入口，`src/modules/` 聚合系统与项目域功能；`playwright/` 存放 E2E 脚本与配置。
- `apps/desktop/src-tauri/`：Rust 核心，负责窗口、文件系统与 Python 子进程调度，`src/project.rs` 管理磁盘项目存储。
- `src-py/`：使用 Poetry 管理的 FastAPI 服务，`dreamcanvas/api/` 暴露系统、即梦、工具路由。
- `tests/`：跨栈脚本集合，`perf/` 保存 k6 压测用例。
- `%APPDATA%/DreamCanvas/`：运行期项目、备份、日志目录；结构详见 `docs/DreamCanvas - 详细开发文档.md`。

## 构建、测试与开发命令
- Shell=PowerShell > `pnpm install`：安装 Node 依赖并准备 Tauri CLI。
- Shell=PowerShell > `pnpm tauri`：一体化调试桌面应用（Next + Tauri + FastAPI）。
- Shell=PowerShell > `pnpm --filter @dreamcanvas/desktop test`：运行 Vitest 前端用例。
- Shell=PowerShell > `cd src-py; poetry install && poetry run pytest`：安装并执行后端测试。
- Shell=PowerShell > `scripts/setup.ps1`：环境自检、目录初始化、`.env` 与 `secrets.enc` 模板准备。
- Shell=PowerShell > `pnpm backend`：后台启动 FastAPI（默认 `--reload`），终端可直接返回；如需前台调试使用 `scripts/start-backend.ps1 -Reload`。
- Shell=PowerShell > `pnpm exec playwright install --with-deps`：首次运行 Playwright 前安装浏览器依赖。
- Shell=PowerShell > `scripts/run-e2e.ps1 [-InstallBrowsers]`：启动 Playwright E2E；`scripts/run-perf.ps1` 触发 k6 压测。
- Shell=PowerShell > `scripts/self-test.ps1 [-IncludeE2E] [-InstallBrowsers]`：一键执行 lint/test/pytest（可选 E2E），并生成 JSON 报告。
- Shell=PowerShell > `dc-cli secrets encrypt --input config/secrets.template.json --output config/secrets.enc`：使用主口令加密敏感配置；如需明文配置进行调试，可执行 `dc-cli secrets init --template ... --output config/secrets.json` 生成副本。
- Shell=PowerShell > `scripts/collect-logs.ps1 [-IncludeSelfTest] [-IncludePoetryTree]`：打包日志、运行手册与诊断信息，便于问题排查。
- Tauri 内置命令：`start_backend`、`stop_backend`、`backend_status` 用于管理 FastAPI 子进程；前端通过 `@/modules/system/backendClient` 调用，并将日志广播到 `backend://stdout`/`backend://stderr` 事件。
## 代码风格与命名规范
- TypeScript 使用 2 空格缩进，遵循 ESLint + Prettier；组件命名采用 PascalCase，hooks 使用 `use*` 前缀。
- CSS/全局样式集中在 `src/app/globals.css`，模块级样式置于对应子目录。
- Python 使用 ruff + black 规则（`pyproject.toml`）；服务类以功能域命名（如 `services/jimeng.py`）。
- 配置变量统一 `DC_*` 前缀，阶段性覆盖放入 `config/profiles/`。

## 测试与质量要求
- 前端：Vitest + Testing Library 覆盖组件，Playwright 负责 MVP 闭环；关键交互需配快照或视觉回归（P2 起）。
- 后端：Pytest 覆盖健康检查、即梦任务异常；引入外部接口前先编写契约测试。
- CI 门槛：GitHub Actions（`ci.yml`）调用 `scripts/self-test.ps1` 执行 `pnpm lint`、`pnpm run lint:docs`、`pnpm --filter @dreamcanvas/desktop test`、`python -m poetry run pytest`，需全部通过；性能、备份基线作为阶段性检查项。
- 覆盖率目标≥75%；若低于阈值需在 PR 中给出补测计划。
## 提交与拉取请求规范
- Commit 使用英文祈使句 + 简短描述（如 `Add P0 fastapi skeleton`），一类变更一条提交，必要时补充 Co-authored-by。
- PR 描述需包含：变更目的、测试结果、关联阶段、风险与回滚策略；涉及 UI 变更附截图或录屏。
- 合并前需确认 `docs/changelog.md`、`docs/rollback.md` 是否同步更新，未更新需在 PR 说明原因。

## 安全与配置提示
- 不提交 `config/secrets.enc` 明文或解密结果；敏感调试日志先执行 `scripts/redact.ps1`。
- Python 解释器路径通过 `DC_PYTHON_BIN` 控制；运行 `scripts/setup.ps1` 后确认脚本输出。
- 凭据管理：使用 `dc-cli secrets encrypt` 维护密文，并在本地/CI 设置 `DC_SECRETS_PASSPHRASE`；如需代理，可在 `config/secrets.template.json` 的 `proxy.http/https` 字段写入，例如 `http://127.0.0.1:7897`。

## 发布、版本与回滚
- 分支模型：`main` + `develop` + `release/Px`，阶段结束在 `main` 打 `vP{阶段}.{迭代}.{修订}` 标签。
- 发布完成后 24 小时内更新 `docs/changelog.md`，并在 `docs/rollback.md` 记录可回退标签、备份位置与脚本。
- 阶段冻结周仅接受阻断性修复，需双人评审与测试证明。
