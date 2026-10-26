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

2026-10-13 完成构建与 Windows 验收，2026-10-14 核对原记录、产物大小与哈希并完成本地归档。构建来自干净提交 `7d4cd07cb2b522bb1e77b3c9470d9c620781ac48`，北京时间 21:33:33 至 21:37:30。随后暂停检查点 `e4a8f20` 只修正测试工具和续接文档，未改变发行运行时代码。

- EXE：`dist/QuantLab/QuantLab.exe`，37,406,762 字节，SHA-256 `5e988fb3ec49005c3b29a87632494637314e9a34f3e1ae0c664be0b7903750c9`。
- 安装包：`dist/installer/QuantLab-CN-HK-1.2.0-rc.1-Setup.exe`，108,097,984 字节，SHA-256 `9e26fd20c13f0c30bb0887577c5b9e5a04aa1e713aa6f332aff2c0dffae2524b`。通用文件名 `QuantLab-CN-HK-Setup.exe` 同时保留。
- 打包脚本重新运行完整 pytest：70 passed，零失败、零跳过；PyInstaller 与 Inno Setup 编译成功。
- **未修改的打包 EXE** 在真实 WebView2 中完成 DOM 加载、密码和模型控件、原生 loaded 事件、窗口关闭和子进程退出检查。
- 独立 AppId 的隔离安装使用上一版真实 payload 和新版相同发行 payload，完成旧版安装、新版覆盖升级、旧库首次迁移与备份、原快照字节哈希核对和实验复算。日常安装与真实用户数据库未操作。
- 模拟 DeepSeek 传输只临时注入隔离安装副本，实际窗口中的模型 B 选择、流式文本、实际模型标签、回答入笔记和清除密钥均通过；测试入口按原字节恢复，发行入口没有模拟注入。
- 在未注入的安装窗口重启后，模型偏好、暂停刷新设置与笔记保留，Key 不自动回到会话。虚拟 Key 未出现在隔离数据库和日志。隔离卸载后用户数据库仍保留，测试安装已经移除。
- 打包离线浏览器检查通过服务、夏普课程切换、自选股持久化、研究笔记与退出。它不代表本轮真实行情端到端验证。

本轮未做真实付费 DeepSeek 请求。最小人工检查是在软件内填 Key、测试连接与官方模型列表、选择模型并发送一条短问题；如有多个可用模型，可切换后再发一条。无须把 Key 发到聊天。候选版已可本地交付，未推送或发布 Release。

归档文件：

- [构建提交、时间、大小与哈希](releases/v1.2.0-rc.1-build.json)
- [脱敏验收摘要与真实／模拟验证范围](releases/v1.2.0-rc.1-validation.json)
- [SHA-256 校验文件](releases/v1.2.0-rc.1-SHA256SUMS.txt)

完整本地日志位于 `dist/release/1.2.0-rc.1/` 与 `.tools/installer-validation-adfb95abc37d42b08fcd11c482b2fb33/`。归档不包含测试数据库、学习笔记内容、Key 或完整日志。

## Git 与恢复

本轮在 `codex/names-refresh-deepseek` 本地提交。起点恢复分支 `codex/recovery-before-names-deepseek-20261013` 保留 `e1b2ff8`；暂停检查点是 `e4a8f20`；2026-10-14 收尾前另建 `codex/recovery-before-delivery-20261014`。工作树干净时可以切换这些分支查看旧代码，不需要破坏性重置。

代码分支不会回退用户数据库。schema v2 的迁移备份位于用户目录 `backups/`；若需要降级，应先关闭软件、另外保留当前库，再使用与旧程序匹配的备份，不把新版本学习笔记直接覆盖掉。本轮没有对日常数据库执行降级或恢复。

## 官方依据与环境

实际环境：Streamlit 1.65.0、AKShare 1.19.1、pandas 2.3.3、OpenAI SDK 2.54.0（兼容旧研究模块）、requests 2.34.2、pywebview 6.2.1、PyInstaller 6.22.3。没有改动其他 AI 工具配置或引入额外桌面前端。

- [AKShare 证券基础资料](https://akshare.akfamily.xyz/data/stock/stock.html)
- [DeepSeek 模型列表](https://api-docs.deepseek.com/api/list-models/)、[流式 Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)、[错误码](https://api-docs.deepseek.com/quick_start/error_codes/)
- [Streamlit fragment 与运行会话](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
- [Windows Credential Manager](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew)
- [实际 WebView2 的 Playwright 验证](https://playwright.dev/docs/webview2)
