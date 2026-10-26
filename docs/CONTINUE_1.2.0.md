# 1.2.0-rc.1 续接记录（用户要求暂停）

**2026-10-14 已按用户“继续”完成本轮收尾。** 以下为暂停时的历史记录，保留作恢复依据。验收文档已经回填，构建和脱敏验证 JSON 已归档；完整交付与剩余真实 Key 检查见 [本轮验收记录](UPGRADE_1.2.0.md)。本轮仍未推送远程或发布 Release。

2026-10-13 用户因额度不足要求先记录进度、暂停，等待之后明确继续。本记录不代表本轮已完成最终交付。

## Git 与权限

- 项目：`D:\Projects\quant-lab`。
- 当前本地开发分支：`codex/names-refresh-deepseek`。
- 起点：`e1b2ff8`，当时工作树干净，基线 45 passed；没有归属不明的原有未提交文件。
- 恢复分支：`codex/recovery-before-names-deepseek-20261013`，指向起点。
- 功能与文档提交：`7d4cd07cb2b522bb1e77b3c9470d9c620781ac48`。
- 暂停前另外修正了 `tools/verify_desktop_gui.py`、`tools/verify_installation.py` 的实际验收流程；会连同本记录保存为本地暂停检查点提交。
- **用户本轮明确禁止远程推送。没有 push、远程标签或新 Release。** 先前的默认自动同步规范不能覆盖这一指令。
- 不执行 reset --hard、git clean 或覆盖真实用户数据。以后继续先核对 Git 状态，保留新增的未知修改。

## 已实现并验证的功能

1. `names.py`：东方财富证券基础资料，市场＋规范代码识别，24 小时名称缓存、失败 5 分钟冷却，失败显示名称暂不可用。名称用于查询、自选股、图表、回测、实验与导出；新实验保存当时名称，旧实验可打开。
2. `refresh.py` / `data.py` / 更新 UI：默认 5 分钟，可选 10/15 分钟，暂停/恢复，立即更新绕过对应缓存；同查询并发合并、连续点击 5 秒防抖，快照请求至少间隔 1 秒。缓存读取不修改成功时间，失败保留数据与原时间，未变化明确显示。北京时间 UTC+08:00；只有市场页运行会话自动检查。
3. `migrations.py` / `storage.py`：schema v2，旧库备份、事务迁移及失败回滚；保存名称、白名单非敏感设置和学习笔记，旧快照 BLOB 和指纹不重写。
4. `deepseek.py` / `ui_deepseek.py` / `ai_context.py`：原生可收起侧栏、官方动态模型及能力、手动 ID 后备、流式输出、实际模型标记、快捷草稿、上下文预览及回答入学习笔记。只有发送触发对话请求；按数据指纹/实验隔离历史，排除私人笔记及完整行情。
5. `credentials.py` / `security.py`：默认会话 Key，可选 Windows 凭据管理器，失败不写明文；错误、输出、笔记和导出脱敏。没有修改 Codex、Claude 或其他工具配置。
6. `knowledge.py` / `ui_knowledge.py`：18 个术语的八项解释结构、手算、当前值模板及追问入口，八节课程代码和实验保留。零波动年化波动率为 0，夏普仍不定义。

## 实际验证结果

- 全套 pytest：**70 passed**，无失败跳过。打包脚本也再次运行并通过同一套测试。
- Windows 凭据管理器：独立随机虚拟凭据写入、读取、删除通过，虚拟凭据已移除，未读取真实 DeepSeek Key。
- 未修改的旧版 1.1.0-rc.1：与上一 Release 的 EXE 哈希一致；隔离安装后真实 WebView DOM、loaded 事件与停止通过。此前隐藏/受限探针超时不能作为旧版 GUI 故障结论。
- 新版未修改打包 EXE：实际 WebView DOM、密码和模型控件、loaded 事件、子进程关闭通过。
- 打包离线浏览器：学院、自选股持久化、研究笔记、服务与退出通过。
- 隔离旧版→新版安装升级→卸载：**通过**。同一随机测试 AppId，日常 AppId 和安装未改动；旧数据库迁移、原快照哈希与复算、笔记/设置重启、Key 不自动回到会话、卸载后用户数据库保留均通过。
- 模拟 API 的真实安装窗口：模型 B 选择、流式输出、实际模型标签、回答入笔记与清除密钥通过。模拟传输仅临时注入 `.tools` 的安装副本，按原字节恢复；发行包不包含注入。
- 虚拟 Key 不在隔离数据库和日志中；未执行真实付费 DeepSeek 调用。

## 构建产物与记录

构建来自干净提交 `7d4cd07`，2026-10-13 21:33:33 至 21:37:30（北京时间）：

- EXE：`D:\Projects\quant-lab\dist\QuantLab\QuantLab.exe`，37,406,762 字节。
  SHA-256：`5e988fb3ec49005c3b29a87632494637314e9a34f3e1ae0c664be0b7903750c9`。
- 安装包：`D:\Projects\quant-lab\dist\installer\QuantLab-CN-HK-1.2.0-rc.1-Setup.exe`，108,097,984 字节。另保留通用文件名 `QuantLab-CN-HK-Setup.exe`。
  SHA-256：`9e26fd20c13f0c30bb0887577c5b9e5a04aa1e713aa6f332aff2c0dffae2524b`。
- 构建日志、manifest、浏览器检查：`dist/release/1.2.0-rc.1/`。
- 隔离安装和 GUI 的完整记录：`.tools/installer-validation-adfb95abc37d42b08fcd11c482b2fb33/`。
  关键文件：`installation-result.json`、`old-gui-result.json`、`gui-original.log`、`gui-mock.log`、`gui-restart.log`、安装/卸载日志；测试用户数据在 `UserData/`，卸载后保留。
- 新版未修改 EXE 的窗口记录：`.tools/desktop-validation-5fce32e9ffa441ebbe39ae9be8ceba61/gui-result.json`。

## 后续继续的起点（避免重做）

核心实现、构建和隔离 Windows 验收已完成。主要待收尾：

1. 把 `docs/UPGRADE_1.2.0.md` 最后一节的“执行中”替换为上述实际验收结果；将精简、无私人数据的构建/验证 JSON 汇总归档到 `docs`。README/ARCHITECTURE/LEARNING/CHANGELOG/AGENTS 已更新功能说明。
2. 核对暂停检查点中两个测试工具修正及文档，作最终本地提交和状态检查。运行时模块在打包后没有再变动；工具不打入 EXE，因此不需要无理由重新打包。
3. 按用户要求给完整中文交付报告：功能、模块、刷新位置、DeepSeek 操作、测试与 GUI 实际范围、产物路径、Git/恢复方式及剩余真实连接验证。继续不得推送或发布。
4. 没有真实 Key 时其他工作已完成；用户只需在软件内填写 Key、测试连接/模型列表、发送一个短问题验证真实流式。若有多个可用模型可再切换发送。不要要求用户把 Key 发到聊天。

验收工具修正是：每次窗口使用新探针文件以免读取旧 CDP 端口；等待实际输入提交/清除后的 UI 回传；原生模型搜索选择并核对返回模型；注入入口字节恢复；恢复验收时保留已保存笔记并验证增量与重启。最后一次完整隔离验收成功，测试安装已经卸载，日常数据未动。
