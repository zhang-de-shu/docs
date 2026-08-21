---
name: eas-update-insights
description: "EAS 服务（付费）。检查已发布 EAS Update 的健康状况：崩溃率、安装/启动次数、独立用户数、payload 大小，以及每个渠道中 embedded 用户与 OTA 用户的占比。当用户询问某个更新表现如何、某次推送是否健康、有多少用户在使用 embedded 构建 vs OTA，或想在 CI 中以更新健康状况作为门禁时使用。"
version: 1.0.0
license: MIT
allowed-tools: "Bash(eas *)"
---

# EAS Update Insights

> **EAS 服务——会产生费用。** Insights 覆盖通过 EAS Update 发布的更新，这是一项有免费额度限制的付费 Expo Application Services 产品。更新分发以及这些命令背后的数据都会计入你所购方案的 EAS Update 用量。请查看 https://expo.dev/pricing。

直接从 CLI 查询已发布 EAS Update 的健康状况：启动次数、启动失败次数、崩溃率、独立用户数、payload 大小、每个渠道中 embedded 与 OTA 用户的占比，以及每个 runtime version 下最热门的更新。这些数据与驱动 expo.dev 上更新和渠道详情页的数据相同；这些命令以人类可读和 JSON 两种形式在终端中暴露它们。

## 何时使用本 skill

当用户想评估已发布 EAS Update 的健康状况或采用情况时使用：崩溃率、安装次数、独立用户数、bundle 大小，以及某渠道中 embedded 用户与 OTA 用户的占比。

示例提示语：

- "How is the latest update doing?"
- "Is the latest update healthy?"
- "Is the new release crashing more than the last one?"
- "How many users are on the latest update vs the embedded build?"
- "Which update is most popular on production right now?"
- "How big is our update bundle?"

也适用于：发布后的推送监控和回归检测。

当用户需要按用户的崩溃详情或设备级报告时不要使用；本 skill 只暴露聚合的 EAS 指标。

## 前提条件

- 已安装 `eas-cli`（`npm install -g eas-cli`）。
- 已登录：`eas login`。
- 对于 `channel:insights`：在 Expo 项目目录中运行（该命令从 `app.json` 解析项目 ID）。`update:insights` 只需要登录。

## 命令一览

| 命令 | 用途 |
|---|---|
| `eas update:list` | 发现最近的 update group、它们的 `group` ID 和分支名 |
| `eas update:insights <groupId>` | 按平台的启动次数、启动失败次数、崩溃率、独立用户数、payload 大小、按日明细 |
| `eas update:view <groupId> --insights` | update group 详情 + 附加同样的指标 |
| `eas channel:insights --channel <name> --runtime-version <version>` | 某渠道 + runtime 的 embedded/OTA 用户数、最热门更新、累计指标 |

以上命令都支持 `--json --non-interactive` 以便程序化解析。

## 查找 ID

在查询某个 update group 的 insights 之前，你需要它的 `group` ID。使用 `eas update:list`，配合 `--branch <name>`（该分支上的更新）或 `--all`（所有分支上的更新）。非交互式运行时始终传 `--json --non-interactive`；不带 branch/`--all` flag 时，该命令会提示选择分支：

```bash
# Latest group id across all branches
eas update:list --all --json --non-interactive | jq -r '.currentPage[0].group'

# Latest group id on a specific branch
eas update:list --branch production --json --non-interactive | jq -r '.currentPage[0].group'
```

JSON 响应有一个 `currentPage` 数组，每个 update group 一个条目（同一次发布的两个平台会合并为一个条目）：

```json
{
  "currentPage": [
    {
      "branch": "production",
      "message": "\"Fix checkout crash\" (1 week ago by someone)",
      "runtimeVersion": "1.0.6",
      "group": "03d5dfcf-736c-475a-8730-af039c3f4d06",
      "platforms": "android, ios",
      "isRollBackToEmbedded": false
    }
  ]
}
```

条目还带有 `codeSigningKey` 和 `rolloutPercentage`，但仅当该 group 使用了这些功能时才有（undefined 值会从 JSON 输出中省略）。

