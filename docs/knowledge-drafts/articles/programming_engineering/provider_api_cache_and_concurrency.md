---
id: provider_api_cache_and_concurrency
title: Provider、API、缓存与并发
english_title: Provider, API, Cache, and Concurrency
aliases: [Provider, 数据提供者, API, 缓存, 并发, single-flight, TTL, 限频]
category: programming_engineering
software_status: implemented
related_modules: [市场数据, 名称服务, 证券目录, 刷新]
prerequisites: [python_modules_and_packages, python_exceptions]
related_articles: [cache_and_freshness, data_provenance, instrument_identity, python_modules_and_packages]
source_ids: [P002, P004, S001]
last_verified: 2026-10-23
---

# Provider、API、缓存与并发（Provider, API, Cache, and Concurrency）

## 快速理解

### 一句话解释

Provider 是行情数据的适配器，API 是它访问的上游接口，缓存保存已验证的短期结果，并发合并让同一查询只发一次请求；Quant Lab 当前默认使用 AKShare Provider，缓存和锁都在当前进程内。

### 它解决什么问题

免费行情接口可能慢、限频或暂时失败。每次页面重绘都请求上游既浪费又容易触发限制。缓存按查询键保存结果，TTL 控制新鲜度；同一查询的并发调用合并为一次上游请求，失败时保留上次有效数据。

### 最常见的误解

- **“Provider 会自动鉴权、限频和重试”**：`MarketDataProvider` 只是接口契约；鉴权、授权、限频和时间戳要由具体实现负责。
- **“快照是实时行情”**：当前快照取最近历史日线收盘，不是盘中实时报价。
- **“缓存命中会刷新成功时间”**：读取缓存不更新上游成功获取时间；只有真正成功取得响应才更新。
- **“失败会返回演示数据”**：失败保留旧值并标记可能过期；没有旧值时明确失败，不伪造成功。
- **“single-flight 会合并所有并发请求”**：只合并相同缓存键的请求；不同查询各走各的。
- **“等待者会无限等待”**：等待有超时边界；超时返回旧值或继续失败流程，不是永不超时。
- **“缓存是跨进程共享的”**：当前是进程内缓存和锁，不是分布式缓存或数据库锁。

## 软件实践

### 在 Quant Lab 哪里出现

- `market_data.MarketDataProvider`：`Protocol`，定义 `name`、`history(market, symbol, start, end, adjustment)` 和 `snapshot(market, symbol)`。
- `data.AKShareProvider`：当前默认实现。A 股使用 `stock_zh_a_hist_tx`；港股主链路使用 `stock_hk_hist`，失败后回退 `stock_hk_daily`，来源字符串明确标注回退。
- `data.HistoryCache`：历史查询 TTL 900 秒（15 分钟），最多 64 条；键包含市场、规范代码、开始日期、结束日期和复权方式。
- `data.SnapshotCache`：快照 TTL 300 秒（5 分钟）；不同快照上游请求至少间隔 1 秒。
- `refresh.RefreshCache`：单飞（single-flight）、TTL、失败保留旧值和旧成功时间。
- `names.NameCache`：名称成功缓存 24 小时，失败冷却 5 分钟；键还包含数据库路径，并持久化到 SQLite。
- `securities._cache`：证券目录缓存 24 小时，最多 8 条；显式更新后写临时文件再原子替换。

### 输入、输出和单位

- `history` 输入：市场、代码、开始日期、结束日期、复权方式；输出 `HistoryBundle`，包含行情表、来源、币种、复权、接收时间和缓存状态。
- `snapshot` 输入：市场、代码；输出 `MarketSnapshot`，包含最近收盘价、观察日期、接收时间、来源、币种和状态。
- TTL 单位是秒；缓存年龄也是秒。
- 历史缓存键中的日期是 `date`，复权是 `""`、`"qfq"` 或 `"hfq"`。
- 名称缓存键是 `(数据库路径, 市场, 规范代码)`；目录缓存键是 `(用户数据目录, 市场)`。
- 等待超时：历史/快照的 `RefreshCache` 等待 60 秒；名称查询等待 30 秒。

### 结果应该怎么读

- `cached=True` 表示结果来自缓存；`cache_age_seconds` 表示缓存年龄。
- `update_result="取得新数据"` 表示本次成功取得新响应；`"检查成功，数据未变化"` 表示成功请求但数据内容相同。
- `update_result="请求失败"` 且 `update_error` 非空时，数据可能是上次有效值，可能过期。
- `cached=False` 且 `update_result="取得新数据"` 通常表示本次上游响应。
- 名称失败时显示“名称暂不可用”，不应推断退市或不存在。
- 证券目录的“获取于”时间是目录接收时间，不是价格时间。

### 当前软件边界

- 当前默认 Provider 是 AKShare；没有自动 Provider 注册、插件发现或运行时切换界面。
- 快照是最近历史日线收盘参考，不是实时行情；没有盘中报价、交易所时间戳或延迟测量。
- 缓存和锁是进程内实现，不是跨进程、分布式缓存或数据库锁。
- single-flight 只合并相同 key；不同市场、代码、日期区间或复权方式不会合并。
- 等待有超时；超时后返回旧值或旧视图，不会无限阻塞。
- 缓存读取、页面重绘和失败尝试不能当作新的上游成功时间。
- 当前没有统一的重试队列、熔断器、限频令牌桶或跨进程请求协调。
- 新的授权 Provider 需要独立处理鉴权、授权、限频、时间戳、延迟和密钥管理；密钥不写入仓库。

