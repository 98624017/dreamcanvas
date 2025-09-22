### **项目代号：DreamCanvas - 详细开发文档 (2025-09-22)**

#### **1. 目标与范围 (Scope)**
- 构建可跨平台运行的桌面端 AI 创作工具，服务 P0~P3 四个交付阶段。
- 以“项目”为核心抽象，统一画布、素材库、提示词上下文、即梦任务与助手能力。
- 在满足基本功能的同时，确保环境部署、凭据安全、数据备份和性能指标可量化。

#### **2. 整体架构 (Architecture Overview)**
```
┌────────────┐      ┌──────────────┐      ┌─────────────────────┐
│ Next.js UI │◄────►│ Tauri Bridge │◄────►│ Python FastAPI Core │
└────────────┘      └──────────────┘      └─────────────────────┘
      ▲                    ▲                           ▲
      │ Zustand Store      │ Command/IPC               │ HTTP (localhost)
      ▼                    ▼                           ▼
┌──────────────┐   ┌───────────────┐            ┌────────────────────┐
│ Asset Storage│   │ Config & Logs │            │ External Services   │
└──────────────┘   └───────────────┘            └────────────────────┘
```
- 前端使用 Next.js 14 (App Router) + TypeScript + Tldraw v2，负责 UI/交互与状态管理，代码位于 `apps/desktop/`。
- Tauri v2 Rust Core 负责窗口管理、文件系统访问、Python 进程生命周期、命令调度与安全沙箱，存放于 `apps/desktop/src-tauri/`。
- Python FastAPI 后端处理即梦 API、AI 抠图、LLM 调用、凭据管理与备份任务，目录 `src-py/`。

#### **2.1 工作区布局 (Workspace Layout)**
```
root
├── apps/desktop/           # Next.js + Tauri 主应用
│   ├── src/app/            # App Router 入口与页面
│   ├── src/modules/        # 画布、素材、任务等功能域
│   └── src-tauri/          # Rust 壳及配置
├── src-py/                 # FastAPI 后端（Poetry）
│   ├── dreamcanvas/        # API、服务与配置
│   └── tests/              # Pytest 用例
├── scripts/                # 环境自检、E2E、备份脚本
├── config/                 # default.env、secrets 模板
└── tests/perf/             # k6 性能脚本
```

#### **3. 模块职责 (Responsibilities)**
- **Next.js 层**：
  - `app/`：路由、布局与全局 Provider。
  - `components/canvas/`：封装 Tldraw 组件与自定义工具栏。
  - `components/panels/`：项目、素材库、提示词、任务面板。
  - `lib/`：Tauri 调用封装、API Hook、持久化工具。
  - `store/`：Zustand 管理项目、任务、UI 状态。
- **Tauri Rust 层**：
  - 统一暴露 `list_projects`、`load_project`、`save_project`、`call_python_api` 等命令。
  - 管理 Python 子进程：启动、心跳、自愈，向日志目录写入监控信息。
  - 负责文件系统访问与加密解密接口（调用 Rust crate `ring`）。
- **Python FastAPI 层**：
  - `main.py`：应用入口、路由注册、生命周期事件（启动加载配置、初始化 TokenManager）。
  - `api/`：`jimeng.py`、`tools.py`、`diagnostics.py`。
  - `services/`：封装即梦 HTTP、LLM、图像处理、备份任务调度。
  - `core/`：来自 `Comfyui_Free_Jimeng` 的 API 客户端与 token 管理实现，通过 Git 子模块跟踪。

#### **4. 里程碑与工程交付 (Milestones)**
| 阶段 | 技术重点 | 关键交付 | 验收要点 |
| --- | --- | --- | --- |
| P0 环境基线 | 脚手架、跨平台配置、凭据加密、数据目录规范 | 初始化脚手架、PowerShell 环境脚本、`.env.example`、`secrets.enc` 生成工具 | 前后端可启动、自动化自检通过、加密凭据读写受控 |
| P1 MVP Alpha | 核心单项目闭环、自动保存、即梦文生图、AI 抠图、基础日志 | 画布模块、素材库、任务面板、失败重试、基础日志与诊断导出 | 关键路径 E2E 测试通过、异常处理覆盖 1015/1016/1003 |
| P2 Beta 扩展 | 多项目资产共享、视觉助手、上下文面板、积分监控 | 视觉助手服务、跨项目复制、上下文同步、密钥阈值告警 | ≥5 项目并行测试、助手稳定率 95%、告警可复现 |
| P3 GA 稳定 | 性能/备份优化、权限审计、发布流程 | 备份恢复工具、性能优化报告、CI 发布脚本、升级/回滚方案 | 性能指标达标、灾备演练通过、发布 Checklist 完整 |

