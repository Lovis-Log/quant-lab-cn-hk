---
id: automated_testing_git_and_modular_monolith
title: 自动化测试、Git 与模块化单体
english_title: Automated Testing, Git, and Modular Monolith
aliases: [自动化测试, pytest, Git, 版本控制, 模块化单体, modular monolith, 架构]
category: programming_engineering
software_status: implemented
related_modules: [测试, 代码库, 架构, 发行流程]
prerequisites: [python_modules_and_packages, python_exceptions]
related_articles: [python_modules_and_packages, schema_migration, provider_api_cache_and_concurrency, reproducibility_and_audit]
source_ids: [P001, P002, S019, S020]
last_verified: 2026-10-23
---

# 自动化测试、Git 与模块化单体（Automated Testing, Git, and Modular Monolith）

## 快速理解

### 一句话解释

本文是一个复合词条，包含三个彼此独立的概念：自动化测试用 pytest 验证代码行为；Git 记录源码版本和恢复点；模块化单体用一个代码库、按职责拆分模块来组织应用。

### 它解决什么问题

测试防止修改破坏已有计算；Git 让源码可以回溯和协作；模块化让市场数据、策略、回测、存储、AI 和 UI 各自有边界。三者共同支持可维护的研究软件，但不能互相替代。

### 最常见的误解

- **“测试通过就说明软件全部验收通过”**：测试不等于真实 WebView、外部接口、交易所规则或安装包验收。
- **“Git 是软件里的一个功能按钮”**：Git 是开发工具，不是 Quant Lab 的用户界面功能。
- **“提交到 Git 就等于备份研究数据”**：Git 保存源码，不保存用户 SQLite、附件、缓存、日志或密钥。
- **“模块化单体就是微服务”**：当前是一个应用、一个代码库，内部按职责划分模块；它不是独立部署的服务，也不要求运行时只有一个操作系统进程。
- **“模块化意味着模块之间没有依赖”**：模块之间仍有依赖，重点是依赖方向和职责边界。
- **“FastAPI 已经实现”**：FastAPI 只是未来计划的薄接口层，当前没有实现。
- **“测试数量是永久能力指标”**：测试数量会随代码和测试用例变化；应以当次 pytest 输出为准，不把某个固定数字当作永久能力指标。

## 软件实践

### 第一部分：自动化测试（Automated Testing）

#### 在 Quant Lab 哪里出现

- `tests/` 使用 pytest 组织测试，覆盖金融小样本、数据校验、缓存并发、迁移回滚、存储复算、AI 边界和发行辅助逻辑。
- 金融手算测试验证收益率、波动率、回撤、夏普和费用等小样本。
- 数据测试验证字段缺失、NaN、无穷值、重复日期和非正价格会报错。
- 缓存测试验证 TTL、single-flight、失败保留和强制刷新。
- 迁移测试验证版本检查、备份、事务提交和失败回滚。
- 存储测试验证 CSV 快照、SHA-256 和复算指纹。
- UI 启动测试验证页面在无额外网络请求时可以启动；这不等于真实 WebView 验收。

#### 输入、输出和单位

- 输入是测试函数、固定样本、临时数据库路径和模拟对象。
- 输出是 pytest 的通过/失败/跳过状态和断言消息。
- 测试数量是整数，会随代码和测试用例变化；具体数量应以当次 pytest 收集和运行输出为准。
- 测试使用独立临时目录，避免写入用户真实资料库。
- 测试中的数值仍使用项目单位：价格、收益率、基点和金额。

#### 结果应该怎么读

- 全部通过表示当前测试断言满足；不表示所有外部环境都可用。
- 失败表示至少一个断言或异常不符合预期；不能通过跳过来宣称完成。
- 警告不等同失败，但需要判断是否影响结果。
- 测试通过后仍要检查改动范围、真实 GUI 和发行包。
- 测试覆盖率数字不是本文结论；当前没有把覆盖率当作验收标准。

#### 当前软件边界

- 测试不能替代真实 WebView DOM/控件验收。
- 测试不能证明外部行情接口、DeepSeek API 或交易所规则在当前网络和当前日期仍然有效。
- 测试不能证明安装包在目标电脑上可安装、可启动或可卸载。
- 测试中的模拟对象只在测试环境使用，不打入发行安装包。
- 当前没有持续集成服务、自动发布流水线或跨平台测试矩阵的完整证明。

### 第二部分：Git（Version Control）

#### 在 Quant Lab 哪里出现