当使用 `--branch <name>` 调用时，响应顶层还会包含 `name`（分支名）和 `id`（分支 ID）。

## `eas update:insights <groupId>`

显示单个 update group 的启动次数、启动失败次数、崩溃率、独立用户数、启动资源数量和平均 payload 大小，**按平台**（iOS、Android）细分，外加启动与失败次数的按日明细。

### 基本用法

```bash
eas update:insights 03d5dfcf-736c-475a-8730-af039c3f4d06
```

### Flags

| Flag | 说明 |
|---|---|
| `--days <N>` | 回溯 N 天。默认：**7**。与 `--start`/`--end` 互斥。 |
| `--start <iso-date>` / `--end <iso-date>` | 显式时间范围，例如 `--start 2026-04-01 --end 2026-04-15`。 |
| `--platform <ios\|android>` | 筛选到单个平台。省略则显示该 group 的所有平台。 |
| `--json` | 机器可读输出。隐含 `--non-interactive`。 |
| `--non-interactive` | 脚本化运行时必需。 |

### JSON 输出结构

顶层：`groupId`、`timespan`（`start`、`end`、`daysBack`），以及 `platforms[]`，该 group 发布到的每个平台一个条目。每个平台条目有 `updateId`、`totals`（`uniqueUsers`、`installs`、`failedInstalls`、`crashRatePercent`）、`payload`（`launchAssetCount`、`averageUpdatePayloadBytes`），以及 `{ date, installs, failedInstalls }` 的 `daily[]` 时间序列。

完整 schema 和字段参考见 [references/update-insights-schema.md](./references/update-insights-schema.md)。

与健康评估相关的字段：

- `platforms[].totals.crashRatePercent`，计算方式为 `failedInstalls / (installs + failedInstalls) * 100`。没有安装时为零。
- `platforms[].totals.installs` 和 `uniqueUsers` 给出采用情况信号。
- `platforms[].daily` 是时间序列，有助于发现失败次数的突然飙升。

### 错误

- `Could not find any updates with group ID: "<id>"` —— group 不存在或你没有访问权限。
- `Update group "<id>" has no ios update (available platforms: android)` —— 使用了 `--platform ios`，但该 group 没有为 iOS 发布。
- `EAS Update insights is not supported by this version of eas-cli. Please upgrade ...` —— 服务端废弃了 CLI 依赖的字段。运行 `npm install -g eas-cli@latest`。

## `eas update:view <groupId> --insights`

在标准 `update:view` 输出的基础上内联扩展同样的按平台 insights。

```bash
# Human-readable
eas update:view 03d5dfcf-... --insights
eas update:view 03d5dfcf-... --insights --days 30

# JSON: wrapped as { updates: [...], insights: {...} }
eas update:view 03d5dfcf-... --json --insights
```

不带 `--insights` 时，`update:view` 的行为与以前完全一致——现有使用方的 JSON 结构不变。`--days` / `--start` / `--end` flag 仅在设置了 `--insights` 时生效；单独传它们会报错。

## `eas channel:insights --channel <name> --runtime-version <version>`

按渠道显示有多少用户在使用 embedded 构建 vs 空中更新（over-the-air），以及哪些更新承载了最多流量。必须在 Expo 项目目录中运行。

### 基本用法

```bash
eas channel:insights --channel production --runtime-version 1.0.6
```

### Flags

| Flag | 说明 |
|---|---|
| `--channel <name>` | **必填。** 渠道名（例如 `production`、`staging`）。 |
| `--runtime-version <version>` | **必填。** 必须与已发布的完全一致。在 `update:list` 中检查 `runtimeVersion` 值。 |
| `--days <N>` | 回溯 N 天。默认：**7**。 |
| `--start` / `--end` | 显式时间范围，与 `update:insights` 相同。 |
| `--json` / `--non-interactive` | 机器可读输出。 |

### JSON 输出结构

顶层：`channel`、`runtimeVersion`、`timespan`、`embeddedUpdateTotalUniqueUsers`、`otaTotalUniqueUsers`、`mostPopularUpdates[]`（每项含 `rank`、`groupId`、`message`、`platform`、`totalUniqueUsers`）、`cumulativeMetricsAtLastTimestamp[]`，外加带 `labels` 和 `datasets` 的图表形 `uniqueUsersOverTime` 和 `cumulativeMetricsOverTime` 对象。