## 专业原理

### 正式定义

- Provider：把上游数据转换为应用内部模型的适配器。
- API：上游提供的接口；可能有鉴权、配额、限频和版本变化。
- 缓存：保存已取得的结果，以便在 TTL 内复用。
- TTL（Time To Live）：缓存条目被视为新鲜的时长。
- Single-flight：相同键的并发请求只允许一个执行，其他请求等待并复用结果。
- 限频：限制单位时间内的请求数量；当前只在快照请求间实现至少 1 秒间隔。

### 公式与符号

缓存新鲜度：

`fresh = (now - last_success_at) < TTL`

缓存键：

`history_key = (market, normalized_symbol, start, end, adjustment)`

`snapshot_key = (market, normalized_symbol)`

`name_key = (database_path, market, normalized_symbol)`

`directory_key = (user_data_dir, market)`

失败保留：

`result = old_value`，若存在；否则 `None`。

### 可手算的小例子

历史缓存时间线：

- t=0 秒：成功请求，保存结果和成功时间；
- t=600 秒：仍在 900 秒 TTL 内，返回缓存，`cached=True`，年龄 600 秒；
- t=901 秒：TTL 过期，尝试上游；
- 若上游失败：返回 t=0 的结果，年龄 901 秒，标记“请求失败”和“数据可能过期”。

通用 Python 示例（不是软件功能）：

```python
import time

key = ("A 股", "600519", "2026-01-01", "2026-10-23", "")
ttl_seconds = 900
cached_at = time.monotonic() - 600
fresh = time.monotonic() - cached_at < ttl_seconds
```

计算：

- 缓存年龄约为 600 秒；
- `600 < 900`，`fresh` 为 `True`；
- 如果把缓存年龄改成 901 秒，`fresh` 为 `False`，才会尝试上游。

这个片段只演示 TTL 判断，不是项目的缓存类；实际实现还包含 single-flight、失败保留和深拷贝。

并发合并示例：

| 时刻 | 调用者 A | 调用者 B | 上游请求数 |
| --- | --- | --- | --- |
| t0 | 请求 key K，成为 owner | 请求 key K，成为 waiter | 1 |
| t1 | 等待响应 | 等待 owner 完成 | 1 |
| t2 | 得到结果 | 读取同一结果 | 1 |

如果 B 请求的是不同 key K2，则 B 会成为 K2 的 owner，上游请求数为 2；single-flight 不合并不同查询。

快照节流示例：

- 上次快照请求在 `t=0.0`；
- 下一次请求在 `t=0.4` 到达，需等待约 0.6 秒；
- `t=1.0` 后才发起上游请求；
- 这 1 秒是进程内快照请求间隔，不是交易所限频规则。

### 前提假设

- 上游响应经过字段校验后才会进入缓存；失败响应不会被当作有效数据。
- 缓存键足以区分不同查询；任一字段不同就是不同条目。
- TTL 是研究假设，不代表上游数据在那段时间内不会变化。
- 同进程内的锁能协调线程；跨进程写入不在当前保证范围内。
- 失败保留的旧值仍可能有用，但必须标明可能过期。
- Provider 的上游授权和限频由实现方负责，不由 Protocol 自动处理。

### 边界情况

- 缓存命中但数据已过期：仍会返回旧值，直到 TTL 到期或手动强制刷新。
- 强制刷新：`force=True` 绕过 TTL，但若同一 key 已有请求在飞，仍会加入等待，不会并发发第二次请求。
- 失败且无旧值：返回明确失败；`HistoryCache` 抛出 `DataUnavailableError`。
- 等待超时：历史/快照等待最多 60 秒，名称等待最多 30 秒；超时返回旧视图或旧名称，不保证新数据。
- 数据未变化：成功请求后比较内容，显示“检查成功，数据未变化”，成功时间仍更新。
- 不同复权方式：缓存键不同，不能复用同一价格序列。
- 代码未规范化：缓存键使用规范代码；直接传原始写法会先规范化。
- 名称失败：保留旧名称；没有旧名称时返回空字符串，界面显示“名称暂不可用”。
- 目录更新失败：保留上次有效目录和原获取时间；内置快照仍可离线使用。
- 多进程：每个进程有自己的缓存和锁；进程之间不共享 single-flight。
- 页面重绘：不应触发新的上游成功时间；只有实际请求成功才更新。

## 相关知识

### 前置概念

- `python_modules_and_packages`：Provider、缓存和 UI 的模块边界。
- `python_exceptions`：失败如何保留旧值并标记错误。

### 相关词条

- `cache_and_freshness` 缓存与新鲜度
- `data_provenance` 数据来源与时间戳
- `instrument_identity` 证券身份与代码规范化
- `data_quality_and_bias` 数据质量与偏差

### 建议下一篇

`automated_testing_git_and_modular_monolith`：了解这些缓存、迁移和 Provider 边界如何被测试和版本管理。

## 参考资料

- `P002` ARCHITECTURE.md：Provider 合同、15 分钟/64 条历史缓存、5 分钟快照、并发合并和失败保留。
- `P004` docs/DATA.md：A 股/港股接口、回退来源、名称缓存和证券目录口径。
- `S001` AKShare 股票数据文档：上游接口和字段背景；官方入口已由 Codex 确认可访问，具体字段仍待逐项核验。
- 外部来源内容未逐条读取；本文状态为 `drafted`，不标 `source_checked`。