- Git 用于源码版本、分支、提交和远程同步；具体分支、提交和远程状态以当次 `git status`、`git log` 和远程查询为准。
- 批次开始前创建恢复分支，指向基线提交，便于需要时回退源码；具体分支名和提交保留在批次记录中。
- 项目约定每次完成改进后提交并推送相关源码、测试和文档。
- 打包、创建版本标签和发布 Release 需要用户在当前任务中明确授权，不属于默认同步动作。
- `.gitignore` 忽略用户数据库、缓存、日志、构建产物和本地环境；这些内容不进入源码提交。

#### 输入、输出和单位

- 输入是工作树中的文件修改、提交消息和远程分支。
- 输出是提交对象、分支引用和远程仓库状态。
- 提交哈希是十六进制字符串；它不是金融指标，也不是研究数据指纹。
- Git 不记录用户数据库中的实验内容；实验复算依赖 SQLite 快照和 `audit_id`。
- 分支名和提交消息是开发元数据，不是软件界面文案。

#### 结果应该怎么读

- `git status` 干净表示工作树与当前提交一致；不表示远程已同步。
- `git log` 显示源码历史；不显示用户研究实验历史。
- 推送成功表示远程分支更新；仍需核对本地与远程提交一致。
- 恢复分支指向某个提交，用于需要时回退源码；它不是用户数据备份。
- 提交哈希可用于定位源码版本，但不能单独复现实验，因为实验还依赖数据、参数和环境。

#### 当前软件边界

- Git 不是 Quant Lab 的应用功能；界面没有提交、分支或仓库管理按钮。
- 当前没有自动把用户研究数据提交到 Git；用户数据库和附件不属于源码。
- Git 不保存密钥；密钥只在会话或 Windows 凭据管理器。
- 不使用强制推送；远程同步前要核对分支，避免覆盖他人更新。
- 打包、标签和 Release 不在默认 Git 同步授权内。

### 第三部分：模块化单体（Modular Monolith）

#### 在 Quant Lab 哪里出现

- 一个 Streamlit 应用、一个 `quant_lab` 包、一个代码库，构成一个应用与部署边界。
- 桌面入口启动桌面父进程和独立 Streamlit 子进程；WebView2 运行时也可能有附加进程。这些进程仍共同构成一个应用，不是可独立部署、通过远程业务 API 协作的微服务。
- 进程数量不是判断模块化单体的标准；职责边界、代码库和部署单元才是。
- Market Data：`market_data.py`、`data.py`、`refresh.py`、`names.py`、`securities.py`、`processing.py`。
- Strategy：`strategy.py`。
- Backtest：`backtest.py`。
- Analytics：`metrics.py`、`statistics.py`、`portfolio.py`、`research.py`。
- Storage：`storage.py`、`migrations.py`、`paths.py`。
- AI：`deepseek.py`、`ai_research.py`、`ai_context.py`、`credentials.py`、`security.py`。
- UI：`ui*.py`、`charts.py`、`app.py`；Desktop：`desktop_launcher.py` 和安装器。
- 核心计算模块不导入 Streamlit；UI 调用同一组服务和模型。

#### 输入、输出和单位

- 模块输入输出由函数和数据类定义；例如 `HistoryBundle` 携带行情表、来源、币种和接收时间。
- 模块边界不改变金融单位；价格、收益率、金额仍按各自口径传递。
- UI 负责展示和控件，不重新实现核心金融公式。
- 存储模块负责 SQLite 和迁移，不负责行情计算。
- 未来 FastAPI 若实现，应复用相同服务和模型，而不是复制一套计算逻辑。

#### 结果应该怎么读

- 看到 `quant_lab.data` 时，知道它负责数据获取和缓存；看到 `quant_lab.ui_*` 时，知道它负责页面。
- 看到核心模块导入 Streamlit，说明边界被破坏；当前核心模块没有这种导入。
- 看到模块之间有依赖是正常的；关键是依赖方向清晰，不形成循环。
- 看到同一公式在 UI 和计算模块各写一遍，说明职责重复；当前项目避免这种重复。
- 看到多个进程不一定说明不是单体：桌面父进程、Streamlit 子进程和 WebView2 附加进程仍可共同构成一个应用；判断标准是是否仍为一个应用/代码库/部署与业务边界，而不是可独立部署、通过远程业务 API 协作的微服务。

#### 当前软件边界

- 当前不是微服务、插件系统、远程计算平台或独立 API 服务。
- 未来 FastAPI 是计划中的薄接口层；当前未实现。
- 模块化单体仍共享数据库和部署边界，可能有共享故障域；它不要求运行时只有一个进程，也不是故障隔离架构。
- 模块边界不等于安全边界；同一应用内的模块通常共享文件系统和数据库权限，进程数量不改变这一点。
- 代码行号和模块列表会随开发变化；复核时以符号名和测试为准。

