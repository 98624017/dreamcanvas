# 即梦AI逆向技术报告

> 注：2025-09-22 起，ComfyUI 节点代码已归档；以下内容仅用于追溯历史实现与协议细节，当前桌面端改造请参考 `docs/DreamCanvas - 详细开发文档.md`。

## 1. 背景与目标
- **项目定位**：本仓库原为 ComfyUI 插件，通过复刻 https://jimeng.jianying.com 的 Web 流量，实现即梦 AI 文生图、图生图、视频生成及高清增强能力的本地调用。
- **逆向目的**：剥离浏览器限制，获取稳定可重放的 API 调用流程，为后续封装独立客户端或服务化调度提供基础。
- **研究范围**：聚焦认证链路、任务提交协议、任务状态轮询、图片上传签名、账号积分与排队机制等核心环节。

## 2. 系统整体架构
- **核心模块划分**：
  - `core/token_manager.py`：负责账号切换、动态签名、Cookie 构造、积分查询与上传凭证获取。
  - `core/api_client.py`：封装文生图、图生图、上传、历史查询、队列状态解析等 HTTP 调用。
  - `jimeng_image_node.py` / `jimeng_video_node.py` / `jimeng_hd_enhancer_node.py`：面向 ComfyUI 的节点包装层，负责加载配置、调用 `ApiClient` 并处理 UI 反馈。
- **配置与运行时**：
  - `config.json.template` 预置模型、分辨率、超时、UI 元数据，用户仅需补齐 `sessionid`。
  - 节点初始化时自动复制模板为 `config.json` 并实例化 `TokenManager`、`ApiClient`。

## 3. 认证机制逆向分析
- **基线 Cookie**：由 `TokenManager._generate_cookie` 以账号 `sessionid` 为核心组合 `sessionid_ss / sid_tt / sid_guard / uid_tt / web_id` 等字段，模拟浏览器持久化状态。
- **web_id 管理**：首次运行为每个账号生成 19 位随机 `web_id` 并缓存，若 Cookie 中已有则沿用（对应 `TokenManager._extract_web_id_from_cookie`）。
- **动态参数生成**：
  - `msToken`：随机 107 位字符，每次请求唯一。
  - `a_bogus`：32 位随机字符串，当前服务端仅校验存在性。
  - `sign`：`md5("9e2c|{api_path后7位}|{pf=7}|{version=5.8.0}|{timestamp}||11ac")`，与线上抓包结果匹配。
- **请求头对齐**：`ApiClient._get_headers` 依据请求 URI 自动决定是否将 `msToken`/`a-bogus` 留在 Header 或改入 Query 参数，与官网最新行为保持一致。

## 4. 文生图流程（`ApiClient.generate_t2i`）
1. **模型映射**：读取 `config.params.models`，将 UI 选择转换为真实 `model_req_key`。
2. **尺寸计算**：根据比例表（1k/2k/4k）得出 `width/height`，并附带 `image_ratio` 与 `large_image_info`。
3. **请求构造**：拼装 `draft_content` 草稿 JSON、`metrics_extra`、`babi_param` 等字段，完全复刻网页工作流。
4. **认证附加**：调用 `TokenManager.get_token`，将 `msToken`/`a_bogus` 放入 URL Query，其他签名置于 Header。
5. **任务排队**：解析返回中的 `history_record_id`，即时检查 `queue_info`，如果排队则返回提示并在后续轮询。
6. **轮询策略**：使用 `get_history_by_ids` 接口，按 `config.timeout.check_interval` 重试直至状态码 50（完成），并从 `resources`/`draft_content` 中解析图片地址。

## 5. 图生图与参考图流程（`ApiClient.generate_i2i`）
1. **输入处理**：将 ComfyUI 张量暂存为本地图片（`_save_input_image`），支持多张参考图。
2. **积分校验**：`TokenManager.find_account_with_sufficient_credit(2)` 保证账号余额满足图生图资费。
3. **上传授权**：
   - `get_upload_token` 请求临时 STS，返回 `access_key/secret_key/session_token` 及空间信息。
   - `_get_upload_token` 内部调用 `get_authorization` 构造 AWS SigV4 签名，调用 ByteDance ImageX `ApplyImageUpload`。