完整 schema 和字段参考见 [references/channel-insights-schema.md](./references/channel-insights-schema.md)。

重要字段：

- `embeddedUpdateTotalUniqueUsers` 是运行 embedded（随二进制打包）构建的用户数。
- `mostPopularUpdates[]` 是按 `totalUniqueUsers` 排名的更新。**注意**：这是服务端返回的 top-N；`otaTotalUniqueUsers` 是该列表的总和，如果活跃的更新超过 top-N 个，可能会低估 OTA 总触达。
- `uniqueUsersOverTime` 和 `cumulativeMetricsOverTime` 是用于绘图的按日数据序列。

### 错误

- `Could not find channel with the name <name>` —— 拼写错误或账号不对。
- 表格中出现 "No update launches recorded" / JSON 中 `mostPopularUpdates` 为空 —— 该渠道 + runtime 还没有启动过任何 OTA 更新。通常意味着该渠道仍在只提供 embedded 构建。

## 常见工作流

### 验证我刚发布的更新是否健康

```bash
# 1. Grab the latest publish on production
GROUP_ID=$(eas update:list --branch production --json --non-interactive \
  | jq -r '.currentPage[0].group')

# 2. Give it some adoption time (minutes to hours), then check crash rate
eas update:insights "$GROUP_ID" --json --non-interactive \
  | jq '.platforms[] | {platform, installs: .totals.installs, crashRate: .totals.crashRatePercent}'
```

跨平台比较 `crashRate`，并与之前的版本比较；突然飙升或不对称表现（iOS 飙升而 Android 平稳，或反之）就是需要调查的信号。

### 比较两个渠道的采用情况

```bash
for channel in production staging; do
  echo "--- $channel ---"
  eas channel:insights --channel "$channel" --runtime-version 1.0.6 --json --non-interactive \
    | jq '{
        channel,
        embedded: .embeddedUpdateTotalUniqueUsers,
        ota: .otaTotalUniqueUsers,
        topUpdate: .mostPopularUpdates[0]
      }'
done
```

### 检测最近 24 小时的推送回归

```bash
eas update:insights "$GROUP_ID" --days 1 --json --non-interactive \
  | jq '.platforms[] | select(.totals.crashRatePercent > 1)'
```

### 为发布说明汇总 group 指标

```bash
eas update:view "$GROUP_ID" --insights --days 30
```

人类可读的 group 详情外加每个平台 30 天的启动/失败数据——适合粘贴到 changelog 或事故复盘中。

## 输出技巧

- 把 JSON 用管道传给 `jq`；payload 结构化良好，便于过滤。
- `--json` 隐含 `--non-interactive`，但两者同时传更明确、更适合脚本化。
- `daily[].date` 中的日期是 UTC ISO 时间戳；人类可读表格将它们渲染为 `YYYY-MM-DD`（UTC）。
- CLI 表格标签显示 "Launches" / "Crashes"，而 JSON 使用 `installs` / `failedInstalls`。是同一个字段，显示名不同。

## 局限性

- **跨平台的独立用户数** 可能会重复计算在 iOS 和 Android 上运行同一次发布的用户。同样的注意事项也适用于 channel insights 中的 `otaTotalUniqueUsers`，它是对 `mostPopularUpdates` 的求和。
- **刚发布的更新** 可能会短暂显示为零，直到指标管道追赶上来。
- **安装是下载，不是启动**：`installs` / "Launches" 字段统计的是下载了 manifest 和启动资源的用户。一次确认的运行只在用户*下一次*更新检查时才被记录（通常在 24 小时内，取决于应用的更新策略）。所以指标会略微滞后于真实世界的状态。
- **崩溃是自报的**：`failedInstalls` / "Crashes" 统计的是在安装/启动期间出错、并在下一次更新检查时被上报的更新。没有触发更新请求的崩溃（例如恢复之前的进程被杀）不会出现。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "eas-update-insights" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
