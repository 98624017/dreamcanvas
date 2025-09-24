# DreamCanvas 版本变更记录

> 维护人：发布负责人；更新频率：每次合并 `release/Px` → `main` 后立即更新。

## 记录格式
- **版本标签**：`vP{阶段号}.{迭代}.{修订}`（示例：`vP1.0.0`）。
- **发布日期**：UTC+8。
- **阶段范围**：对应需求文档中的里程碑编号。
- **关键特性**：列出 3-5 个最重要的增强或修复。
- **质量指标**：列出覆盖率、性能基线、已知风险。

## 示例
| 版本 | 发布日期 | 阶段范围 | 关键特性 | 质量指标 |
| --- | --- | --- | --- | --- |
| vP0.0.1 | 2025-09-22 | P0 环境基线 | - 初始化 Next.js + Tauri 脚手架<br>- 搭建 FastAPI 基础路由<br>- 新增环境自检脚本与配置模板 | - 自动化测试脚手架就绪<br>- 覆盖率目标≥75%（后续补录） |
| vP0.0.2 | 2025-09-22 | P0 环境基线 | - 加入后端健康轮询 Hook 与页面状态看板<br>- 新增 `scripts/start-backend.ps1` 热重载脚本 + Tauri BackendManager 命令<br>- 页面引入实时日志控制台，Tauri 广播 stdout/stderr 事件 | - 前端单测通过<br>- FastAPI 健康用例通过 |
| vP0.0.3 | 2025-09-22 | P0 环境基线 | - 正式下线 ComfyUI 节点脚本与 `core/` 目录<br>- 重写 `__init__.py` 提示迁移至 `src-py/dreamcanvas` 实现<br>- 更新逆向报告为历史档案，新增本地运行手册 | - python requirements 精简，无 torch/numpy 依赖 |
| vP0.0.4 | 2025-09-22 | P0 环境基线 | - Tauri 后端托管支持后台启动并推送 stdout/stderr 事件<br>- 桌面端首页订阅 started/stopped 事件并提供可视提示<br>- `scripts/self-test.ps1` 聚合 lint/test/pytest 并生成 JSON 报告 | - `scripts/self-test.ps1` 全量通过<br>- 前端/后端单测通过并无 React 告警 |
| vP0.0.5 | 2025-09-22 | P0 环境基线 | - 新增 `dc-cli secrets encrypt/decrypt`，落地 PBKDF2+Fernet 加密流程<br>- 引入 `SecretManager` 统一加载密文，支持 `DC_SECRETS_PASSPHRASE`<br>- 扩充自检与文档模板（`config/secrets.template.json`、Runbook/AGENTS 更新） | - 新增 Pytest 覆盖 CLI/加密模块<br>- 自检脚本校验命令退出码并全部通过 |
| vP0.1.0 | 2025-11-15 | P0 环境基线 | - 完成 `scripts/setup.ps1` 自检<br>- 集成 `DC_PYTHON_BIN` 配置<br>- 初版凭据加密 CLI | - Lint/Test 100% 通过<br>- 前端覆盖率 76%<br>- 备份任务成功率 95% |
| vP1.0.0 | 2025-12-05 | P1 MVP Alpha | - 前端落地项目侧栏、画布自动保存、任务面板与素材库联动<br>- FastAPI 接入 `JimengService` 模拟任务生命周期、任务取消与备份导出<br>- Tauri `ProjectManager`/Python `ProjectStorage` 打通磁盘持久化，自动恢复空白画布<br>- 新增 Playwright 闭环脚本与 Zustand/任务单测，`self-test` 支持可选 E2E | - Vitest/Playwright/Pytest 全绿<br>- `scripts/self-test.ps1 -IncludeE2E` 通过<br>- 项目数据自动保存 2s 内完成 |
| vP1.0.1 | 2025-09-22 | P1 MVP Alpha | - `JimengService` 接入真实即梦 API，回传排队信息与 trace<br>- 支持 `config/secrets.local.json` 明文回退并更新运行手册<br>- `self-test` 默认执行 Playwright E2E，工作流上传报告与截图 | - Vitest/Playwright/Pytest 全量通过<br>- 自检产出 artefact（JSON+截图） |
| vP1.0.2 | 2025-09-22 | P1 MVP Alpha | - 客户端回归“启动器 + 浏览器主界面”模式，新增 UI 设置页，可保存 Web 入口并选择自动打开<br>- 启动器改用本地配置文件（`ui-settings.json`），保留 `DC_WEB_APP_URL` 作为兼容入口，去除 `.next` 依赖<br>- 文档回滚至浏览器主界面的操作指引，补充忽略目录 `src-tauri/gen`/`icons` | - `pnpm tauri` 自检通过，客户端无 `asset not found` 报错<br>- Web 端功能与既有单测不受影响 |
| vP1.0.3 | 2025-09-22 | P1 MVP Alpha | - 使用正式 `sessionid` 完成单图/多图文生图（任务 4265368139020、4265076452108）并记录素材<br>- 自动将成功任务写入项目 `P1-真实任务演示`，保存 8 张离线 PNG 与 `history/import.log`<br>- 手动调用 `/tools/segment_image`，输出示例 `tests/output/segment_alpha.png` 验证透明通道<br>- 通过 `pnpm install --force` 修复 Next.js 软链接缺失，`scripts/self-test.ps1 -IncludeE2E` 产出报告与截图 | - `self-test-report.json` 全绿，Playwright 报告与截图归档<br>- 10 次并发真实任务成功率 100%，平均排队时间 < 6s |

> 每次更新时请复制上述表格行，替换为真实数据；若存在紧急修复补丁，请在同一发布日期下追加条目并注明差异。
