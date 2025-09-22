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

> 每次更新时请复制上述表格行，替换为真实数据；若存在紧急修复补丁，请在同一发布日期下追加条目并注明差异。