#### **5. 环境与配置 (Environment & Configuration)**
- **前端**：Node.js 20 + pnpm，使用 `pnpm install`，开发时运行 `pnpm dev --filter web`。
- **Rust/Tauri**：Rust stable + `tauri-cli`；`pnpm tauri dev` 作为统一启动命令。
- **Python**：推荐使用 `conda create -n dreamcanvas python=3.11` 或 venv；通过环境变量 `DC_PYTHON_BIN` 指定解释器路径，Tauri 启动时读取。
- **配置文件**：
  - `config/default.env`：公共配置（API Endpoint、默认模型、日志级别）。
  - `config/secrets.template.json`：本地填写敏感信息的明文模板。
  - `config/secrets.enc`：通过 `dc-cli secrets encrypt --input config/secrets.template.json` 生成的密文，随代码库提交。
  - `src-py/config/config.yaml`：后端参数（模型、尺寸映射、超时等），支持按阶段覆盖。
- **脚本**：`scripts/setup.ps1` 自动完成依赖检查、Python 环境核对、子模块同步、加密文件生成；`scripts/start-backend.ps1` 负责以 `uvicorn` 启动 FastAPI 服务（支持 `-Reload`、后台模式与自定义监听地址）；`scripts/self-test.ps1` 用于一键执行 lint/test/pytest 并输出 JSON 报告；`scripts/collect-logs.ps1` 打包日志、运行手册与依赖树。
- **Tauri 命令**：`start_backend`、`stop_backend`、`backend_status` 由 `BackendManager` 托管 Python 子进程，并将 stdout/stderr 通过事件 `backend://stdout`、`backend://stderr` 推送给前端，实现桌面端的实时日志调试。

#### **6. 数据持久化与目录布局 (Data Persistence)**
```
%APPDATA%/DreamCanvas/
├── projects/
│   └── {projectId}/
│       ├── manifest.json        # 项目元数据、版本、校验和
│       ├── canvas.json          # Tldraw Snapshot (gzip+base64)
│       ├── assets/
│       │   ├── images/          # 原始/生成图片，文件名={assetId}.png
│       │   ├── prompts/         # 提示词模板，.json
│       │   └── components/      # 视觉助手生成的组件片段
│       ├── history/             # 任务调用历史，按日期分文件
│       └── snapshots/           # 画布快照
├── backups/                     # 增量备份，命名 {date}-{projectId}.bak
└── logs/                        # Rust、Python、前端日志（JSON Lines）
```
- 所有写操作遵循“临时文件 → 校验 → 原子替换”流程。
- 备份任务由 Python APScheduler 在每日 02:00 执行，保留最近 7 天并支持 CLI 恢复。

#### **7. 核心数据结构 (Type Definitions)**
```typescript
// file: src/lib/types.ts
import type { TLRecord, TLStoreSnapshot } from '@tldraw/tldraw';

export interface ProjectManifest {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  version: string; // 语义化版本，追踪迁移
  canvasChecksum: string;
}

export interface ProjectPayload {
  manifest: ProjectManifest;
  canvas: TLStoreSnapshot<TLRecord>;
  assets: Asset[];
  history: GenerationRecord[];
}

type AssetKind = 'image' | 'text_prompt' | 'generated_component';

export interface Asset {
  id: string;
  projectId: string;
  kind: AssetKind;
  uri: string; // 相对路径或 data URL
  metadata: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
}

export interface GenerationRecord {
  id: string;
  prompt: string;
  sessionId: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
  resultUris: string[];
  error?: string;
  createdAt: number;
  completedAt?: number;
}
```

#### **8. Tauri Commands & FastAPI Endpoints**
| Command | 参数 | 描述 |
| --- | --- | --- |
| `list_projects` | `()` | 读取 `projects/` 目录返回 manifest 摘要 |
| `load_project` | `{ projectId }` | 解密并加载 `ProjectPayload`，返回前端 |
| `save_project` | `{ payload: ProjectPayload }` | 写入项目数据并触发快照 |
| `create_project` | `{ name }` | 生成 manifest、初始化目录结构 |
| `call_python_api` | `{ method, endpoint, payload }` | 通过 HTTP 调用 FastAPI（会自动附带鉴权 Token） |

| Endpoint | 方法 | 描述 |
| --- | --- | --- |
| `/jimeng/generate` | POST | 支持文生图/图生图，根据 payload 判断模式；包含重试与轮询逻辑 |
| `/jimeng/history` | GET | 查询任务状态，供前端订阅更新 |
| `/tools/segment_image` | POST | rembg 抠图，返回 base64 PNG |
| `/tools/llm_text` | POST | 调用 Cloudflare Gateway 代理的 LLM，返回响应文本 |
| `/tools/llm_vision` | POST | 上传画布截图并获取组件描述或 UI 片段 |
| `/system/diagnostics` | GET | 返回版本、依赖、健康检查结果 |
| `/system/backup` | POST | 触发备份任务或恢复指定备份 |

#### **9. 运行时流程 (Runtime Flow)**
1. Tauri 启动 Rust 主进程，读取 `DC_PYTHON_BIN` 并检查解释器；若缺失提示执行 `scripts/setup.ps1`。
2. Rust 启动 Python FastAPI（subprocess），监听 `127.0.0.1:18500`，并通过健康检查确认可用。
3. 前端加载时调用 `list_projects`，Zustand 初始化当前项目状态，并加载 `canvas.json`。
4. 用户操作画布时，前端监听变更并通过防抖每 5 秒触发 `save_project` 更新。
5. 调用即梦功能时，前端组装 payload → Tauri `call_python_api` → FastAPI 任务提交 → 輪询 `history`，完成后通知前端更新素材库与画布。
6. 备份任务由 Python APScheduler 按计划运行，同时支持前端手动触发。

