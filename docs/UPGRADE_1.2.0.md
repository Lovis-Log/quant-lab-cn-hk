# 1.2.0-rc.1 本轮检查与验收记录

## 起点与保护

2026-10-13 检查实际工作树干净，HEAD 为 `e1b2ff8`，45 项测试通过。上一轮升级和 Release 记录已经提交；没有归属不明的未提交文件需要归档。创建 `codex/recovery-before-names-deepseek-20261013` 恢复分支，并在 `codex/names-refresh-deepseek` 本地开发。未复制日常用户数据库或密钥进仓库。

用户本轮明确要求不推送远程。本轮本地提交、构建与验证记录会保存，但不创建远程标签、不发布 Release。

## 检查时的刷新行为

- 只有市场页自选股 fragment 每五分钟重跑；历史查询仍按需加载，其他页面不自动更新。
- 历史缓存 15 分钟，快照缓存 5 分钟。手动快照刷新在成功请求后 60 秒内仍会读缓存。
- 失败时自选股显示行可能被清空，缺少完整的成功时间、缓存年龄和最近检查状态。

## 本轮实现

- 证券基础资料按市场＋代码缓存 24 小时，名称失败冷却 5 分钟，价格和回测不依赖名称成功。
- 当前市场页历史查询和自选股默认每五分钟强制检查；可选 10/15 分钟、暂停/恢复。立即更新只绕过对应缓存，同查询并发合并，5 秒连续点击防抖。数据未变或失败明确显示，失败保留旧值及原成功时间。
- SQLite schema v2 对有数据的旧库先备份再事务升级，失败回滚，旧快照 BLOB 和指纹不重写。
- 原生 DeepSeek 侧栏动态读取官方模型与能力，仅发送按钮触发对话，流式输出并保存实际模型标签。上下文按数据指纹/实验隔离，排除完整行情和私人笔记。
- API Key 仅会话或 Windows 凭据管理器；不写研究数据库、日志和导出。无 Key 时离线课程与研究仍可用。
- 集中维护 18 个术语的八项解释结构、手算与当前值模板，并保留八节参数课程。

## 已完成的源码验证

- 全套 pytest：70 passed，未跳过失败测试。
- 包括名称代码匹配与失败、强制刷新、失败保留时间、并发合并、旧库迁移回滚、旧实验复算、模型切换与重绘不调用、密钥脱敏、回撤恢复算术。
- 正常 Windows 用户会话的真实源码 WebView：DOM 加载、密码与模型控件、原生 loaded 事件和子进程停止通过。
- Windows 凭据管理器用随机独立虚拟凭据完成写入/读取/删除，虚拟凭据已移除；没有读取真实 DeepSeek Key。

## 上轮 WebView 超时排查

将哈希与上一 Release 核对一致的 **未修改 1.1.0-rc.1** payload 安装到独立 AppId 和目录后，在正常用户会话连接其实际 WebView：旧版 DOM、loaded 事件和退出都通过。因此不能把之前隐藏／受限会话探针超时当作旧版 GUI 普遍故障。本轮保留更完整的 WebView2 诊断日志，并用实际 DOM 与原生事件共同验收，关闭窗口时不再把 CDP 目标关闭当作加载失败。证据支持探针运行环境差异，未声称单独锁定隐藏窗口或受限令牌中的某一个因素。

## 打包与隔离安装验收

执行中，完成后补入 EXE/安装包哈希、构建提交、原版打包窗口、模拟 API 流式 UI、旧版到新版安装升级、重启保留和卸载结果。真实 DeepSeek 账户调用未执行，用户只需在软件内填写 Key、测试模型列表并发送一条短问题；不用将 Key 发到聊天。

## 官方依据与环境

实际环境：Streamlit 1.65.0、AKShare 1.19.1、pandas 2.3.3、OpenAI SDK 2.54.0（兼容旧研究模块）、requests 2.34.2、pywebview 6.2.1、PyInstaller 6.22.3。没有改动其他 AI 工具配置或引入额外桌面前端。

- [AKShare 证券基础资料](https://akshare.akfamily.xyz/data/stock/stock.html)
- [DeepSeek 模型列表](https://api-docs.deepseek.com/api/list-models/)、[流式 Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)、[错误码](https://api-docs.deepseek.com/quick_start/error_codes/)
- [Streamlit fragment 与运行会话](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
- [Windows Credential Manager](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew)
- [实际 WebView2 的 Playwright 验证](https://playwright.dev/docs/webview2)
