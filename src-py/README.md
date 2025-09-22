# DreamCanvas FastAPI 后端

- 使用 Poetry 管理依赖：`poetry install`
- 本地开发：`poetry run uvicorn dreamcanvas.app:app --reload --port 18500`
- 运行测试：`poetry run pytest`

后续迭代将在 `dreamcanvas/services/` 目录中实现即梦 API、备份与诊断逻辑。