#### **10. 观测与性能 (Observability & Performance)**
- **指标埋点**：任务排队时长、生成耗时、失败原因、备份耗时、画布保存耗时。
- **日志格式**：统一使用 JSON Lines，字段包含 `timestamp`、`module`、`level`、`message`、`context`。
- **性能目标**：
  - 首屏渲染≤3 秒；画布交互帧率≥55fps；素材库搜索≤1 秒。
  - 即梦任务 95% 在 90 秒内完成首次结果。
  - rembg 抠图平均耗时<1.5 秒（1080p 图片）。
- **测试策略**：提供 Vitest/Playwright 前端测试、Pytest 后端测试、k6 压测脚本模拟任务高峰。

#### **11. 安全与凭据管理 (Security)**
- 凭据全部存储在 `config/secrets.enc`，通过 PBKDF2+Fernet 加密；使用 `dc-cli secrets encrypt`/`decrypt` 管理密文，`SecretManager` 负责运行期读取与缓存。
- 运行时需要在桌面端或 CI 中设置 `DC_SECRETS_PASSPHRASE`，后端启动时即可解密凭据；未提供口令会触发显式错误提醒。
- sessionid 更新流程：前端触发 → 运行 `dc-cli secrets decrypt` 导出明文或更新模板 → 加密后写回密文 → FastAPI 通过 `SecretManager` 刷新缓存。
- 日志默认脱敏：当记录 HTTP 请求时，仅保留 hash 后 sessionid，禁止写入明文。
- 外部请求通过 Cloudflare Gateway 控制速率；配置文件中可设置全局速率限制，避免触发即梦风控。

#### **12. 依赖与版本管理 (Dependencies)**
- 通过 `pnpm` workspace 管理 `web` 与 `tauri` 子包；使用 `pnpm lint`、`pnpm test`、`pnpm build` 作为 CI 基础任务。
- Python 依赖写入 `src-py/pyproject.toml` 与 `poetry.lock`，避免手工复制 `requirements.txt`。
- `core/` 目录改为 Git 子模块：`git submodule add https://github.com/<org>/Comfyui_Free_Jimeng core`，每个版本升级需在变更日志中记录。
- 使用 Renovate/GitHub Actions 监控依赖更新，保持与 Tldraw、Tauri、FastAPI 主版本兼容。

#### **13. 文档与交付物 (Documentation)**
- 每个阶段更新：需求文档、设计稿、接口说明、部署手册、测试报告。
- 在 `docs/changelog.md` 维护阶段变更记录；CI 校验确保文档更新与代码变更同步。
- 发布前需要输出用户手册（项目管理、账号配置、常见故障排查）与安全自查报告。

#### **14. 测试与 CI 流水线 (Testing & CI)**
- **CI 平台**：GitHub Actions（`ci.yml`）采用 Windows runner，执行统一自检流程并上传自检报告。
- **任务拆分**：
  - `self-test`：`scripts/self-test.ps1` 串行执行 `pnpm --filter @dreamcanvas/desktop lint`、`pnpm run lint:docs`、`pnpm --filter @dreamcanvas/desktop test`、`python -m poetry run pytest`，输出 JSON 报告。
  - `e2e`：Playwright 运行关键用户路径脚本，使用项目模板数据启动 Tauri 应用。
  - `perf`：k6 压测脚本按周定时运行，记录即梦任务延迟与备份耗时。
- **准入门槛**：任何管道失败阻止合并；`self-test` 为 PR 准入必选项，覆盖率低于阈值或基线性能回退时需提供豁免说明。
- **工具支持**：`scripts/self-test.ps1` 已纳入 CI；`scripts/run-e2e.ps1`、`scripts/run-perf.ps1` 可按需在流水线中扩展，结果通过 Allure 或 HTML 报告存档。

#### **15. 版本控制策略 (Versioning)**
- **分支结构**：`main` 用于可发布版本；`develop` 用于日常集成；`release/Px` 对应阶段稳定分支，所有阶段内迭代从该分支衍生 feature 分支。
- **标签规则**：阶段验收通过后在 `main` 打标签 `vP{阶段号}.{迭代}.{修订}`，并将发布记录同步至 `docs/changelog.md`。
- **发布流程**：`release/Px` → CI 通过 → 创建 `release` PR 合并到 `main` → 打标签 → 触发发布脚本（生成安装包、文档、QA 报告）。
- **回滚预案**：维护 `rollback.md`，记录每个版本的快照位置、备份包、恢复指令；CI 在打标签时自动保存项目数据 SHA 与依赖版本清单。
- **审计要求**：阶段结束时整理分支、关闭过期 feature 分支，并汇总差异到阶段复盘文档。
