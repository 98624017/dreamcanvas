# DreamCanvas 回滚预案

> 维护人：运维负责人；更新时间：每次发布前与发布后 24 小时内复核一次。

## 1. 基本信息
- 当前版本标签：vP0.0.4
- 目标回滚版本标签：vP0.0.3
- 发布负责人：DreamCanvas 发布值班（待指定值班人）
- 回滚审批人：产品负责人（或指定代理人）
- 预计回滚窗口：发布后 2 小时内完成，必要时延长需再次审批

## 2. 回滚触发条件
- 核心业务中断或 SLA 未达标（请描述监控或报警 ID）。
- 数据损坏或备份恢复失败。
- 安全风险：凭据泄露、权限异常等。
- 其他：

## 3. 回滚准备
1. 通知相关干系人（团队群、工单系统）。
2. 锁定代码：冻结 `main` 与 `release/Px`，只允许紧急修复。
3. 获取备份：确认 `%APPDATA%/DreamCanvas/backups/` 中最新备份可用，并复制到安全位置。
4. 记录现场：执行 `scripts/collect-logs.ps1 -IncludeSelfTest` 导出日志（Rust、Python、前端），并归档诊断包。

## 4. 回滚操作步骤
1. **代码回退**
   - `git checkout main`
   - `git revert --no-commit <当前发布 commit>` 或 `git checkout <目标标签>`
   - `git push origin main`
2. **依赖与配置**
   - 运行 `scripts/setup.ps1 -Mode Restore -Tag <目标标签>`（如需执行，补充具体命令）。
   - 校验 `config/secrets.enc` 是否需要回滚或重新生成。
3. **数据恢复**
   - 停止应用 → 复制备份包到 `%APPDATA%/DreamCanvas/projects/`
   - 使用 `scripts/restore-backup.ps1 -Snapshot <文件名>` 执行恢复。
4. **服务验证**
   - 执行 `pnpm tauri dev` 或生产启动脚本，完成健康检查。
   - 运行 `scripts/self-test.ps1`（必要时追加 `-IncludeE2E`）复核 lint/test/pytest/markdownlint。
   - Playwright、Pytest 单独执行用于对比回滚前后结果并记录。
5. **公告与记录**
   - 更新 `docs/changelog.md`，新增回滚说明。
   - 发送回滚完成通知，附带原因与后续行动项。

## 5. 回滚后补救行动
- 根因分析负责人：
- 临时补丁或配置调整：
- 防复发措施与时间表：

## 6. 附件
- 日志与诊断包存储路径：
- 相关工单或 Issue 链接：