4. **数据上传**：按授权指引向具体 `UploadHost` POST 二进制内容，附带 CRC32 校验与授权头。上传成功后提交 `CommitImageUpload`。
5. **生成请求**：携带上传得到的 `image_uri` 组装 `draft_content` 的 `ref_image` 段，流程与文生图一致；同样处理排队与轮询。

## 6. 其他接口能力
- **积分管理**：`get_credit`、`receive_daily_credit` 复刻商城接口，实现账户积分读取与每日领取。
- **高清增强**：`jimeng_hd_enhancer_node.py` 针对 `/aigc_hd` 等接口定制 `a_bogus` 生成方式（Base64(sessionid + 时间戳 + 常量)），说明部分接口需要固定前缀。
- **视频生成**：`jimeng_video_node.py` 组合 `token_manager` 与 `api_client` 中的视频模型配置，并实现批量任务提交（含队列提示、素材上传等流程）。

## 7. 安全与风控观察
- 目前服务器主要依赖 `sessionid` + 基本随机串判断合法性；缺少 UA/指纹校验，因此插件通过伪造随机值即可通过。
- 若官方升级 `a_bogus` 计算或加入 TLS 指纹，需重新抓包分析；建议在独立客户端内保留回放能力和调试日志。
- 建议限制请求频率，避免触发 `ret=1016`（频率限制）和 `ret=1015`（风控拦截）。

## 8. 独立客户端演进建议
- **方案一：SDK 化复用**
  - 将 `core` 目录抽象为 Python 包，直接暴露生成、轮询、上传等方法，桌面端仅负责 UI 与配置管理。
  - 技术要点：打包依赖、兼容多平台 Python 环境、提供简明的错误码与异常类型，便于调用方捕获。

- **方案二：服务化部署**
  - 在后端部署 `TokenManager`、`ApiClient`，对外暴露 REST/gRPC 接口，实现多账号池、限流、日志集中化。
  - 技术要点：鉴权、调度算法（基于积分与排队长度选择账号）、接口幂等性、防止重复提交、任务持久化。

- **方案三：渐进式稳定性增强与监控体系**
  - **任务监控**：在客户端内增加任务状态机，记录提交时间、队列位置、轮询次数，结合本地 SQLite/InfluxDB 持久化历史，便于追踪异常。
  - **失败重试与降级**：针对常见错误码（1015/1016/1003）建立可配置重试策略，自动切换账号或延迟重试，必要时回退到低分辨率/低费用模型。
  - **网络与代理支持**: 抽象 HTTP 层，允许配置企业代理、重放最近一次成功请求的 header 组合，观察反爬策略变化。
  - **报警与通知**：接入本地通知或 webhook，一旦排队超时、积分不足或签名失效，及时提醒运维或终端用户。
  - **流量审计**：可选写入原始请求/响应日志（注意脱敏 sessionid），为后续升级签名算法或适配移动端接口提供数据资产。

- **合规提示**
  - 在产品层提醒用户自行保管 `sessionid`，提供快速更新与失效检测通道，避免共享凭证导致账号违规。

## 9. 后续工作方向
- 跟踪官网协议更新，及时校准 `sign/a_bogus` 生成逻辑。
- 研究是否存在 WebSocket/长轮询接口以替代轮询查询，降低延迟和流量。
- 抽象模型、分辨率、任务参数配置成外置 YAML/JSON，方便终端用户扩展。
- 为图生图/视频任务补充进度查询、超时回退策略，提高客户端交互体验。

## 10. 附录：关键文件索引
- `core/token_manager.py`：认证参数与账号管理实现。
- `core/api_client.py`：HTTP 流程封装与任务调度逻辑。
- `jimeng_image_node.py`：ComfyUI 图像节点初始化流程。
- `jimeng_video_node.py`：视频节点及队列反馈实现。
- `jimeng_hd_enhancer_node.py`：高清增强接口调用与校验串生成。
- `获取认证参数指南.md`：抓包获取 sessionid 的操作指引。
