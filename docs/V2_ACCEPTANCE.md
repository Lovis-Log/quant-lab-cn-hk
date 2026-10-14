# V2 Learning Center 验收报告

## 审查与完成范围

项目审查、模块设计、schema 和验收标准见 [V2_PLAN.md](V2_PLAN.md)，知识原理和实践建议见 [V2_LEARNING_REPORT.md](V2_LEARNING_REPORT.md)。原四项名称、搜索、DeepSeek 替换和统计说明均复用 1.2.1 实现。

P1 实现：新手导航、首次欢迎与重启、九页教程、统一帮助与返回、八项证据任务、四条路径、八节七层课程与本地测验、SQLite 进度/目标/实验/笔记/继续学习位置、新手专业模式、共用 DeepSeek 教学上下文。先进算法、完整路径课程、因子框架、优化器、实时数据与历史股票池未在本版实现。

## 文件与迁移

新增 `guidance.py`、`learning_store.py`、`ui_guidance.py`，扩展导航、研究控件 key、知识/Academy 入口和实际分析摘要；现有纯金融计算未改变。新增指南、学习存储与 UI 自动化测试；更新桌面验收脚本。

数据库从 v2 到 v3 先一致性备份，在事务中创建进度和测验表；失败回滚，旧研究快照 BLOB、名称、笔记与指纹不重写。无版本号的旧库也可迁移。进度重置保留研究、行情、学习笔记、设置和密钥。测试全部使用独立用户目录，不迁移日常用户数据库。

## 当前验证状态

**全部完成。104 项 pytest 无失败、无跳过**；构建脚本再次通过同一套测试。源码实际 WebView 与安装副本的候选、课程、测验、目标、笔记、教学草稿、帮助返回、重启恢复和专业模式控件均通过。另通过离线浏览器课程/自选/笔记、隔离模拟 DeepSeek 假设/受控实验/审阅、v2→v3 备份迁移、旧两份快照字节一致和原指纹复算、隔离卸载保留数据。

构建源码为 `7c003180ae31acb9ad01a217b717a52a1b801a04`，干净提交，版本 `2.0.0-rc.1`。北京时间 2026-10-14 23:57:27 至 2026-10-15 00:00:42 构建完成。标签指向该提交；后续仅回填文档与完善验收脚本同步/定位，不改发行应用代码。

| 产物 | 字节 | SHA-256 |
| --- | ---: | --- |
| `dist/packages/2.0.0-rc.1/QuantLab/QuantLab.exe` | 32,351,916 | `b05f0305d3831b120208ba094a23d53ae6e9aa4c8b207bb5916c59b9117b6d5e` |
| `dist/installer/QuantLab-CN-HK-2.0.0-rc.1-Setup.exe` | 100,942,978 | `b6749346372be3498c889ee8e815945a73a5c62faf5e1bc9e34b98ecdfaf0647` |

真实安装测试 AppId `B28FCBE9-A207-4564-B670-9AFD0448DDD3`，独立 `.tools/learning-delivery-3eeab7b1b7f24f0d908461ba5cf58311/UserData`。测试安装已卸载，数据库保留；日常研究数据库与凭据未改动。真实 DeepSeek 付费 API 未调用，模拟只临时注入隔离安装入口并恢复原字节；发行目录不含模拟脚本。回测价格数据本轮没有作完整联网复测，保持预发布版本。

源码窗口记录：`.tools/v2-source-webview-3/`；完整构建、首次失败、修正后的浏览器/桌面脚本和 JSON 留在 `dist/release/2.0.0-rc.1/`，安装日志与各阶段结果另存其 `desktop/`。第一轮传统目录构建因正在运行的 1.2.1 占用 DLL 失败，之后修正为版本独立目录；没有关闭用户旧窗口。首次单选/滑块定位、隐藏 JSON 重复文本和页面重绘时序尝试没有计为通过；按实际可见控件、原生搜索以及 Streamlit `notRunning` 状态复测完整流程通过。

实际命令：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1 -BuildInstaller`；`python tools/verify_packaged.py --offline` 的可见结果定位修正后复测；`python tools/verify_learning_delivery.py` 首轮后使用同安装副本与保留的 `complete_learning_delivery.py` 继续原始/模拟/重启/卸载校验。发行时的测试同步修正已归并回验收工具，以供后续重复执行。

已发布 [v2.0.0-rc.1 预发布版](https://github.com/Lovis-Log/quant-lab-cn-hk/releases/tag/v2.0.0-rc.1)。先建立草稿，上传版本化安装包、SHA256SUMS、构建 JSON 和验证 JSON，四个远程附件大小及 SHA-256 在发布前后均核对。构建与校验、发布回执见 [build](releases/v2.0.0-rc.1-build.json)、[validation](releases/v2.0.0-rc.1-validation.json)、[receipt](releases/v2.0.0-rc.1-receipt.json)、[SHA256SUMS](releases/v2.0.0-rc.1-SHA256SUMS.txt)。

## Windows 使用

安装本版后从桌面入口启动，首次欢迎可开始或跳过。左侧新手使用指引提供五个分区；对应页面帮助可直接定位教程，再返回研究。课程调参后保存实验、提交测验，进度页保存目标/笔记并可重启欢迎或明确重置。DeepSeek 不需要第二个 Key，教学按钮只填草稿；真实付费连接在软件中显式测试和发送。

## 兼容性与后续

保留已有历史、刷新、候选、统计、回测、AI 和桌面入口；专业模式不改变数值。查看帮助后原研究在同一会话可继续；跨重启研究需从已保存档案复算，而不是保留内存数据。免费数据/身份目录时效仍未知，无法验证当前上市状态或所有公司行动。真实付费 API 未由自动验收调用。

P2 优先质量报告、源码/输入契约版本、同口径实验比较和带历史生效时间的执行假设；P3 再评估多因子、优化、滚动机器学习、只读 AI 工具、授权行情和报告。详见独立计划，不把这些路线图写成已完成。
