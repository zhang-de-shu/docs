---
name: eas-simulator
description: "EAS 服务（付费）。在托管于 EAS 云端的远程 iOS/Android 模拟器上运行并控制用户的应用。在运行任何 `eas simulator:*` 命令之前先阅读本 skill——它包含该实验性 API 的当前语法。只要用户需要本地无法运行的模拟器就使用它——'把我的应用跑到云端模拟器上'、'用 eas simulator 运行/安装/截图我的应用'、'我在 Linux/Cursor 上，需要 iOS 设备'、'这台机器没有模拟器 / headless CI'、'让 agent 帮我点一遍应用并截图'、'在带 live reload 的远程模拟器上测试我的 dev build'、'把模拟器串流到我的浏览器'——即使他们没有说 'EAS Simulator' 或 'cloud' 也算。在没有本地模拟器的宿主机上（Linux、CI、云端沙箱），它就是默认方案；在 macOS 上，对于一句简单的 'run on the simulator' 不要自动触发——仅在用户需要云端/远程/可共享的模拟器、需要他们没有的 iOS 版本，或需要 agent 驱动的会话时才使用。不适用于本地模拟器（expo run:ios、Xcode、Android Studio）、EAS Build/Update、web 预览或真机。"
version: 1.0.0
license: MIT
allowed-tools: "Bash(npx *eas-cli@*), Bash(npx *agent-device@*), Bash(npx expo *), Bash(eas *), Bash(expo *), Bash(xcodebuild*), Bash(pod*), Bash(argent *), Bash(ffmpeg*)"
---

# EAS Simulator

> **EAS 服务——会产生费用。** EAS Simulator 运行在 Expo Application Services 云基础设施上，这是一项有免费额度限制的付费产品；远程模拟器会话会使用你所购方案中的计算配额。详见 https://expo.dev/pricing。

EAS Simulator 在 EAS 基础设施上运行远程 iOS 模拟器或 Android 模拟器，由你在自己的机器上操控——通过 CLI、通过 AI agent（借助 `agent-device`），以及通过浏览器预览。它是**无法在本地运行模拟器的环境**（Linux 机器、Cursor Cloud 等云端/后台 agent）的解锁方案，也让 agent 能够在真实设备上*验证*改动，而不只是对代码进行推理。

`simulator:*` 命令是**实验性且隐藏的**，并且需要较新的 eas-cli（撰写时为 ≥ 20.3.0）——这也是本 skill 通过 `npx --yes eas-cli@latest` 运行所有命令的原因。flag 和动词可能会变化；如果命令失败，**以 `<cmd> --help` 为准。**

## 何时使用

frontmatter 的 `description` 中列出了触发短语。简而言之：用它把用户的应用跑在**云端**模拟器上并与之交互——尤其是在没有 Mac 或云端/沙箱的 agent 环境中。**不适用**于本地模拟器（`expo run:ios`、Xcode、Android Studio）、商店构建/签名（那是 EAS Build 的事）或真机。对于 macOS 的情况，见下一节*云端 vs 本地*。

## 云端 vs 本地：先做这个判断

- **非 macOS**（Linux / CI / Cursor Cloud 等云端沙箱，可通过 `uname -s` ≠ `Darwin` 检测）：这是获取模拟器的唯一途径——**在确认有访问权限后继续**（见下文*先检查可用性*）。
- **macOS：** 本地模拟器是存在的，而云端会话既花钱又有延迟，所以**先询问**（"要用远程云端模拟器吗——可以分享实时预览、转移负载，或测试你没有的 iOS 版本——还是直接在本地运行？"），除非用户明确说了云端/远程/可共享。
- 始终尊重用户的明确选择；对于"在本地运行"，转交给 `expo run:ios` / Xcode。

```bash
# Programmatic detection — run this to decide before doing anything else:
if [ "$(uname -s)" != "Darwin" ] || ! xcrun --find simctl &>/dev/null 2>&1; then
  echo "no local sim — proceed with EAS Simulator"
else
  echo "local sim available — ask the user (cloud or local?)"
fi
```