## 专业原理

### 正式定义

**自动化测试**：用可执行代码检查程序行为是否符合预期。pytest 通过收集 `test_*.py` 中的测试函数、执行断言并报告结果。常见测试类型包括单元测试、集成测试和端到端测试。

**Git**：分布式版本控制系统。提交（commit）是不可变快照，分支（branch）是指向提交的引用，远程（remote）是另一个仓库副本。合并和推送改变引用，不改变历史提交内容。

**模块化单体**：一个应用、一个代码库，以及一个部署与业务边界，内部按业务职责划分为模块。模块通过明确接口协作，通常共享数据库和运行环境；它不要求运行时只有一个操作系统进程或线程，也不是可独立部署、通过远程业务 API 协作的微服务。它与微服务的区别在部署单元和网络边界，而不是代码是否分目录，也不是进程数量。

### 公式与符号

测试断言示例：

`assert simple_price_return(100.0, 110.0) == pytest.approx(0.10)`

Git 提交图（示意）：

```text
A --- B --- C  main
           \
            D --- E  feature
```

模块依赖方向：

`UI → Analytics / Storage / Market Data → 数据模型`

核心计算模块不反向依赖 UI。

### 可手算的小例子

**测试示例**（通用 pytest，不是软件新增功能）：

```python
import pytest

def simple_price_return(first_close, last_close):
    return last_close / first_close - 1

def test_simple_price_return():
    assert simple_price_return(100.0, 110.0) == pytest.approx(0.10)
```

计算：`110/100 - 1 = 0.10`；断言通过。若把期望值写成 `10`，测试会失败，因为 `0.10` 与 `10` 相差 100 倍；这正是百分数和小数的区别。

**Git 示例**（通用命令，不是软件界面）：

```text
git switch -c recovery-before-change
git commit -m "docs: describe change"
git push origin feature-branch
```

这些命令只操作源码仓库；不会备份用户 SQLite、附件或缓存。

**模块化示例**：

```text
quant_lab/
  data.py          # 获取和缓存
  processing.py    # 校验
  strategy.py      # 信号
  backtest.py      # 成交
  research.py      # 实验和指纹
  ui_strategy.py   # 页面展示
```

依赖方向：`ui_strategy → research → backtest → strategy`；`ui_strategy` 不把金融公式复制到页面。

### 前提假设

- 测试使用隔离的临时目录和模拟对象，不依赖真实用户数据。
- 测试断言与当前业务口径一致；口径变化时测试也要更新。
- Git 提交前工作树范围清晰，不混入归属不明的修改。
- 远程同步前核对分支和远程状态，不使用强制推送。
- 模块边界由职责和依赖方向维护，而不是只靠目录名。
- 模块化单体的边界由应用、代码库和部署与业务边界定义，不由进程或线程数量定义。
- 未来接口层复用现有服务，不复制金融计算。

### 边界情况

- 测试全部通过但真实 WebView 控件缺失：仍不能验收通过；必须检查实际 DOM。
- 测试使用模拟 API 通过，但真实 API 字段变化：外部接口仍需单独验证。
- 测试在开发机通过，但目标 Windows 机器缺少 WebView2：安装包验收仍失败。
- Git 提交成功但远程推送失败：本地有提交，远程未同步；应报告原因，不声称同步成功。
- Git 恢复分支存在，但用户数据库已变化：源码回退不能恢复研究数据。
- 模块目录划分清楚，但模块之间循环导入：架构仍有问题。
- 单体应用的一个模块崩溃可能影响同一运行实例中的其他模块：模块化不提供进程隔离或故障隔离；桌面父进程、Streamlit 子进程和 WebView2 进程的划分也不是业务微服务边界。
- 未来 FastAPI 未实现时，不能把 API 文档写成当前功能。

## 相关知识

### 前置概念

- `python_modules_and_packages`：模块和包是模块化单体的代码基础。
- `python_exceptions`：测试需要验证失败路径和异常消息。

### 相关词条

- `schema_migration` Schema 迁移
- `provider_api_cache_and_concurrency` Provider、API、缓存与并发
- `reproducibility_and_audit` 可复现性与审计
- `python_modules_and_packages` Python 模块与包

### 建议下一篇

`reproducibility_and_audit`：把测试、版本和数据指纹放在同一条研究复现链上理解。

## 参考资料

- `P001` README.md：运行测试、桌面入口和项目结构。
- `P002` ARCHITECTURE.md：模块边界、数据流和未来 FastAPI 计划。
- `S019` Git 文档：提交、分支、远程和恢复点；页面未联网复核。
- `S020` pytest 文档：测试收集、断言和测试组织；页面未联网复核。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
