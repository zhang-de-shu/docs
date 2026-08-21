---
name: expo-examples
description: Framework（开源）。Expo 官方示例项目——expo/examples 仓库中约 70 个 `with-*` 集成示例（Stripe、Clerk、Supabase、OpenAI、地图、Reanimated、SQLite、Skia、NativeWind 等）。适用于将第三方库或服务集成到现有 Expo 应用中、希望获得规范的且版本匹配的模式以供改编时，或使用 `npx create-expo --example` 从某个示例脚手架创建新项目时。
allowed-tools: "Read,Bash(gh api:*),Bash(git clone:*),Bash(npx create-expo:*),Bash(npx degit:*),Bash(bun create:*)"
version: 1.0.0
license: MIT
---

# Expo Examples

[expo/examples](https://github.com/expo/examples) 是 Expo 的官方示例库，包含约 70 个**集成示例**——目录命名为 `with-<library>`（例如 `with-stripe`、`with-maps`），每个示例围绕**一个**库或服务构建。它们不是完整的应用：它们是 **managed** 项目（没有 `ios/`/`android/` 目录——原生配置通过 config plugins 完成），典型的示例是**约 100–200 行的单个界面**。请从中挖掘规范的集成*模式*——Expo 针对当前 SDK 维护的依赖集合、`app.json` config plugins 和最简接线代码——并将其改编到用户的应用中。不要指望从中搬出整套应用架构。

在手工实现集成之前，先去找一个示例。（种类——全栈、展示、starter——在 `./references/catalog.md` 中有说明。）

## 两种模式

1. **参考/改编**（最常见）——用户已经有项目。找到匹配的示例，阅读其关键文件，把*模式*应用到他们的代码中。
2. **脚手架**——全新项目。直接从示例启动一个新项目。

## 工作流程

### 1. 找到合适的示例

把用户的需求映射到示例名称（例如支付 → `with-stripe`，认证 → `with-clerk`）。`./references/catalog.md` 是用于快速筛选的分类快照——但它会过时，所以要与线上列表核对：

```bash
# Live example names:
gh api repos/expo/examples/contents --jq '.[] | select(.type=="dir" and (.name|startswith(".")|not)) | .name'
# Aliases (renamed) + deprecated (dead/moved) examples — check before recommending:
gh api repos/expo/examples/contents/meta.json --jq '.content' | base64 -d
```

`meta.json` 是关于哪些示例已改名或已废弃的事实来源（废弃的示例会从仓库目录树中移除，但仍在这里列出，每个都带有一条 `message`）。如果某个示例位于其 `deprecated` 映射中，不要推荐它——按照 `message` 找到现代替代路径。如果它位于 `aliases` 中，请使用 `destination`。

### 2a. 参考模式——在不触碰用户项目的情况下研究

常见情况：用户已经有了应用，想看看 Expo 是怎么做某件事的。把示例作为**参考**阅读，手工应用其中的模式——绝不要在用户项目之上脚手架一个示例。

**首先，一次性列出整个示例。** 集成代码通常是嵌套的（例如 Stripe 的服务端路由位于 `app/api/`），因此只列一层会漏掉重要文件：

```bash
gh api 'repos/expo/examples/git/trees/master?recursive=1' \
  --jq '.tree[].path | select(startswith("with-stripe/"))'
```

**然后优先阅读高价值文件：** `README.md`（配置步骤）→ `package.json`（依赖）→ `app.json`（config plugins / 权限）→ 清单中揭示的集成代码 → `.env`（所需的机密信息）。每个文件：

```bash
gh api repos/expo/examples/contents/with-stripe/utils/stripe-server.ts --jq '.content' | base64 -d
# No gh? Raw URL (branch is master):
curl -s https://raw.githubusercontent.com/expo/examples/master/with-stripe/utils/stripe-server.ts
```

**要读的文件超过两三个？** 许多集成分散在服务端路由、客户端 provider 和配置中（Stripe 就是如此）。跳过逐文件调用——把整个示例拉到一个**用完即弃/被 gitignore 的目录（不是用户项目）**中，用 Grep/Read 自由阅读，然后手工应用：

```bash
npx degit expo/examples/with-stripe /tmp/expo-ref/with-stripe   # clean copy, no git history
# fallback without degit (sparse-checkout, no full ~64 MB clone):
git clone --depth 1 --filter=blob:none --sparse https://github.com/expo/examples.git /tmp/expo-ref/examples \
  && (cd /tmp/expo-ref/examples && git sparse-checkout set with-stripe)
```

从那里用 Grep/Read 阅读；完成后删除临时目录。

### 2b. 脚手架模式——从示例创建新项目

```bash
npx create-expo --example with-stripe   # short form:  npx create-expo -e with-stripe
bun create expo --example with-stripe    # with bun
```

### 3. 改编进用户的应用——非破坏性地（关键）

当用户已经有了应用时，**只添加示例所引入的内容；绝不覆盖他们的配置。**

- **版本对齐——不要照抄固定版本。** 示例跟随**最新** SDK，因此它们 `package.json` 中固定的版本与较旧的项目不匹配。只添加*缺失的*依赖，用 `npx expo install <pkg>`（它会解析出与 SDK 匹配的正确版本），而不是照抄精确版本号。
- **合并配置，而不是替换。** 只添加示例引入的、用户尚缺的 `app.json`/`app.config.*` plugins 和权限——保持他们现有的配置块完好。
- **移植集成代码。**
- **重建环境变量**，参照示例 `.env` 的结构——其中存放的是占位符，绝不是可用的机密信息。

**完成的标准是**集成代码已移植，且它所需的每个依赖、config plugin、权限和环境变量都已在用户的应用中落实——而不是它仅仅*看起来*接通了。

## 注意事项

- **默认分支是 `master`，** 不是 `main`（对 raw URL 和 sparse checkout 很重要）。
- **一键部署。** 每个示例都有一个启动 URL：`https://launch.expo.dev/?github=https://github.com/expo/examples/tree/master/<example>`。

## 相关 skill

- Tailwind / NativeWind 样式 → `expo-tailwind-setup`
- 原生 UI 组件（@expo/ui 包）→ `expo-ui`
- 样式和原生质感的界面 → `expo-native-ui`
- 导航和路由 → `expo-router`
- 编写原生模块 → `expo-module`
- 在采用最新 SDK 的示例之前先升级 SDK → `expo-upgrade`

## 参考文档

- `./references/catalog.md` — 示例库的分类快照，用于快速筛选。

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-examples" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