## 前提条件

- **通过 `npx --yes eas-cli@latest …` 运行所有 `eas` 命令**——保证 CLI 足够新、带有 `simulator:*`（全局安装的 `eas` 往往太旧），而且 `--yes` 会跳过 npx 的确认提示。（如果 `eas --version` 是最新的，直接用裸 `eas` 也行。）
- **已认证。** 有交互能力的机器 → `npx --yes eas-cli@latest login`。**云端沙箱 / CI / headless agent 无法进行浏览器登录——改为在环境中设置 `EXPO_TOKEN`**（expo.dev → Account → Access Tokens）。无论哪种方式，都用 `npx --yes eas-cli@latest whoami` 验证。
- 在 Expo **项目目录**中运行。全新应用需要一次性设置：`npx --yes eas-cli@latest init` 用于创建/关联项目（当没有 `projectId` 时），并且如果应用配置中缺少 **`ios.bundleIdentifier`，请设置它**——全新的 `create-expo-app` 往往没有它，而 `prebuild`/`eas build` 需要它（没有时它们会提示或直接失败；例如 `dev.<owner>.<slug>`）。用 `npx expo config --json` 读取当前配置（它可能在 `app.config.js` 里）。Mode C 首次运行较慢（原生构建）；后续运行会复用它。
- 一个用于操控设备的 controller。本 skill 使用 **agent-device**（开源，MIT），通过 `npx agent-device@latest` 按需运行——不需要全局安装任何东西。**argent** 是替代方案（在 `simulator:start` 中用 `--type argent`）；见 [references/controllers.md](./references/controllers.md)。
- **`.env.eas-simulator`** 由 eas-cli 写入/管理（不是本 skill）：它保存会话 id（`EAS_SIMULATOR_SESSION_ID`）+ daemon URL/**token**，因此 `get`/`stop`/`exec` 默认作用于该会话（通常**省略 `--id`**；用 `--id <id>` 指定其他会话）。它带有 **token → 确保将其加入 gitignore**（eas-cli 会标记它 "do not commit"，但可能不会添加 ignore 规则，而全新应用的 `.gitignore` 不会覆盖到它——如果缺少请添加 `.env.eas-simulator`）。
- `--max-duration-minutes` 仅限付费方案；否则应用默认值。
- **命令块假定使用 POSIX shell**（bash/zsh）——`printf`、`lsof`、`$(seq …)` 循环无法在 cmd/PowerShell 中运行。在 Windows 上，请在 WSL 或 Git Bash 中运行它们，或者边运行边转换（`eas-cli`/`agent-device` 的调用本身是跨平台的）。

## 先检查可用性

EAS Simulator 是一项**限制访问**的 EAS 功能，仍在逐步推出中，因此并非每个账号都已启用。在开始会话**之前**确认访问权限——这是一个只读检查：不会创建会话，不会计费。

```bash
npx --yes eas-cli@latest simulator:availability --json
# → {"available": true, ...}  enabled → continue to the core loop
# → {"available": false, ...} not enabled → do NOT start a session
```

如果**不**可用，不要调用 `simulator:start`（它会失败）。取而代之，优雅地转交，以便在没有本 skill 的情况下继续推进：
- 告诉用户他们的账号还没有 EAS Simulator——即将推出。
- 回退到实现其实际目标的常规本地路径——本地模拟器/模拟器用 `expo run:ios` / Xcode / Android Studio，或者 EAS Build，或者其他合适的方案。不要在云端模拟器上走进死胡同；用户的请求几乎从来不是"专门使用 EAS Simulator"。

（如果 `simulator:availability` 不被识别，说明 CLI 太旧——升级即可；或者以同样方式处理来自 `simulator:start` 的 `not enabled for this account` 错误：停下来并回退。）

## 核心循环（永远一样）

一个会话是：**start →（安装你的应用）→ drive → stop。** `eas-cli` 管理*会话*；设备*动词*（open/tap/screenshot）来自 controller，`npx --yes eas-cli@latest simulator:exec` 会在加载会话的连接环境后替你运行它。

```bash
# 1. Start a session (boots the remote sim + agent-device daemon; writes .env.eas-simulator).
printf '# managed by eas-cli\n' > .env.eas-simulator   # clear any stale session first
npx --yes eas-cli@latest simulator:start --platform ios --type agent-device --non-interactive \
  --name "Checkout flow screenshots"   # always name it — see 'Always name the session'
#    Then confirm it's live: simulator:get --json → status IN_PROGRESS (bounded poll in run-your-app.md).

# 2. Drive it through `exec` (loads the session env, then runs the command you give it).
#    agent-device runs on demand via npx — nothing installed globally.
npx --yes eas-cli@latest simulator:exec npx agent-device@latest open <app-or-url> --platform ios
npx --yes eas-cli@latest simulator:exec npx agent-device@latest snapshot -i          # interactive UI tree → @e1, @e2 refs
npx --yes eas-cli@latest simulator:exec npx agent-device@latest press @e2            # tap a ref (NOTE: 'press', not 'tap')
npx --yes eas-cli@latest simulator:exec npx agent-device@latest screenshot ./shot.png

# 3. Stop (ends billing; tears down the VM) and reset the dotenv. Omit --id to target the dotenv session.
npx --yes eas-cli@latest simulator:stop
printf '# managed by eas-cli\n' > .env.eas-simulator
```

要实时**观看**，把 `start` 打印出的 `webPreviewUrl` 交给用户（`--type agent-device` 的 iOS 会话会在 daemon 旁边运行 serve-sim，所以会输出一个——一个会话同时拥有 agent 控制*和*浏览器预览；Android 没有预览，而 `--type serve-sim` 只有预览）。**这个 URL 是给*用户*的浏览器用的——你无法替他们打开它，而且它绝不能碰到模拟器：**
- **"在这里打开"（Cursor/VS Code）** → 把 URL 单独打印一行，并告诉用户打开 Simple Browser（`Cmd/Ctrl+Shift+P` → "Simple Browser: Show"）并粘贴进去。然后**停下**：不要调用 shell 去打开系统浏览器或 Cursor/VS Code 的 URL handler，也不要问"出现标签页了吗？"——你无法确认，交接已经完成。
- **绝不要在模拟器上 `open` `webPreviewUrl`。** 它是浏览器预览，不是 deep link，也不是 `agent-device open` 的参数；把它路由到设备会渲染出"浏览器套浏览器"（一个真实发生过的故障）。
- **Headless agent**（没有显示器）→ 直接把 URL 作为交付物返回即可。
- **保活让用户来操控** → 设定上限：用 `--max-duration-minutes N` 启动让它自动停止；告诉他们停止之前一直在计费以及何时自动停止；结束时主动提出重新开启/延长。（这是"立即停止"不适用的唯一情形；一次性的 `screenshot`/`get` 运行仍然立即停止。）

`start` 还会打印一个 job-run URL。

## 始终为会话命名

每次 `simulator:start` 都传 `--name "<description>"`。这个名字会出现在 `simulator:list`、`simulator:get` 以及 expo.dev 的 **Simulator sessions** 页面上，在那里它会替换每一行的通用标题。不命名的话，每一行都显示 "Simulator session" 加一个随机 id——一堵谁也无法导航的相同条目墙。写名字时要面向**几天后浏览该列表的人**，而不是为本次运行中的自己。

用几个朴素的词写出这个会话是*干什么*的：

```bash
--name "Checkout flow screenshots"     # what you did
--name "Dev build — dark mode fix"     # what you were testing
--name "Login repro for issue 412"     # why it exists
```

规则：
- 从用户的请求中提炼，而不是从模式或工具中提炼。`Mode C session`、`agent-device ios` 和 `test` 什么都没说。
- **长度：目标 3–6 个单词、约 40 个字符，并把 50 视为实际上限。** 它在窄表格列中渲染为单行标题，名字太长会被截断。API 接受最多 **255 个字符**并拒绝空白/仅空白字符的名字，但 255 是你永远不该接近的上限，而不是目标。一个名词短语，不要句子。
- 在这个预算内做到具体。有工单号或 PR 号就带上。
- **句首大写：** 只有首词大写，标识符保持其真实大小写（`Dev build for expo-router v4`、`Repro for EXPO-1234`）。它是行标题，所以不用 Title Case、不用全小写，结尾也不加句号。
- **不要重复表格已经显示的内容。** 每一行已经显示了会话 id、平台、开始时间、时长和创建者——所以不放 id、不放 `iOS`、不放日期、不放在你自己的名字。把整个预算花在那些列说不出来的东西上：用途。
- 如果用户起了名字，照用他们的名字。
- 会话是按次运行的，所以为每次新运行命名。不要把旧名字复用到不同的工作上。

`--name` 比 `simulator:start` 本身更晚出现，因此较旧的已安装 `eas-cli` 可能拒绝它。如果发生这种情况，通过 `npx --yes eas-cli@latest` 运行或升级；作为最后手段，去掉 `--name` 重试一次（会话将以未命名方式启动）。见 [references/troubleshooting.md](./references/troubleshooting.md)。

## 命令一览

| 命令 | 用途 |
|---|---|
| `npx --yes eas-cli@latest simulator:start --platform ios\|android --name "<description>" [--type agent-device\|argent\|serve-sim] [--package-version X] [--max-duration-minutes N] [--non-interactive] [--json]` | 创建会话；启动模拟器 + controller；写入 `.env.eas-simulator`；打印 `webPreviewUrl` + job-run URL。**始终传 `--name`**（见*始终为会话命名*）。**`--json` 会抑制 `.env.eas-simulator` 的写入**——在 `exec` 流程中省略它，或者自己从 `remoteConfig` 设置环境。 |
| `npx --yes eas-cli@latest simulator:exec <cmd> [args…]` | 加载 `.env.eas-simulator`，然后在该环境下运行 `<cmd>`。通往 controller 的桥梁。 |
| `npx --yes eas-cli@latest simulator:get [--id] [--json]` | 会话状态 + 连接详情，包括会话 `--name`。**用它来确认就绪**（见*操作原则*）。 |
| `npx --yes eas-cli@latest simulator:list [--status …] [--type …] [--platform …]` | 按名称列出应用的会话——这就是传给 `start` 的 `--name` 的用途 |
| `npx --yes eas-cli@latest simulator:stop [--id]` | 停止会话（幂等） |

## 运行用户的应用——选一种模式

远程模拟器启动时是**空白的——没有 Expo Go，没有任何应用。** 安装一个构建，然后操控它——但**先让构建*类型*匹配目标**（下面方框中）；实时会话运行就是在这里翻车的。完整流程：[references/run-your-app.md](./references/run-your-app.md)——在运行某种模式之前先读它。

> **在安装任何东西之前先让构建匹配目标——实时会话运行就是在这里翻车的。** 两个陷阱，同一个根源（拿了一个与请求不匹配的构建）：
> 1. **类型错误。** 实时编辑（Mode C）**需要 dev build。** 一个*静态*构建——本地 Release（A）、默认的 EAS 模拟器构建（B），或者**之前截图运行留在模拟器上的任何构建**——其 JS 在构建时就已冻结，**永远无法热重载。** 对于实时请求，**完全忽略已有构建**，安装一个 **dev** 构建（本地 Debug，或带 `developmentClient: true` 的 EAS 构建）。永远不要把 Metro 重新连到一个静态构建上并指望它能重载——它不会。
> 2. **过期。** 静态展示必须匹配当前源码——只复用 fingerprint 匹配的构建，否则就重新构建；复用必须是显式的。
>
> 所以残留的 EAS/release 构建**不是**"实时迭代"的捷径——它是错误的二进制文件。构建*存在*这一事实永远不会让它成为正确的构建。

| 模式 | 是什么 | 何时选择 | 支持实时编辑？ |
|---|---|---|---|
| **A——本地 release 构建** | 在本地构建 Release `.app`，用 `agent-device install` 安装（会上传） | 用户有 Mac 工具链，想要快速"把我的当前代码跑到云端设备上" | 否（需重新构建才能看到变化） |
| **B——EAS 构建**（少见，仅限显式要求） | 用 `eas build` 构建模拟器构建，用 `agent-device install-from-source <url>`（VM 去下载） | **仅在明确要求时**——用户指名某个已有/EAS 构建，或想要一个静态 EAS 产物用于 CI/分享。不用于"给我看看"/"迭代"（用 C）。模拟器构建不需要凭据。 | 否 |
| **C——本地 dev 构建 + tunnel** | Dev（Debug）构建 + `EXPO_UNSTABLE_TUNNEL_V2=1 expo start --tunnel` + 把 dev client 连到 Metro | **agent 式的边改边看循环**——改代码并实时看到（Fast Refresh） | **是** |

快速决策——**默认选 C；A 和 B 仅限显式要求：**
- **C（几乎所有情况）：** 迭代、交互、戳应用、实时编辑——*以及*大多数"给我看看我的应用"（当前代码反正需要构建，所以实时+当前代码胜出）。有 Mac → 本地构建 dev client；没有 Mac → 在 EAS 上构建（`developmentClient: true`）。**拿不准 → C。**
- **A：** 仅在 Mac 上做明确的一次性**静态**截图。
- **B：** 仅当用户指名某个已有/EAS 构建，或想要一个静态 EAS 产物（CI/分享）——见上方方框，了解为什么静态构建不适合"迭代"。

## 操控设备（agent-device）

`agent-device` 就是 controller。常用动词（每条都以 `npx --yes eas-cli@latest simulator:exec npx agent-device@latest <verb>` 的形式运行）：

| 动词 | 作用 |
|---|---|
| `apps --platform ios` | 列出用户安装的应用（空白模拟器上不显示任何应用）；加 `--all` 可包含系统应用 |
| `install <appId> <path> --platform ios` | 安装本地 `.app`（会上传） |
| `install-from-source <url> --platform ios` | 从 URL 安装——VM 去下载（用于 EAS 产物） |
| `open <appId\|deep-link> --platform ios` | 启动应用（bundle id）或跟随应用 **deep link**（`exp+slug://…`）。首次 deep link 会弹出系统 **"Open in '<app>'?"** 对话框——要有预期（别浪费一次 snapshot 去发现它），并用 `press 'label="Open"'` 交接；它可能很慢，所以用 agent-device 自己的 `--timeout` 来设上限（例如 `press 'label="Open"' --timeout 120000`）——**而不是** shell 的 `timeout` 包装器（macOS 没有 `timeout` 这个二进制）。(Mode C 通过 "Enter URL manually" 为 Metro 连接环节绕过了这个对话框——见 run-your-app.md。）**不适用**于 `webPreviewUrl`——那是给用户的浏览器预览，永远不是给设备的。 |
| `snapshot -i` | 可交互的无障碍树 → `@e1` 风格的引用 |
| `press <ref\|selector>` | 点击（例如 `press @e2` 或 `press 'label="Open"'`）——**点击动词是 `press`，不是 `tap`** |
| `fill <ref> "text"` | 在输入框中输入文字 |
| `screenshot <path>` | 把屏幕截图保存为本地 PNG（从 daemon 下载）——需要先打开一个应用（先 `open`） |
| `record start` / `record stop <path>` | 把屏幕录制为视频——用于**动态内容**（动画、手势、转场、时序问题），单张截图无法捕捉 |
| `metro prepare` / `metro reload` | 把 dev client 指向 Metro / 重载（Mode C） |

**截图 vs 录屏。** 静态状态默认用 `screenshot`，但对于任何*会动*的东西——动画、转场、手势、时序/卡顿问题——**录制视频并检查帧**；静态图无法证明运动。两种 controller 都能录制（agent-device 的 `record start`/`stop`，argent 的 `screen-recording-start`/`stop`）。录制采样率约 30fps——足以看出明显的卡顿，但不足以证明 60/120Hz 下亚帧级别的掉帧。对于**时序**问题，argent 默认会丢弃静态帧（关掉 `trimStatic`）——这一点以及其他各 controller 的坑都在 [references/controllers.md](./references/controllers.md) 中。

完整的动词集合和 `argent` controller 替代方案见 [references/controllers.md](./references/controllers.md)。

## 操作原则

不那么显而易见、值得内化的心智模型。具体的 错误→修复 查询表（卡住的动词、`tap`→`press`、`--platform`、`--json`、`pod install` locale、孤立会话、启动波动）见 [references/troubleshooting.md](./references/troubleshooting.md)。

1. **先确立事实基线，然后重置——不要打补丁式循环。** 永远不要假定已有会话或 Metro 是你的或健康的。在操控之前，确认：
   - **cwd** ——你在预期的 Expo 项目目录中（指向错误的 `start`/`exec` 会让*错误的应用*进入会话 + 留下一个游离的 `.env.eas-simulator`；用 `pwd` / 检查 `app.json`）。
   - **会话存活** ——通过 `simulator:get --json` 确认 `IN_PROGRESS`（已停止的会话仍保留 id + `remoteConfig`，所以光有 dotenv 不能证明）。
   - **Metro 在自己的端口上** ——只有本会话内由你启动的才复用；否则在空闲端口上启动一个（`--port <N>`，例如 8082），不要杀掉别的服务器来夺回 `:8081`（run-your-app.md）。
   - **构建匹配意图** ——**release 构建无法实时重载**；如果想要实时编辑而安装的是 release 构建，**安装 dev 构建，不要重连**。

   如果**首次**连接后当前代码没有渲染出来，停止对实时状态的试探：**重置到基线**（停止会话 → 清空 dotenv → 杀掉你的 Metro）并把该模式**重做一遍**；第二次失败 → 停下并报告。永远不要原地重启 Metro、重连超过一次、为修复 JS/连接问题而重新构建原生客户端，或在状态未知时抛出预览 URL。（daemon 掉线——`ERR_NGROK_3200` / `Remote daemon is unavailable`——处理方式相同：重置，而不是重试。）
2. **`exec` 是包装器，不是驱动器。** `simulator:exec` 加载 `.env.eas-simulator` 并派生你传入的命令；设备动词来自 controller（`npx agent-device@latest`）。不存在 `simulator:tap`。
3. **立即行动；不要闲置会话。** 会话是短生命周期的——`start` 之后立即安装并操控。放着闲置会丢掉 tunnel/daemon（→ 按第 1 条重置）。
4. **在所有退出路径上停止（计费）并重置 dotenv。** `--non-interactive` 不会自动停止，被遗忘的会话会计费直到被停止。不要为了"重试"缓慢的启动而再次 `start`——那会让第二个计费会话变成孤儿。
5. **只对正确且新鲜的构建截图。** Mode C 仅在 dev client 连上 Metro 之后；A/B 仅用与当前源码匹配的构建——复用已有构建是"我的编辑不显示"的第一大成因（见上方的构建注意事项）。（状态栏中的 `9:41` 是模拟器默认值，不是过期。）

## 停止并清理

停止会话（结束计费）**并重置 dotenv**，以免后续运行试图复用已死的会话：

```bash
npx --yes eas-cli@latest simulator:stop          # omit --id → stops the dotenv session (or pass --id <id>)
printf '# managed by eas-cli\n' > .env.eas-simulator   # clear the stale session id so it isn't reused
# if you started Metro for Mode C, stop it too (Ctrl+C in its terminal, or kill the expo process)
```

## 参考资料

- [references/run-your-app.md](./references/run-your-app.md) ——模式 A、B 和 C 的完整命令序列（在运行某种模式之前先读）。
- [references/controllers.md](./references/controllers.md) ——agent-device 动词参考和 `argent` 替代方案。
- [references/troubleshooting.md](./references/troubleshooting.md) ——具体错误及修复方法。

权威信息来源：Expo 文档以及 `eas` / `agent-device` CLI（`npx --yes eas-cli@latest simulator:* --help`、`agent-device --help`）。本 skill 教你如何使用它们；它不能替代它们。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "eas-simulator" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
